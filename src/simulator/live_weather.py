import os
import json
import time
import requests
from typing import Dict, List, Optional, Any, Tuple
from src.schemas import StreamEvent, EventKind, SourceType

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_LAT = 21.1458  # Nagpur, India
DEFAULT_LON = 79.0882

CITY_PRESETS = {
    "Nagpur, India": (21.1458, 79.0882),
    "Mumbai, India": (19.0760, 72.8777),
    "Bengaluru, India": (12.9716, 77.5946),
    "New Delhi, India": (28.6139, 77.2090),
    "Berlin, Germany": (52.5200, 13.4050),
    "New York, USA": (40.7128, -74.0060),
    "Tokyo, Japan": (35.6762, 139.6503),
    "London, UK": (51.5074, -0.1278),
}


def fetch_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, timeout: int = 5) -> Dict[str, Any]:
    """
    Fetches real-time 15-minute precipitation telemetry from Open-Meteo.
    Requires no API key.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,rain,wind_speed_10m",
        "minutely_15": "precipitation",
        "past_minutely_15": 4,      # Last hour of 15-min buckets
        "forecast_minutely_15": 4,  # Next hour forecast
        "timezone": "auto",
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def to_events(
    payload: Dict[str, Any], 
    last_ts_seen: str = "", 
    current_minute: int = 1
) -> Tuple[List[StreamEvent], str]:
    """
    Transforms 15-minute Open-Meteo precipitation buckets into discrete StreamEvents.
    
    Guarantees:
    - Avoids faking per-minute precision: emits exactly one event per new 15-min bucket.
    - Converts bucket mm to standard rain gauge rate (mm/h = bucket_mm * 4.0).
    - Deduplicates by timestamp string so repeated polling does not create duplicates.
    """
    events: List[StreamEvent] = []
    minutely = payload.get("minutely_15", {})
    times = minutely.get("time", [])
    vals = minutely.get("precipitation", [])
    
    newest_ts = last_ts_seen

    for t_str, v in zip(times, vals):
        if v is None or t_str <= last_ts_seen:
            continue
        
        mm_per_h = float(v) * 4.0  # Convert 15-min rainfall to mm/h
        
        # Deduplication tracking
        if t_str > newest_ts:
            newest_ts = t_str

        # Generate StreamEvent with continuous precipitation rate (mm/h)
        clean_id = t_str.replace("-", "").replace(":", "").replace("T", "_")
        ev = StreamEvent(
            id=f"meteo_{clean_id}",
            source_id="open_meteo",
            source_type=SourceType.RAIN,
            event_time=current_minute * 60 + 5,
            arrival_time=current_minute * 60 + 10,
            kind=EventKind.RAIN_GAUGE,
            value=round(mm_per_h, 2),
            location=f"meteo_grid_{payload.get('latitude', 0):.2f}_{payload.get('longitude', 0):.2f}",
            is_anomaly=(mm_per_h > 15.0)  # >15 mm/h classified as heavy cloudburst
        )
        events.append(ev)

    return events, newest_ts


class LiveWeatherFeed:
    """
    Manages live or offline-replayed Open-Meteo precipitation stream for CrisisSense.
    
    Features:
    - Deduplication by 15-minute bucket timestamp.
    - Stale / Missing status on API timeout or failure (matching sensor cutout protocol).
    - Rolling rain rate history for BOCD / CUSUM monsoon regime shift detection.
    - Offline fixture replay mode for deterministic CI/CD testing.
    """

    def __init__(self, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
        self.lat = lat
        self.lon = lon
        self.last_ts_seen: str = ""
        self.is_stale: bool = False
        self.last_poll_time: float = 0.0
        self.current_rate_mm_h: float = 0.0
        self.rolling_history: List[float] = []
        self.poll_interval_sec: int = 300  # Poll every 5 minutes
        self.fixture_payload: Optional[Dict[str, Any]] = None
        self.fail_on_poll: bool = False

    def load_fixture(self, fixture_path: str):
        """Loads an offline Open-Meteo JSON response fixture."""
        with open(fixture_path, "r", encoding="utf-8") as f:
            self.fixture_payload = json.load(f)

    def set_offline_failure(self, should_fail: bool = True):
        """Simulates API timeout / network loss mid-episode."""
        self.fail_on_poll = should_fail

    def poll(self, current_minute: int = 1, force: bool = False) -> List[StreamEvent]:
        """
        Polls for new 15-minute weather buckets.
        Returns empty list and marks source stale on network failure.
        """
        now = time.time()
        # Rate limit to once per interval unless forced or running simulated offline
        if not force and self.fixture_payload is None:
            if (now - self.last_poll_time) < self.poll_interval_sec and self.last_ts_seen:
                return []

        self.last_poll_time = now

        # 1. Simulated failure injection
        if self.fail_on_poll:
            self.is_stale = True
            return []

        # 2. Fetch payload (offline fixture or live API)
        try:
            if self.fixture_payload is not None:
                payload = self.fixture_payload
            else:
                payload = fetch_weather(self.lat, self.lon, timeout=5)

            events, newest_ts = to_events(payload, self.last_ts_seen, current_minute=current_minute)
            self.last_ts_seen = newest_ts
            self.is_stale = False

            if events:
                # Update current rate from newest event and add all bucket rates to rolling history
                self.current_rate_mm_h = events[-1].value
                for ev in events:
                    self.rolling_history.append(ev.value)
                    if len(self.rolling_history) > 20:
                        self.rolling_history.pop(0)

            return events

        except Exception:
            # On failure, do NOT emit fake "0 mm"; mark source as stale (missing event)
            self.is_stale = True
            return []

    def get_rolling_average_rain(self) -> float:
        """Returns the rolling average precipitation in mm/h."""
        if not self.rolling_history:
            return 0.0
        return float(sum(self.rolling_history) / len(self.rolling_history))
