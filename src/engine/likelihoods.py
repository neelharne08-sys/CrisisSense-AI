import numpy as np
from typing import Dict, List, Optional, Tuple
from src.schemas import StreamEvent, EventKind, SourceType
from src.engine.state_space import StateSpace

class LikelihoodModel:
    """
    Computes reliability-adjusted likelihoods, Dong et al. (VLDB) dependence weighting,
    structured-lie detection penalties, and silence-as-evidence vectors across 128 states.
    """
    def __init__(self, state_space: StateSpace):
        self.state_space = state_space
        self.num_states = state_space.num_states
        self.fault_likelihood = 0.25
        
        # Source group history for structured-lie detection
        self.recent_events_by_group: Dict[str, List[StreamEvent]] = {}
        self.suspicious_groups: Dict[str, int] = {} # group_id -> expiry_minute

    def get_base_probability(self, kind: EventKind, s: Tuple[int, int, int, int, int, int]) -> float:
        """
        Calculates P(event_kind observed | latent state s = (h, r, f, g1, g2, u)).
        s: (H, R, F, G1, G2, U)
        """
        h, r, f, g1, g2, u = s
        
        if kind == EventKind.DRAIN_ANOMALY:
            if h == 3: return 0.92
            if r == 1: return 0.85 # Heavy rain explains drainage anomaly
            if h == 2: return 0.65
            if h == 1: return 0.40
            return 0.03

        elif kind == EventKind.TRAFFIC_SLOW:
            if h == 3: return 0.88
            if r == 1: return 0.70 # Heavy rain explains traffic slowdown
            if h == 2: return 0.30
            return 0.04

        elif kind == EventKind.CALL_SURGE:
            if h == 3: return 0.85
            if u == 1: return 0.85
            if r == 1: return 0.80 # Heavy storm explains emergency call surge
            if h == 2: return 0.35
            return 0.05

        elif kind == EventKind.DISPATCH_INCIDENT:
            # Dispatch verified: high under H3/H2, very low under noise/rumor/rain
            if h == 3: return 0.85
            if h == 2: return 0.70
            return 0.02

        elif kind == EventKind.HOSPITAL_ARRIVALS:
            # Hospital arrivals explained by cascade OR flu cluster
            if f == 1: return 0.85 # Flu cluster fully explains ER arrival surge
            if h == 3: return 0.80
            return 0.03

        elif kind == EventKind.CITIZEN_REPORT:
            if u == 1: return 0.85
            if h == 3: return 0.70
            if h == 2: return 0.40
            return 0.06

        elif kind == EventKind.CAMERA_FLAG:
            if h == 3: return 0.75
            if h == 2: return 0.60
            return 0.04

        elif kind == EventKind.RAIN_GAUGE:
            if r == 1: return 0.95
            return 0.02

        elif kind == EventKind.GATEWAY_HEARTBEAT:
            # Value < 0.5 represents heartbeat loss
            # Handled specifically in gateway logic
            return 0.50

        elif kind == EventKind.SOCIAL_POST:
            if u == 1: return 0.90
            if h == 3: return 0.65
            return 0.05

        return 0.05

    def compute_event_likelihood_vector(self, event: StreamEvent, reliability: float) -> np.ndarray:
        """
        Returns a vector of length 128: L(event | s) = r * L_true(event | s) + (1-r) * L_fault.
        """
        L = np.zeros(self.num_states, dtype=float)
        
        # Gateway outage special case
        if event.kind == EventKind.GATEWAY_HEARTBEAT:
            is_down = (event.value < 0.5)
            gw_id = event.gateway_id or "gw_1"
            for idx, s in enumerate(self.state_space.idx_to_tuple):
                h_val = s[0]
                g_val = s[3] if gw_id == "gw_1" else s[4]
                if is_down:
                    # Heartbeat loss indicates gateway down G_k=1 and H1 (SensorFailure)
                    if g_val == 1 and h_val == 1:
                        p = 0.98
                    elif g_val == 1:
                        p = 0.90
                    else:
                        p = 0.001
                else:
                    p = 0.98 if (g_val == 0 and h_val != 1) else 0.001
                L[idx] = reliability * p + (1.0 - reliability) * 0.01
            return L

        for idx, s in enumerate(self.state_space.idx_to_tuple):
            p_true = self.get_base_probability(event.kind, s)
            L[idx] = reliability * p_true + (1.0 - reliability) * self.fault_likelihood
            
        return L

    def audit_structured_lies(self, events: List[StreamEvent], current_minute: int, 
                              all_events_this_minute: List[StreamEvent]) -> Dict[str, float]:
        """
        Structured Lie Detection (Section 6.3 & Part B Section 25):
        Checks:
        1. Zero-variance / frozen reading (< 1e-4) with high anomaly (> 0.8)
        2. Physical contradiction (severe drain anomaly while rain=0 and normal traffic)
        3. Uncorroborated volume spike (>5x baseline without independent corroboration)
        Returns multiplier dictionary for suspicious groups.
        """
        multipliers: Dict[str, float] = {}

        # Update event buffers by group
        for ev in events:
            group_key = ev.gateway_id or ev.claim_id or ev.source_id
            if group_key not in self.recent_events_by_group:
                self.recent_events_by_group[group_key] = []
            self.recent_events_by_group[group_key].append(ev)
            # Retain only last 5 minutes
            self.recent_events_by_group[group_key] = [
                e for e in self.recent_events_by_group[group_key] 
                if (current_minute * 60) - e.event_time <= 300
            ]

        # Check conditions
        rain_gauge_events = [e for e in all_events_this_minute if e.kind == EventKind.RAIN_GAUGE]
        rain_is_dry = any(e.value < 0.1 for e in rain_gauge_events) if rain_gauge_events else False
        traffic_is_normal = not any(e.kind == EventKind.TRAFFIC_SLOW and e.value > 0.6 for e in all_events_this_minute)

        for group_key, grp_events in self.recent_events_by_group.items():
            # Check expiry
            if group_key in self.suspicious_groups:
                if current_minute >= self.suspicious_groups[group_key]:
                    del self.suspicious_groups[group_key]
                else:
                    multipliers[group_key] = 0.3
                    continue

            if len(grp_events) >= 3:
                vals = [e.value for e in grp_events]
                variance = float(np.var(vals))
                mean_val = float(np.mean(vals))
                
                # Check 1: Frozen high anomaly
                if variance < 1e-4 and mean_val > 0.8:
                    self.suspicious_groups[group_key] = current_minute + 10
                    multipliers[group_key] = 0.3
                    continue

                # Check 2: Physical contradiction
                has_drain = any(e.kind == EventKind.DRAIN_ANOMALY and e.value > 0.8 for e in grp_events)
                if has_drain and rain_is_dry and traffic_is_normal and len(rain_gauge_events) > 0:
                    self.suspicious_groups[group_key] = current_minute + 10
                    multipliers[group_key] = 0.3
                    continue

                # Check 3: Uncorroborated volume spike
                if len(grp_events) >= 15:
                    independent_kinds = {e.kind for e in all_events_this_minute if (e.gateway_id or e.claim_id) != group_key}
                    if len(independent_kinds) <= 1:
                        self.suspicious_groups[group_key] = current_minute + 10
                        multipliers[group_key] = 0.3
                        continue

        return multipliers

    def apply_dong_dependence_discounting(
        self, 
        group_events: List[StreamEvent], 
        base_reliability: float, 
        current_g_posteriors: Tuple[float, float],
        is_suspicious: bool
    ) -> np.ndarray:
        """
        Dong et al. (VLDB) Dependence Weighting:
        LLR_group(s) = (mean_i LLR_i(s)) * omega(n, rho)
        where omega(n, rho) = 1 + (1 - rho) * ln(n).
        If gateway is down, omega = 0.
        """
        n = len(group_events)
        if n == 0:
            return np.ones(self.num_states, dtype=float)

        first_ev = group_events[0]
        gw_id = first_ev.gateway_id
        
        # Check if gateway is down
        if gw_id == "gw_1" and current_g_posteriors[0] > 0.8:
            return np.ones(self.num_states, dtype=float)  # 0 evidence
        if gw_id == "gw_2" and current_g_posteriors[1] > 0.8:
            return np.ones(self.num_states, dtype=float)

        effective_reliability = base_reliability * (0.3 if is_suspicious else 1.0)
        
        # Determine intra-cluster correlation rho
        if first_ev.claim_id is not None:
            # Same rumor claim collapses to 1 claim
            rho = 1.0
            omega = 1.0
        elif gw_id is not None:
            # Physical sensors behind same gateway have correlation rho = 0.85
            rho = 0.85
            omega = 1.0 + (1.0 - rho) * np.log(max(1, n))
        else:
            rho = 0.0
            omega = float(n)

        # Baseline noise state (H=0, all nuisances=0)
        h0_idx = self.state_space.state_to_idx(0, 0, 0, 0, 0, 0)
        
        # Compute individual LLRs
        all_llrs = []
        for ev in group_events:
            L_vec = self.compute_event_likelihood_vector(ev, effective_reliability)
            L_h0 = max(1e-12, L_vec[h0_idx])
            llr = np.log(np.maximum(1e-12, L_vec) / L_h0)
            all_llrs.append(llr)

        mean_llr = np.mean(all_llrs, axis=0)
        group_llr = mean_llr * omega
        
        # If high-volume uncorroborated rumor spike (claim_id with n >= 5), strongly boost U=1 states
        if first_ev.claim_id is not None and n >= 5:
            for idx, s in enumerate(self.state_space.idx_to_tuple):
                if s[5] == 1:  # U=1
                    group_llr[idx] += min(6.0, 1.0 + 0.15 * n)

        # Convert back to likelihood factor relative to H0
        group_L = np.exp(group_llr)
        # Normalize scale to prevent overflow
        group_L /= np.max(group_L)
        return group_L

    def get_silence_likelihood_vector(self, current_minute: int, has_drain: bool, has_traffic: bool) -> np.ndarray:
        """
        Negative evidence (silence):
        If minute >= 5 and neither drainage nor traffic has appeared, H3 is heavily penalized.
        """
        L = np.ones(self.num_states, dtype=float)
        if current_minute >= 6 and not has_drain and not has_traffic:
            for idx, s in enumerate(self.state_space.idx_to_tuple):
                if s[0] == 3:  # H3
                    L[idx] = 0.40  # Decay H3 when expected signals fail to appear
        return L
