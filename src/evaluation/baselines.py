import numpy as np
from typing import Dict, List, Tuple
from src.schemas import StreamEvent, ActionLevel, EventKind

class ThresholdRuleBaseline:
    """
    Baseline 1: Threshold Rule
    Alert if >= 3 anomalies within the last 5 minutes.
    Escalate if >= 8 anomalies within the last 5 minutes.
    """
    def __init__(self):
        self.window_events: List[StreamEvent] = []

    def process_minute(self, minute: int, events: List[StreamEvent]) -> Tuple[ActionLevel, float]:
        # Append events
        for e in events:
            if e.value >= 0.5:
                self.window_events.append(e)

        # Retain last 5 minutes (300 sec)
        cutoff = minute * 60 - 300
        self.window_events = [e for e in self.window_events if e.event_time >= cutoff]
        
        count = len(self.window_events)
        if count >= 8:
            action = ActionLevel.ESCALATE
            p_h3 = 0.85
        elif count >= 3:
            action = ActionLevel.ALERT
            p_h3 = 0.55
        elif count >= 1:
            action = ActionLevel.PREPARE
            p_h3 = 0.25
        else:
            action = ActionLevel.WATCH
            p_h3 = 0.05

        return action, p_h3

class NaiveBayesBaseline:
    """
    Baseline 2: Naive Bayes
    Treats all incoming events as independent and equally reliable (r = 0.8).
    Multiplies likelihoods directly with no common-cause discounting and no nuisance explaining away.
    """
    def __init__(self):
        # Prior over H: H0, H1, H2, H3
        self.log_probs = np.log([0.60, 0.15, 0.15, 0.10])

    def process_minute(self, minute: int, events: List[StreamEvent]) -> Tuple[ActionLevel, np.ndarray]:
        # CPT approximations without nuisances
        for ev in events:
            if ev.kind == EventKind.DRAIN_ANOMALY:
                l = np.array([0.05, 0.40, 0.65, 0.90])
            elif ev.kind == EventKind.TRAFFIC_SLOW:
                l = np.array([0.04, 0.20, 0.30, 0.88])
            elif ev.kind == EventKind.DISPATCH_INCIDENT:
                l = np.array([0.02, 0.05, 0.70, 0.85])
            elif ev.kind == EventKind.HOSPITAL_ARRIVALS:
                l = np.array([0.03, 0.05, 0.20, 0.80])
            else:
                l = np.array([0.05, 0.05, 0.05, 0.05])
            
            # Equal reliability r = 0.8
            l_adj = 0.8 * l + 0.2 * 0.25
            self.log_probs += np.log(l_adj)

        # Softmax normalize
        max_log = np.max(self.log_probs)
        probs = np.exp(self.log_probs - max_log)
        probs /= np.sum(probs)

        # Static threshold mapping
        p3 = probs[3]
        if p3 >= 0.65:
            action = ActionLevel.ESCALATE
        elif p3 >= 0.25:
            action = ActionLevel.ALERT
        elif p3 >= 0.10:
            action = ActionLevel.PREPARE
        else:
            action = ActionLevel.WATCH

        return action, probs

class ShiryaevSingleThresholdBaseline:
    """
    Baseline 4 (Part B Section 22.3): Single-Threshold Shiryaev Quickest Change Detector
    Triggers ALERT as soon as posterior P(H3) exceeds the worked crossing point pi* = 0.167.
    Has no hysteresis, no value-of-waiting, and no lead-time multiplier.
    """
    def __init__(self):
        self.current_action = ActionLevel.WATCH
        self.pi_star = 0.1667

    def process_minute(self, minute: int, p_h3: float) -> ActionLevel:
        if p_h3 >= 0.655:
            self.current_action = ActionLevel.ESCALATE
        elif p_h3 >= self.pi_star:
            self.current_action = ActionLevel.ALERT
        elif p_h3 >= 0.016:
            self.current_action = ActionLevel.PREPARE
        else:
            self.current_action = ActionLevel.WATCH
        return self.current_action
