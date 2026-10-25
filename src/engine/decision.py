import numpy as np
from typing import Dict, List, Tuple
from src.schemas import ActionLevel

ACTION_ORDER = [ActionLevel.WATCH, ActionLevel.PREPARE, ActionLevel.ALERT, ActionLevel.ESCALATE]

class DecisionEngine:
    """
    Optimal Stopping Decision Layer:
    - Asymmetric Cost Matrix with Lead-Time Escalation
    - Cry-Wolf Fatigue Penalty (Frequency + False Alarms)
    - Shiryaev Bayesian Quickest Change Crossing Points
    - 200-Draw Monte Carlo Value-of-Waiting
    - Hysteresis & Anti-Flip-Flop Stability Controls
    """
    def __init__(self):
        self.fatigue = 0.0
        self.current_action = ActionLevel.WATCH
        self.minutes_at_current_action = 0
        self.downgrade_candidate_count = 0
        self.action_history: List[Tuple[int, ActionLevel]] = []
        self.recent_alerts_window: List[int] = [] # timestamps of ALERT/ESCALATE
        self.flip_flop_count = 0
        self.last_p_h3 = 0.0

    def compute_cost_matrix(self, minute: int, onset_minute: int, p_h3: float = 0.0) -> np.ndarray:
        """
        Computes 4x4 cost matrix: rows = [WATCH, PREPARE, ALERT, ESCALATE], cols = [H0, H1, H2, H3]
        Lead-time penalty activates when cascade is suspected (P(H3) >= 0.20).
        """
        lead_time = max(0, minute - onset_minute) if p_h3 >= 0.20 else 0
        lead_time_multiplier = 1.0 + 0.15 * lead_time
        fatigue_multiplier = 1.0 + 2.0 * self.fatigue

        matrix = np.array([
            # H0,                     H1,                     H2,                     H3
            [0.0,                    0.0,                    4.0,                    100.0 * lead_time_multiplier], # WATCH
            [1.0,                    1.0,                    2.0,                    40.0 * lead_time_multiplier],  # PREPARE
            [6.0 * fatigue_multiplier, 6.0 * fatigue_multiplier, 3.0 * fatigue_multiplier, 15.0 * lead_time_multiplier],  # ALERT
            [25.0 * fatigue_multiplier, 25.0 * fatigue_multiplier, 20.0 * fatigue_multiplier, 5.0 * lead_time_multiplier] # ESCALATE
        ], dtype=float)

        return matrix

    def compute_expected_costs(self, probs: np.ndarray, minute: int, onset_minute: int) -> Dict[str, float]:
        matrix = self.compute_cost_matrix(minute, onset_minute, probs[3])
        expected = matrix @ probs
        return {
            ActionLevel.WATCH.value: float(expected[0]),
            ActionLevel.PREPARE.value: float(expected[1]),
            ActionLevel.ALERT.value: float(expected[2]),
            ActionLevel.ESCALATE.value: float(expected[3]),
        }

    def compute_shiryaev_crossing_points(self, minute: int, onset_minute: int) -> Dict[str, float]:
        """
        Computes the theoretical crossing points for P(H3) assuming P(H2) = 0.
        """
        lead = 1.0 + 0.15 * max(0, minute - onset_minute)
        W = 1.0 + 2.0 * self.fatigue

        # WATCH vs PREPARE: 100 * lead * p = 1 * (1 - p) + 40 * lead * p
        # (60 * lead + 1) * p = 1 => p = 1 / (60 * lead + 1)
        p_watch_prep = 1.0 / (60.0 * lead + 1.0)

        # PREPARE vs ALERT: 1 + (40 lead - 1) p = 6W + (15 lead - 6W) p
        # (25 lead + 6W - 1) p = 6W - 1
        num_alert = 6.0 * W - 1.0
        den_alert = 25.0 * lead + 6.0 * W - 1.0
        p_prep_alert = num_alert / den_alert if den_alert > 0 else 0.17

        # ALERT vs ESCALATE: 6W + (15 lead - 6W) p = 25W + (5 lead - 25W) p
        # (10 lead + 19W) p = 19W
        num_esc = 19.0 * W
        den_esc = 10.0 * lead + 19.0 * W
        p_alert_esc = num_esc / den_esc if den_esc > 0 else 0.66

        return {
            "WATCH_to_PREPARE": float(p_watch_prep),
            "PREPARE_to_ALERT": float(p_prep_alert),
            "ALERT_to_ESCALATE": float(p_alert_esc)
        }

    def evaluate_value_of_waiting(
        self, 
        probs: np.ndarray, 
        minute: int, 
        onset_minute: int, 
        raw_best_action: ActionLevel,
        current_min_cost: float,
        num_simulations: int = 200
    ) -> float:
        """
        Value-of-Waiting (1-Step Monte Carlo Lookahead):
        Simulates 200 synthetic belief perturbations at t+1.
        Returns expected cost savings from waiting 1 minute.
        """
        # If already ESCALATE-worthy, do not delay
        if raw_best_action == ActionLevel.ESCALATE:
            return 0.0

        p_h3 = probs[3]
        matrix_next = self.compute_cost_matrix(minute + 1, onset_minute, p_h3)

        # Vectorized 200-draw Monte Carlo lookahead
        is_cascade = (np.random.rand(num_simulations) < p_h3)
        deltas = np.where(
            is_cascade, 
            np.random.normal(0.08, 0.03, num_simulations), 
            np.random.normal(-0.04, 0.02, num_simulations)
        )
        sim_p3 = np.clip(p_h3 + deltas, 0.01, 0.98)
        sim_p0 = (1.0 - sim_p3) * 0.7
        sim_p1 = (1.0 - sim_p3) * 0.1
        sim_p2 = (1.0 - sim_p3) * 0.2
        sim_probs = np.vstack([sim_p0, sim_p1, sim_p2, sim_p3])  # Shape: (4, num_simulations)
        
        ec_next = matrix_next @ sim_probs  # Shape: (4, num_simulations)
        min_ec_next = np.min(ec_next, axis=0)
        expected_cost_wait = float(np.mean(min_ec_next))
        savings = current_min_cost - expected_cost_wait
        return max(0.0, savings)

    def select_action(
        self, 
        probs: np.ndarray, 
        minute: int, 
        onset_minute: int = 0,
        independent_physical_confirmations: int = 0
    ) -> Tuple[ActionLevel, Dict[str, float], float]:
        """
        Selects stable recommended action subject to hysteresis and minimum dwell time.
        In ambiguous prefix (minute <= 7 without >= 2 hard physical confirmations),
        caps recommendation at PREPARE to avoid crying wolf.
        """
        ec_dict = self.compute_expected_costs(probs, minute, onset_minute)
        
        # Raw best action
        raw_best_str = min(ec_dict.keys(), key=lambda k: ec_dict[k])
        raw_best_action = ActionLevel(raw_best_str)
        raw_min_cost = ec_dict[raw_best_str]

        # Prevent premature commitments during ambiguous prefix
        if minute <= 7 and independent_physical_confirmations < 2:
            if ACTION_ORDER.index(raw_best_action) > ACTION_ORDER.index(ActionLevel.PREPARE):
                raw_best_action = ActionLevel.PREPARE
                raw_min_cost = ec_dict[ActionLevel.PREPARE.value]

        curr_cost = ec_dict[self.current_action.value]
        curr_idx = ACTION_ORDER.index(self.current_action)
        raw_idx = ACTION_ORDER.index(raw_best_action)

        # Value of waiting lookahead
        vow_saved = self.evaluate_value_of_waiting(
            probs, minute, onset_minute, raw_best_action, raw_min_cost
        )

        p_h3 = probs[3]
        delta_p_h3 = p_h3 - self.last_p_h3
        self.last_p_h3 = p_h3

        next_action = self.current_action

        # Upgrade Logic (Fast Commit)
        if raw_idx > curr_idx:
            cost_advantage = curr_cost - raw_min_cost
            dwell_satisfied = (self.minutes_at_current_action >= 3)
            fast_bypass = (delta_p_h3 > 0.25) # immediate bypass on sharp surge
            
            # If value of waiting is substantial and action is ALERT, delay upgrade
            should_wait = (vow_saved > 2.0 and raw_best_action == ActionLevel.ALERT and not fast_bypass)

            if cost_advantage >= 3.0 and (dwell_satisfied or fast_bypass) and not should_wait:
                next_action = raw_best_action
                self.minutes_at_current_action = 0
                self.downgrade_candidate_count = 0

        # Downgrade Logic (Slow Relaxation)
        elif raw_idx < curr_idx:
            cost_advantage = curr_cost - raw_min_cost
            if cost_advantage >= 8.0:
                self.downgrade_candidate_count += 1
                if self.downgrade_candidate_count >= 3:
                    next_action = raw_best_action
                    self.minutes_at_current_action = 0
                    self.downgrade_candidate_count = 0
            else:
                self.downgrade_candidate_count = 0
        else:
            self.downgrade_candidate_count = 0

        if next_action == self.current_action:
            self.minutes_at_current_action += 1
        else:
            # Audit flip-flop
            self._audit_flip_flop(minute, next_action)
            self.current_action = next_action

        # Record action in history
        self.action_history.append((minute, self.current_action))
        if self.current_action in (ActionLevel.ALERT, ActionLevel.ESCALATE):
            self.recent_alerts_window.append(minute)
            # Retain alerts in past 20 min
            self.recent_alerts_window = [m for m in self.recent_alerts_window if minute - m <= 20]

        # Update fatigue
        freq_penalty = (0.05 if len(self.recent_alerts_window) > 2 else 0.0)
        self.fatigue = float(np.clip(self.fatigue - 0.02 + freq_penalty, 0.0, 1.0))

        return self.current_action, ec_dict, vow_saved

    def register_false_alarm(self):
        """Called when an ALERT/ESCALATE is logged for an episode that is confirmed non-cascade."""
        self.fatigue = float(np.clip(self.fatigue + 0.15, 0.0, 1.0))

    def _audit_flip_flop(self, minute: int, new_action: ActionLevel):
        """
        Flip-flop defined as any sequence (X -> lower -> X) within 10 minutes.
        """
        recent = [a for m, a in self.action_history if minute - m <= 10]
        if len(recent) >= 2:
            prev_act = recent[-1]
            if ACTION_ORDER.index(prev_act) < ACTION_ORDER.index(new_action):
                # We are upgrading. Did we hold this action or higher in the last 10 min?
                earlier = [a for a in recent[:-1] if ACTION_ORDER.index(a) >= ACTION_ORDER.index(new_action)]
                if len(earlier) > 0:
                    self.flip_flop_count += 1
