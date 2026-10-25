import numpy as np
from typing import Dict, List, Tuple, Any

class EvaluationMetrics:
    """
    Computes rigorous statistical performance metrics:
    - 4-class Brier Score
    - 10-bin Expected Calibration Error (ECE) & Reliability Diagrams
    - False ESCALATE & Missed Cascade rates
    - Detection Lead Time
    - Flip-flop action instability
    - Delay vs False Alarm Tradeoff Curve
    """
    @staticmethod
    def compute_brier_score(predictions: List[np.ndarray], ground_truths: List[int]) -> float:
        """
        predictions: list of length N, each shape (4,)
        ground_truths: list of length N, each integer 0..3
        """
        if not predictions:
            return 0.0
        n = len(predictions)
        total_sq_err = 0.0
        for p, y in zip(predictions, ground_truths):
            one_hot = np.zeros(4, dtype=float)
            one_hot[y] = 1.0
            total_sq_err += np.sum((p - one_hot) ** 2)
        return float(total_sq_err / n)

    @staticmethod
    def compute_ece(confidences: List[float], accuracies: List[bool], num_bins: int = 10) -> Tuple[float, Dict[str, Any]]:
        """
        10-bin Expected Calibration Error (ECE):
        ECE = sum_m (|B_m| / N) * |acc(B_m) - conf(B_m)|
        """
        if not confidences:
            return 0.0, {"bins": []}

        confs = np.array(confidences)
        accs = np.array(accuracies, dtype=float)
        n = len(confs)

        bins = np.linspace(0.0, 1.0, num_bins + 1)
        ece = 0.0
        diagram_data = []

        for i in range(num_bins):
            b_low, b_high = bins[i], bins[i+1]
            in_bin = (confs >= b_low) & (confs < b_high if i < num_bins - 1 else confs <= b_high)
            bin_size = int(np.sum(in_bin))

            if bin_size > 0:
                bin_acc = float(np.mean(accs[in_bin]))
                bin_conf = float(np.mean(confs[in_bin]))
                weight = bin_size / n
                ece += weight * abs(bin_acc - bin_conf)
                diagram_data.append({
                    "bin_low": round(b_low, 2),
                    "bin_high": round(b_high, 2),
                    "accuracy": round(bin_acc, 3),
                    "confidence": round(bin_conf, 3),
                    "count": bin_size
                })
            else:
                diagram_data.append({
                    "bin_low": round(b_low, 2),
                    "bin_high": round(b_high, 2),
                    "accuracy": 0.0,
                    "confidence": (b_low + b_high) / 2.0,
                    "count": 0
                })

        return float(ece), {"bins": diagram_data}

    @staticmethod
    def compute_delay_vs_false_alarm_curve(
        cascade_episodes_data: List[Dict[str, Any]], 
        non_cascade_episodes_data: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        """
        Sweeps decision threshold from 0.05 to 0.95 to plot
        detection delay vs false alarm rate Pareto frontier.
        """
        thresholds = np.linspace(0.05, 0.95, 19)
        curve = []

        for th in thresholds:
            delays = []
            false_alarms = 0

            # Evaluate delay on cascade episodes
            for ep in cascade_episodes_data:
                onset = ep["onset_minute"]
                probs_h3 = ep["p_h3_sequence"]
                alert_min = None
                for m, p in enumerate(probs_h3, start=1):
                    if p >= th:
                        alert_min = m
                        break
                if alert_min is not None:
                    delays.append(max(0, alert_min - onset))
                else:
                    delays.append(30 - onset) # Max penalty for missed

            # Evaluate false alarms on non-cascade episodes
            for ep in non_cascade_episodes_data:
                probs_h3 = ep["p_h3_sequence"]
                if any(p >= th for p in probs_h3):
                    false_alarms += 1

            fa_rate = false_alarms / max(1, len(non_cascade_episodes_data))
            mean_delay = float(np.mean(delays)) if delays else 0.0

            curve.append({
                "threshold": round(float(th), 2),
                "false_alarm_rate": round(fa_rate, 3),
                "mean_delay_minutes": round(mean_delay, 2)
            })

        return curve
