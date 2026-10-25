import datetime
from typing import Dict, List, Optional
from xml.sax.saxutils import escape
from src.schemas import ActionLevel, CAPAlert, CAPAlertInfo

class CAPAlertBuilder:
    """
    Constructs compliant OASIS / WMO Common Alerting Protocol (CAP v1.2) payloads.
    Guarantees status is strictly 'Exercise' (simulated recommendation).
    """
    @staticmethod
    def build_cap_alert(
        minute: int,
        action: ActionLevel,
        p_h3: float,
        top_zone: str = "Metro Central & North Sector",
        top_driver: str = "Drainage Overflow & Arterial Congestion"
    ) -> Optional[CAPAlert]:
        # Only issue formal CAP alerts for PREPARE, ALERT, or ESCALATE
        if action == ActionLevel.WATCH:
            return None

        # Urgency mapping
        urgency_map = {
            ActionLevel.ESCALATE: "Immediate",
            ActionLevel.ALERT: "Expected",
            ActionLevel.PREPARE: "Future",
            ActionLevel.WATCH: "Past"
        }
        urgency = urgency_map.get(action, "Expected")

        # Severity mapping
        if p_h3 >= 0.65:
            severity = "Extreme"
        elif p_h3 >= 0.40:
            severity = "Severe"
        elif p_h3 >= 0.15:
            severity = "Moderate"
        else:
            severity = "Minor"

        # Certainty mapping
        if p_h3 >= 0.80:
            certainty = "Observed"
        elif p_h3 >= 0.50:
            certainty = "Likely"
        elif p_h3 >= 0.20:
            certainty = "Possible"
        else:
            certainty = "Unlikely"

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        identifier = f"CrisisSense-2026-EX-M{minute}-{int(p_h3*100)}"

        headline = f"CrisisSense Advisory: {action.value} — Cascade Probability {round(p_h3*100, 1)}%"
        description = (
            f"Automated decision engine recommends {action.value}. Primary driver: {top_driver}. "
            f"Simulated minute {minute}. All response agencies initiate {action.value} protocol."
        )

        info = CAPAlertInfo(
            category="Safety",
            event="Urban Cascading Infrastructure Anomaly",
            urgency=urgency,
            severity=severity,
            certainty=certainty,
            headline=headline,
            description=description,
            area_desc=top_zone,
            recommended_action=action.value
        )

        return CAPAlert(
            identifier=identifier,
            sender="duty-officer@crisissense.gov",
            sent=now_iso,
            status="Exercise",  # Crucial safety guarantee
            msg_type="Alert" if action in (ActionLevel.ALERT, ActionLevel.ESCALATE) else "Update",
            scope="Restricted",
            info=info
        )

    @staticmethod
    def to_xml(alert: CAPAlert) -> str:
        """Converts CAPAlert to XML string."""
        info = alert.info
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
    <identifier>{escape(alert.identifier)}</identifier>
    <sender>{escape(alert.sender)}</sender>
    <sent>{escape(alert.sent)}</sent>
    <status>{escape(alert.status)}</status>
    <msgType>{escape(alert.msg_type)}</msgType>
    <scope>{escape(alert.scope)}</scope>
    <info>
        <category>{escape(info.category)}</category>
        <event>{escape(info.event)}</event>
        <urgency>{escape(info.urgency)}</urgency>
        <severity>{escape(info.severity)}</severity>
        <certainty>{escape(info.certainty)}</certainty>
        <headline>{escape(info.headline)}</headline>
        <description>{escape(info.description)}</description>
        <area>
            <areaDesc>{escape(info.area_desc)}</areaDesc>
        </area>
    </info>
</alert>"""
        return xml
