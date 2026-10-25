from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class SourceType(str, Enum):
    DRAINAGE = "drainage_sensors"
    TRAFFIC = "traffic_sensors"
    RAIN = "rain_gauges"
    EMERGENCY_LINES = "emergency_lines"
    DISPATCH = "dispatch_logs"
    HOSPITALS = "hospitals"
    CAMERAS = "cameras"
    CITIZEN = "citizen_reports"
    SOCIAL = "social_rumor"

class EventKind(str, Enum):
    DRAIN_ANOMALY = "drain_anomaly"
    TRAFFIC_SLOW = "traffic_slow"
    CALL_SURGE = "call_surge"
    DISPATCH_INCIDENT = "dispatch_incident"
    HOSPITAL_ARRIVALS = "hospital_arrivals"
    CITIZEN_REPORT = "citizen_report"
    CAMERA_FLAG = "camera_flag"
    RAIN_GAUGE = "rain_gauge"
    GATEWAY_HEARTBEAT = "gateway_heartbeat"
    SOCIAL_POST = "social_post"

class ActionLevel(str, Enum):
    WATCH = "WATCH"
    PREPARE = "PREPARE"
    ALERT = "ALERT"
    ESCALATE = "ESCALATE"

class StreamEvent(BaseModel):
    id: str
    source_id: str
    source_type: SourceType
    event_time: int = Field(..., description="Simulated event time in seconds (minute * 60 + sec)")
    arrival_time: int = Field(..., description="Simulated arrival time in seconds")
    kind: EventKind
    value: float = Field(..., ge=0.0, le=1.0)
    location: str
    gateway_id: Optional[str] = None
    claim_id: Optional[str] = None
    retracts: Optional[str] = None
    dup_of: Optional[str] = None
    is_anomaly: bool = True

class ForecastItem(BaseModel):
    event_kind: str
    zone: str
    window_start_min: int
    window_end_min: int
    probability: float
    expected_delay_min: float
    description: str

class CAPAlertInfo(BaseModel):
    category: str = "Safety"
    event: str = "Urban Cascading Infrastructure Failure"
    urgency: str
    severity: str
    certainty: str
    headline: str
    description: str
    area_desc: str
    recommended_action: str

class CAPAlert(BaseModel):
    identifier: str
    sender: str = "duty-officer@crisissense.gov"
    sent: str
    status: str = "Exercise"  # Mandated safety guarantee
    msg_type: str = "Alert"   # Alert, Update, Cancel
    scope: str = "Restricted"
    info: CAPAlertInfo

class MinuteStatePayload(BaseModel):
    minute: int
    probabilities: Dict[str, float]          # H0, H1, H2, H3
    uncertainty_band: Dict[str, List[float]] # [low, high] per H
    nuisance_posteriors: Dict[str, float]    # R, F, G1, G2, U
    recommended_action: ActionLevel
    expected_costs: Dict[str, float]         # WATCH, PREPARE, ALERT, ESCALATE
    value_of_waiting_saved: float
    fatigue_level: float
    forecasts: List[ForecastItem]            # Top 3 next events
    source_trust: Dict[str, float]           # Beta mean per source_type
    blind_sources: List[str]
    explanation_summary: str
    top_drivers: List[Dict[str, Any]]
    discounted_items: List[str]
    what_would_change_mind: str
    flip_flop_count: int
    regime_shift_detected: bool
    temperature: float = 1.0
    cap_alert: Optional[CAPAlert] = None
