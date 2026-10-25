import numpy as np
from typing import Dict, List, Tuple, Any
from src.schemas import StreamEvent, ActionLevel, EventKind

class ExplainabilityBuilder:
    """
    Constructs the auditable explainability ledger per minute:
    1. Signed Log-Likelihood Ratio (LLR) drivers
    2. Discounted items list with reasons
    3. Explaining-away attribution percentages
    4. Action decision rationale
    5. Counterfactual 'What would change my mind'
    """
    @staticmethod
    def build_explanation(
        minute: int,
        prev_p_h3: float,
        curr_p_h3: float,
        action: ActionLevel,
        expected_costs: Dict[str, float],
        nuisances: Dict[str, float],
        discounted_items: List[str],
        top_events: List[StreamEvent]
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        # 1. Top drivers
        drivers = []
        for ev in top_events[:3]:
            # Approximate signed LLR contribution
            if ev.kind in (EventKind.DRAIN_ANOMALY, EventKind.TRAFFIC_SLOW, EventKind.DISPATCH_INCIDENT):
                llr = round(np.log(ev.value / 0.1), 2)
                drivers.append({
                    "source": f"{ev.source_type.value} ({ev.source_id})",
                    "kind": ev.kind.value,
                    "llr": llr,
                    "direction": "positive" if llr > 0 else "negative"
                })
            elif ev.kind == EventKind.RAIN_GAUGE:
                drivers.append({
                    "source": "Rain Gauge",
                    "kind": "rain_confirmation",
                    "llr": -0.85,
                    "direction": "explaining_away"
                })

        # 2. Explaining away note
        explaining_notes = []
        if nuisances.get("R", 0.0) > 0.40:
            pct = int(min(95, nuisances["R"] * 100))
            explaining_notes.append(f"Drainage and traffic anomalies are {pct}% explained by heavy rain.")
        if nuisances.get("F", 0.0) > 0.40:
            pct = int(min(95, nuisances["F"] * 100))
            explaining_notes.append(f"Hospital arrivals are {pct}% explained by seasonal flu cluster.")
        if nuisances.get("U", 0.0) > 0.40:
            pct = int(min(95, nuisances["U"] * 100))
            explaining_notes.append(f"Citizen and social reports are {pct}% explained by viral rumor surge.")
        if nuisances.get("G1", 0.0) > 0.60:
            explaining_notes.append("Gateway 1 outage masking 100 downstream sensors.")

        explaining_text = " ".join(explaining_notes) if explaining_notes else "No strong nuisance factor active."

        # 3. Decision rationale
        min_cost = expected_costs[action.value]
        sorted_costs = sorted(expected_costs.items(), key=lambda x: x[1])
        runner_up = sorted_costs[1]
        cost_diff = round(runner_up[1] - min_cost, 2)
        
        summary = (
            f"Action: {action.value} (P(H3): {round(prev_p_h3, 2)} -> {round(curr_p_h3, 2)}). "
            f"Expected cost {round(min_cost, 2)} vs {runner_up[0]} ({round(runner_up[1], 2)}, saving {cost_diff} units). "
            f"{explaining_text}"
        )

        # 4. What would change my mind
        if action in (ActionLevel.WATCH, ActionLevel.PREPARE):
            if curr_p_h3 < 0.20:
                mind_change = "Would move to PREPARE if two independent physical sensors (drainage + arterial traffic) confirm sustained anomaly."
            else:
                mind_change = "Would escalate to ALERT if an independent emergency dispatch incident confirms road blockage or if rain is ruled out."
        elif action == ActionLevel.ALERT:
            mind_change = "Would escalate to ESCALATE if ambulance delays exceed 4 minutes and hospital arrival surges are verified non-flu."
        else:
            mind_change = "Would de-escalate to ALERT if traffic flow returns to baseline or if a key incident report is retracted."

        return summary, drivers, mind_change
