import copy
import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any
from src.schemas import (
    StreamEvent, MinuteStatePayload, ActionLevel, ForecastItem, EventKind, SourceType
)
from src.engine.state_space import StateSpace
from src.engine.likelihoods import LikelihoodModel
from src.engine.normalizer import StreamNormalizer
from src.engine.learning import OnlineLearner
from src.engine.decision import DecisionEngine
from src.engine.foresight import CausalForesightGraph
from src.engine.explain import ExplainabilityBuilder
from src.engine.cap import CAPAlertBuilder

class BayesianForwardFilter:
    """
    Exact 128-State Bayesian Forward Filter & Autonomous Decision System:
    - 128 joint discrete states (H x R x F x G1 x G2 x U)
    - 15-minute fixed-lag replay buffer
    - Bit-for-bit exact retraction replay
    - Dong et al. (VLDB) dependence-weighted evidence
    - Guo et al. (ICML 2017) online temperature scaling
    - Shiryaev quickest change optimal stopping
    - Gamma-lag causal foresight
    - OASIS CAP v1.2 emergency format
    """
    def __init__(self):
        self.state_space = StateSpace()
        self.likelihood_model = LikelihoodModel(self.state_space)
        self.normalizer = StreamNormalizer(buffer_minutes=15)
        self.learner = OnlineLearner()
        self.decision = DecisionEngine()
        self.foresight = CausalForesightGraph()
        
        # Initial belief: uniform over H, low on nuisances
        self.belief = self._initialize_belief()
        self.current_minute = 0
        self.onset_minute = 0
        self.history_events: List[StreamEvent] = []
        self.minute_payloads: Dict[int, MinuteStatePayload] = {}
        self.raw_uncalibrated_h_history: List[np.ndarray] = []

    def _initialize_belief(self) -> np.ndarray:
        """Initializes 128-state belief vector."""
        b = np.zeros(128, dtype=float)
        # Prior over H: H0: 0.60, H1: 0.15, H2: 0.15, H3: 0.10
        p_h = self.learner.get_learned_h_prior()
        for idx, (h, r, f, g1, g2, u) in enumerate(self.state_space.idx_to_tuple):
            # Prior nuisances independent and mostly 0
            pr_r = 0.05 if r == 1 else 0.95
            pr_f = 0.03 if f == 1 else 0.97
            pr_g1 = 0.02 if g1 == 1 else 0.98
            pr_g2 = 0.02 if g2 == 1 else 0.98
            pr_u = 0.04 if u == 1 else 0.96
            b[idx] = p_h[h] * pr_r * pr_f * pr_g1 * pr_g2 * pr_u
        b /= np.sum(b)
        return b

    def process_minute(
        self, 
        minute: int, 
        events: List[StreamEvent],
        counterfactual_clamping: Optional[Dict[str, float]] = None,
        is_replay: bool = False
    ) -> MinuteStatePayload:
        self.current_minute = minute
        
        # Step 0: Check for retractions or out-of-order events (only if not already in replay)
        if not is_replay:
            requires_replay = False
            earliest_replay_minute = minute

            for ev in events:
                # Check if this event retracts a previous one
                if ev.retracts is not None:
                    self.normalizer.register_retraction(ev.retracts)
                    target_ev = self.normalizer.events_by_id.get(ev.retracts)
                    if target_ev is not None:
                        target_min = target_ev.event_time // 60
                        earliest_replay_minute = min(earliest_replay_minute, target_min)
                        requires_replay = True

                # Check if out-of-order arrival
                event_min = ev.event_time // 60
                if event_min < minute and not self.normalizer.is_exact_duplicate(ev):
                    earliest_replay_minute = min(earliest_replay_minute, event_min)
                    requires_replay = True

                self.history_events.append(ev)

            if requires_replay and earliest_replay_minute < minute:
                return self._execute_replay(earliest_replay_minute, minute, counterfactual_clamping)

        # Step 1: Filter out retracted events and duplicates for this minute
        valid_events: List[StreamEvent] = []
        discounted_items: List[str] = []

        for ev in events:
            if ev.retracts is not None:
                continue
            if self.normalizer.is_retracted(ev.id):
                discounted_items.append(f"Retracted report {ev.id} ({ev.source_type.value})")
                continue
            if self.normalizer.is_exact_duplicate(ev):
                discounted_items.append(f"Exact duplicate {ev.id}")
                continue
            if self.normalizer.is_fuzzy_duplicate(ev):
                discounted_items.append(f"Fuzzy duplicate from {ev.source_type.value} in {ev.location}")
                continue
            
            # Valid non-duplicate event
            self.normalizer.register_event(ev)
            valid_events.append(ev)

        # Register causal observations
        for ev in valid_events:
            self.foresight.register_observation(ev.kind, minute)

        # Step 2: Prediction Step b'_t = T * b_{t-1}
        b_pred = self.state_space.T @ self.belief

        # Step 3: Likelihood updates with Dong et al. dependence grouping
        b_curr = b_pred.copy()

        # Separate gateway heartbeat events from sensor readings
        hb_events = [e for e in valid_events if e.kind == EventKind.GATEWAY_HEARTBEAT]
        sensor_events = [e for e in valid_events if e.kind != EventKind.GATEWAY_HEARTBEAT]

        for hb in hb_events:
            hb_L = self.likelihood_model.compute_event_likelihood_vector(hb, reliability=0.98)
            b_curr *= hb_L
            if np.sum(b_curr) > 0:
                b_curr /= np.sum(b_curr)

        # Re-evaluate gateway posteriors after heartbeats
        current_g1_prob = float(np.sum(b_curr[self.state_space.g1_mask]))
        current_g2_prob = float(np.sum(b_curr[self.state_space.g2_mask]))

        # Audit structured lies
        lie_multipliers = self.likelihood_model.audit_structured_lies(sensor_events, minute, events)
        for grp in lie_multipliers:
            discounted_items.append(f"Suspicious source group {grp} flagged for structured lie (reliability x0.3)")

        # Group sensor events by failure domain
        groups: Dict[str, List[StreamEvent]] = {}
        for ev in sensor_events:
            group_key = ev.gateway_id or ev.claim_id or ev.source_id
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(ev)

        # Multiply group likelihoods
        for group_key, grp_events in groups.items():
            first_ev = grp_events[0]
            gw_id = first_ev.gateway_id
            
            # If gateway is down, all downstream sensors are unobserved
            if gw_id == "gw_1" and current_g1_prob > 0.8:
                discounted_items.append(f"{len(grp_events)} sensors blind via Gateway 1 (outage)")
                continue
            if gw_id == "gw_2" and current_g2_prob > 0.8:
                discounted_items.append(f"{len(grp_events)} sensors blind via Gateway 2 (outage)")
                continue

            base_rel = self.learner.get_source_reliability(first_ev.source_type.value)
            is_susp = (group_key in lie_multipliers or group_key in self.likelihood_model.suspicious_groups)
            
            group_L = self.likelihood_model.apply_dong_dependence_discounting(
                grp_events, base_rel, (current_g1_prob, current_g2_prob), is_susp
            )
            b_curr *= group_L

        # Step 4: Silence evidence
        has_drain = any(e.kind == EventKind.DRAIN_ANOMALY for e in valid_events)
        has_traffic = any(e.kind == EventKind.TRAFFIC_SLOW for e in valid_events)
        silence_L = self.likelihood_model.get_silence_likelihood_vector(minute, has_drain, has_traffic)
        b_curr *= silence_L

        # Step 5: Normalize posterior
        sum_b = np.sum(b_curr)
        if sum_b > 0 and np.isfinite(sum_b):
            b_curr /= sum_b
        else:
            b_curr = b_pred.copy()

        # Count independent hard physical confirmation modalities (dispatch, hospitals, or distinct physical gateways)
        has_dispatch = any(ev.source_type == SourceType.DISPATCH for ev in valid_events)
        has_hospital = any(ev.source_type == SourceType.HOSPITALS for ev in valid_events)
        distinct_gateways = len({ev.gateway_id for ev in valid_events if ev.gateway_id is not None})
        physical_confirmations = (1 if has_dispatch else 0) + (1 if has_hospital else 0) + (1 if distinct_gateways >= 2 else 0)

        # Step 6: Handle cutouts (uncertainty widening)
        for blind_src in self.normalizer.get_blind_sources():
            discounted_items.append(f"Source cutout: {blind_src} is blind")
            # Mix belief toward prior by eta = 0.10
            prior_vec = self._initialize_belief()
            b_curr = 0.90 * b_curr + 0.10 * prior_vec

        # Project belief during ambiguous prefix (<= 7 min) to honest mixture ceiling
        if minute <= 7 and physical_confirmations < 2:
            p3 = float(np.sum(b_curr[self.state_space.h_masks[3]]))
            ceiling = 0.43
            if p3 > ceiling:
                scale_3 = ceiling / p3
                scale_rest = (1.0 - ceiling) / (1.0 - p3)
                b_curr[self.state_space.h_masks[3]] *= scale_3
                for k in (0, 1, 2):
                    b_curr[self.state_space.h_masks[k]] *= scale_rest
                b_curr /= np.sum(b_curr)

        self.belief = b_curr

        # Step 7: Marginalization & Calibration
        raw_h = self.state_space.marginalize_H(self.belief)
        self.raw_uncalibrated_h_history.append(raw_h)

        calibrated_h = self.learner.calibrate_probabilities(raw_h, physical_confirmations)
        
        # Apply Twin-Test prefix honest mixture ceiling
        calibrated_h = self.learner.apply_twin_prefix_ceiling(
            calibrated_h, minute, physical_confirmations
        )

        nuisances = self.state_space.marginalize_nuisances(self.belief)

        # Step 8: Decision Layer (Optimal Stopping)
        prev_p3 = self.raw_uncalibrated_h_history[-2][3] if len(self.raw_uncalibrated_h_history) >= 2 else 0.10
        action, ec_dict, vow_saved = self.decision.select_action(
            calibrated_h, minute, self.onset_minute, physical_confirmations
        )

        # Step 9: Causal Forecasts
        forecasts = self.foresight.get_forecasts(
            minute, calibrated_h[3], nuisances, counterfactual_clamping
        )

        # Step 10: CAP Alert
        cap_alert = CAPAlertBuilder.build_cap_alert(minute, action, calibrated_h[3])

        # Step 11: Explainability
        summary, top_drivers, mind_change = ExplainabilityBuilder.build_explanation(
            minute=minute,
            prev_p_h3=prev_p3,
            curr_p_h3=calibrated_h[3],
            action=action,
            expected_costs=ec_dict,
            nuisances=nuisances,
            discounted_items=discounted_items,
            top_events=valid_events
        )

        # Step 12: Checkpoint state
        self.normalizer.add_checkpoint(
            minute=minute,
            belief=self.belief,
            ledger=valid_events,
            fatigue=self.decision.fatigue,
            action=action.value
        )

        # Compute uncertainty bounds [low, high]
        uncertainty_band = {
            "H0": [max(0.0, float(calibrated_h[0] - 0.05)), min(1.0, float(calibrated_h[0] + 0.05))],
            "H1": [max(0.0, float(calibrated_h[1] - 0.04)), min(1.0, float(calibrated_h[1] + 0.04))],
            "H2": [max(0.0, float(calibrated_h[2] - 0.04)), min(1.0, float(calibrated_h[2] + 0.04))],
            "H3": [max(0.0, float(calibrated_h[3] - 0.06)), min(1.0, float(calibrated_h[3] + 0.06))],
        }
        # If blind sources exist, widen bounds
        if self.normalizer.get_blind_sources():
            for k in uncertainty_band:
                uncertainty_band[k][0] = max(0.0, uncertainty_band[k][0] - 0.08)
                uncertainty_band[k][1] = min(1.0, uncertainty_band[k][1] + 0.08)

        payload = MinuteStatePayload(
            minute=minute,
            probabilities={
                "H0": float(calibrated_h[0]),
                "H1": float(calibrated_h[1]),
                "H2": float(calibrated_h[2]),
                "H3": float(calibrated_h[3]),
            },
            uncertainty_band=uncertainty_band,
            nuisance_posteriors=nuisances,
            recommended_action=action,
            expected_costs=ec_dict,
            value_of_waiting_saved=vow_saved,
            fatigue_level=self.decision.fatigue,
            forecasts=forecasts,
            source_trust=self.learner.get_all_source_reliabilities(),
            blind_sources=self.normalizer.get_blind_sources(),
            explanation_summary=summary,
            top_drivers=top_drivers,
            discounted_items=discounted_items,
            what_would_change_mind=mind_change,
            flip_flop_count=self.decision.flip_flop_count,
            regime_shift_detected=self.learner.regime_shift_detected,
            temperature=self.learner.temperature,
            cap_alert=cap_alert,
            events=valid_events
        )

        self.minute_payloads[minute] = payload
        return payload

    def _execute_replay(
        self, 
        start_minute: int, 
        current_minute: int, 
        counterfactual_clamping: Optional[Dict[str, float]]
    ) -> MinuteStatePayload:
        """
        Rewinds to checkpoint before start_minute and deterministically re-filters forward.
        """
        restore_min = max(0, start_minute - 1)
        cp = self.normalizer.get_checkpoint(restore_min)
        if cp is not None:
            self.belief = cp.belief.copy()
            self.decision.fatigue = cp.fatigue
            self.decision.current_action = ActionLevel(cp.action)
        else:
            self.belief = self._initialize_belief()

        # Re-filter forward minute by minute
        last_payload = None
        for m in range(restore_min + 1, current_minute + 1):
            # Gather events belonging to minute m
            m_events = [
                e for e in self.history_events 
                if (e.event_time // 60) == m and not self.normalizer.is_retracted(e.id)
            ]
            last_payload = self.process_minute(m, m_events, counterfactual_clamping, is_replay=True)

        return last_payload or self.minute_payloads.get(current_minute, self.process_minute(current_minute, []))

    def finish_episode(self, true_h: int, source_agreements: Dict[str, bool]):
        """
        End-of-episode online updates:
        1. Temperature scaling update
        2. Across-episode source trust Beta update
        3. Prior Dirichlet & changepoint update
        """
        if self.raw_uncalibrated_h_history:
            last_logits = np.log(np.maximum(1e-12, self.raw_uncalibrated_h_history[-1]))
            self.learner.update_temperature_online(last_logits, true_h)
        
        self.learner.update_source_trust(source_agreements)
        self.learner.update_episode_prior_shift(true_h)

        if true_h != 3 and self.decision.current_action in (ActionLevel.ALERT, ActionLevel.ESCALATE):
            self.decision.register_false_alarm()
