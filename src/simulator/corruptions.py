import random
import copy
from typing import List, Dict, Optional
from src.schemas import StreamEvent, SourceType, EventKind

class StreamCorruptor:
    """
    Applies synthetic stream corruptions:
    - Out-of-order time jitter
    - Exact & fuzzy duplicates
    - Retraction events
    - Structured lies (frozen values, contradictions)
    - Gateway failures (100 sensors masked)
    - Camera cutouts
    """
    def __init__(self, rng_seed: int = 42, seed: Optional[int] = None):
        if seed is not None:
            rng_seed = seed
        self.rng = random.Random(rng_seed)

    def inject_delays(self, events: List[StreamEvent], max_delay_sec: int = 180) -> List[StreamEvent]:
        """Shuffles arrival_time while preserving event_time."""
        corrupted = []
        for ev in events:
            ev_copy = copy.deepcopy(ev)
            # Dispatch logs delayed 60-180s; citizen reports delayed 0-240s
            if ev.source_type == SourceType.DISPATCH:
                delay = self.rng.randint(60, 180)
            elif ev.source_type == SourceType.CITIZEN:
                delay = self.rng.randint(0, 240)
            else:
                delay = self.rng.randint(0, 30)
            ev_copy.arrival_time = ev_copy.event_time + delay
            corrupted.append(ev_copy)
        return corrupted

    def inject_duplicates(self, events: List[StreamEvent], dup_fraction: float = 0.10) -> List[StreamEvent]:
        """Injects exact and fuzzy duplicates."""
        output = list(events)
        n_dups = int(len(events) * dup_fraction)
        if not events or n_dups == 0:
            return output

        sample_targets = self.rng.sample(events, min(n_dups, len(events)))
        for idx, target in enumerate(sample_targets):
            # 50% exact dup, 50% fuzzy dup
            if self.rng.random() < 0.5:
                # Exact duplicate with same ID
                output.append(copy.deepcopy(target))
            else:
                # Fuzzy duplicate within 60s
                fuzzy = copy.deepcopy(target)
                fuzzy.id = f"fuzzy_dup_{idx}_{target.id}"
                fuzzy.dup_of = target.id
                fuzzy.event_time = min(1799, target.event_time + self.rng.randint(10, 60))
                fuzzy.arrival_time = fuzzy.event_time + 5
                output.append(fuzzy)
        return output

    def inject_retractions(self, events: List[StreamEvent], retract_fraction: float = 0.05) -> List[StreamEvent]:
        """Injects retraction events targeting previously sent events."""
        output = list(events)
        n_retracts = max(1, int(len(events) * retract_fraction))
        candidates = [e for e in events if e.kind in (EventKind.DISPATCH_INCIDENT, EventKind.CITIZEN_REPORT)]
        if not candidates:
            return output

        targets = self.rng.sample(candidates, min(n_retracts, len(candidates)))
        for idx, target in enumerate(targets):
            retract_ev = StreamEvent(
                id=f"retract_for_{target.id}",
                source_id=f"system_retractor_{idx}",
                source_type=target.source_type,
                event_time=min(1799, target.event_time + 120), # Arrives 2 min later
                arrival_time=min(1799, target.event_time + 125),
                kind=target.kind,
                value=0.0,
                location=target.location,
                retracts=target.id,
                is_anomaly=False
            )
            output.append(retract_ev)
        return output

    def inject_gateway_failure(
        self, 
        gateway_id: str = "gw_1", 
        num_sensors: int = 100, 
        failure_minute: int = 4
    ) -> List[StreamEvent]:
        """
        Simulates Gateway drop: 1 heartbeat loss event + 100 downstream sensors emitting silence/stuck noise.
        """
        events = []
        # Heartbeat loss
        events.append(StreamEvent(
            id=f"gw_hb_loss_{gateway_id}",
            source_id=f"controller_{gateway_id}",
            source_type=SourceType.DRAINAGE,
            event_time=failure_minute * 60 + 5,
            arrival_time=failure_minute * 60 + 6,
            kind=EventKind.GATEWAY_HEARTBEAT,
            value=0.0, # 0.0 = Heartbeat Lost
            location="infrastructure_core",
            gateway_id=gateway_id,
            is_anomaly=True
        ))
        
        # 100 downstream sensors
        for i in range(num_sensors):
            sec = self.rng.randint(10, 50)
            events.append(StreamEvent(
                id=f"gw_down_sensor_{gateway_id}_{i}",
                source_id=f"sensor_{gateway_id}_{i}",
                source_type=SourceType.DRAINAGE if i % 2 == 0 else SourceType.TRAFFIC,
                event_time=failure_minute * 60 + sec,
                arrival_time=failure_minute * 60 + sec + 2,
                kind=EventKind.DRAIN_ANOMALY if i % 2 == 0 else EventKind.TRAFFIC_SLOW,
                value=0.92, # High stuck reading
                location=f"sector_{i % 5}",
                gateway_id=gateway_id,
                is_anomaly=True
            ))
        return events

    def inject_structured_lie(
        self, 
        minute: int = 6, 
        num_sensors: int = 20
    ) -> List[StreamEvent]:
        """
        Injects a structured lie: 20 sensors reporting identical frozen value 0.9500
        while rain gauge reads 0.0.
        """
        events = []
        for i in range(num_sensors):
            events.append(StreamEvent(
                id=f"lie_sensor_{minute}_{i}",
                source_id=f"rogue_sensor_{i}",
                source_type=SourceType.DRAINAGE,
                event_time=minute * 60 + 15,
                arrival_time=minute * 60 + 17,
                kind=EventKind.DRAIN_ANOMALY,
                value=0.9500, # Identical frozen value (var = 0.0)
                location="zone_north",
                gateway_id="gw_lie",
                is_anomaly=True
            ))
        # Dry rain gauge
        events.append(StreamEvent(
            id=f"rain_truth_{minute}",
            source_id="rain_gauge_official",
            source_type=SourceType.RAIN,
            event_time=minute * 60 + 18,
            arrival_time=minute * 60 + 20,
            kind=EventKind.RAIN_GAUGE,
            value=0.0,
            location="zone_north",
            gateway_id="gw_weather",
            is_anomaly=False
        ))
        return events
