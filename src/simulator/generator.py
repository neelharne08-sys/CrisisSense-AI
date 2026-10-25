import random
import copy
import numpy as np
from typing import Dict, List, Tuple, Optional
from src.schemas import StreamEvent, SourceType, EventKind
from src.simulator.corruptions import StreamCorruptor

class EpisodeGenerator:
    """
    30-Minute Seeded Compressible Episode Generator:
    Generates realistic municipal event streams across 8 distinct scenario types,
    including exact twin pairs and season shift regimes.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.corruptor = StreamCorruptor(seed)

    def generate_shared_twin_prefix(self) -> List[StreamEvent]:
        """
        Generates identical 7-minute prefix for Twin Test:
        Ambiguous anomalies from drainage sensors, traffic slowdowns, and citizen calls
        consistent with either an emerging cascade OR a moderate benign rain shower.
        """
        prefix_events = []
        # Minutes 1-7
        for m in range(1, 8):
            # Drainage anomaly
            prefix_events.append(StreamEvent(
                id=f"twin_pfx_drain_{m}",
                source_id="drain_main_basin",
                source_type=SourceType.DRAINAGE,
                event_time=m * 60 + 12,
                arrival_time=m * 60 + 15,
                kind=EventKind.DRAIN_ANOMALY,
                value=0.72 + (m * 0.02),
                location="zone_north",
                gateway_id="gw_1"
            ))
            # Minor traffic slowdown
            if m >= 3:
                prefix_events.append(StreamEvent(
                    id=f"twin_pfx_traffic_{m}",
                    source_id="traffic_arterial_1",
                    source_type=SourceType.TRAFFIC,
                    event_time=m * 60 + 25,
                    arrival_time=m * 60 + 28,
                    kind=EventKind.TRAFFIC_SLOW,
                    value=0.65,
                    location="zone_north",
                    gateway_id="gw_1"
                ))
            # Citizen call
            if m >= 5:
                prefix_events.append(StreamEvent(
                    id=f"twin_pfx_call_{m}",
                    source_id=f"citizen_caller_{m}",
                    source_type=SourceType.CITIZEN,
                    event_time=m * 60 + 40,
                    arrival_time=m * 60 + 55,
                    kind=EventKind.CITIZEN_REPORT,
                    value=0.60,
                    location="zone_north",
                    claim_id="claim_surface_water"
                ))
        return prefix_events

    def generate_episode(
        self, 
        scenario_type: str = "cascade", 
        enable_corruptions: bool = True,
        is_season_shifted: bool = False
    ) -> Tuple[List[StreamEvent], int, Dict[str, Any]]:
        """
        Generates 30-minute episode stream.
        Returns: (events_sorted_by_arrival, true_h, ground_truth_meta)
        """
        events: List[StreamEvent] = []
        true_h = 0
        meta: Dict[str, Any] = {"scenario": scenario_type, "season_shifted": is_season_shifted}

        # 1. Twin Cascade (Branch A)
        if scenario_type == "twin_cascade":
            events.extend(self.generate_shared_twin_prefix())
            true_h = 3
            # Divergence at minute 8: Hard independent confirmations
            for m in range(8, 31):
                # Dispatch incident (verified multi-vehicle accident / road cut)
                events.append(StreamEvent(
                    id=f"twin_a_dispatch_{m}",
                    source_id="ems_dispatch_core",
                    source_type=SourceType.DISPATCH,
                    event_time=m * 60 + 10,
                    arrival_time=m * 60 + 75, # 65s delay
                    kind=EventKind.DISPATCH_INCIDENT,
                    value=0.92,
                    location="zone_north"
                ))
                # Non-flu Hospital trauma arrivals
                events.append(StreamEvent(
                    id=f"twin_a_hospital_{m}",
                    source_id="memorial_er",
                    source_type=SourceType.HOSPITALS,
                    event_time=m * 60 + 30,
                    arrival_time=m * 60 + 40,
                    kind=EventKind.HOSPITAL_ARRIVALS,
                    value=0.88,
                    location="zone_central"
                ))
                # Camera confirmation
                events.append(StreamEvent(
                    id=f"twin_a_cam_{m}",
                    source_id="cam_junction_4",
                    source_type=SourceType.CAMERAS,
                    event_time=m * 60 + 45,
                    arrival_time=m * 60 + 48,
                    kind=EventKind.CAMERA_FLAG,
                    value=0.85,
                    location="zone_north",
                    gateway_id="gw_2"
                ))

        # 2. Twin Benign (Branch B)
        elif scenario_type == "twin_benign":
            events.extend(self.generate_shared_twin_prefix())
            true_h = 0
            # Divergence at minute 8: Rain gauge confirms heavy rain explaining drainage
            for m in range(8, 31):
                events.append(StreamEvent(
                    id=f"twin_b_rain_{m}",
                    source_id="met_office_gauge",
                    source_type=SourceType.RAIN,
                    event_time=m * 60 + 10,
                    arrival_time=m * 60 + 12,
                    kind=EventKind.RAIN_GAUGE,
                    value=0.90,
                    location="zone_north",
                    gateway_id="gw_weather"
                ))
                # Traffic normalizes (no slow events)

        # 3. True Cascade (Standard H3)
        elif scenario_type == "cascade":
            true_h = 3
            onset = 2
            meta["onset_minute"] = onset
            for m in range(1, 31):
                if m >= onset:
                    # Drainage overflow
                    events.append(StreamEvent(
                        id=f"casc_drain_{m}",
                        source_id=f"drain_{m%3}",
                        source_type=SourceType.DRAINAGE,
                        event_time=m * 60 + 10,
                        arrival_time=m * 60 + 15,
                        kind=EventKind.DRAIN_ANOMALY,
                        value=0.89,
                        location="zone_north",
                        gateway_id="gw_1"
                    ))
                if m >= onset + 2:
                    # Traffic arterial jam
                    events.append(StreamEvent(
                        id=f"casc_traffic_{m}",
                        source_id=f"traffic_{m%2}",
                        source_type=SourceType.TRAFFIC,
                        event_time=m * 60 + 25,
                        arrival_time=m * 60 + 30,
                        kind=EventKind.TRAFFIC_SLOW,
                        value=0.86,
                        location="zone_north",
                        gateway_id="gw_1"
                    ))
                if m >= onset + 4:
                    # Emergency calls & dispatch
                    events.append(StreamEvent(
                        id=f"casc_disp_{m}",
                        source_id="dispatch_line",
                        source_type=SourceType.DISPATCH,
                        event_time=m * 60 + 40,
                        arrival_time=m * 60 + 100, # delay
                        kind=EventKind.DISPATCH_INCIDENT,
                        value=0.91,
                        location="zone_north"
                    ))
                if m >= onset + 6:
                    # Hospital arrival surge
                    events.append(StreamEvent(
                        id=f"casc_hosp_{m}",
                        source_id="city_hospital",
                        source_type=SourceType.HOSPITALS,
                        event_time=m * 60 + 50,
                        arrival_time=m * 60 + 55,
                        kind=EventKind.HOSPITAL_ARRIVALS,
                        value=0.87,
                        location="zone_central"
                    ))

        # 4. Rain Mimic (H0 with R=1)
        elif scenario_type == "rain_mimic":
            true_h = 0
            for m in range(1, 31):
                events.append(StreamEvent(
                    id=f"rain_g_{m}",
                    source_id="rain_sensor_1",
                    source_type=SourceType.RAIN,
                    event_time=m * 60 + 5,
                    arrival_time=m * 60 + 8,
                    kind=EventKind.RAIN_GAUGE,
                    value=0.94,
                    location="zone_north",
                    gateway_id="gw_weather"
                ))
                events.append(StreamEvent(
                    id=f"rain_drain_{m}",
                    source_id="drain_basin_1",
                    source_type=SourceType.DRAINAGE,
                    event_time=m * 60 + 20,
                    arrival_time=m * 60 + 25,
                    kind=EventKind.DRAIN_ANOMALY,
                    value=0.68,
                    location="zone_north",
                    gateway_id="gw_1"
                ))

        # 5. Flu Mimic (H0 with F=1)
        elif scenario_type == "flu_mimic":
            true_h = 0
            for m in range(1, 31):
                events.append(StreamEvent(
                    id=f"flu_hosp_{m}",
                    source_id="memorial_er",
                    source_type=SourceType.HOSPITALS,
                    event_time=m * 60 + 15,
                    arrival_time=m * 60 + 20,
                    kind=EventKind.HOSPITAL_ARRIVALS,
                    value=0.85,
                    location="zone_central"
                ))

        # 6. Gateway Outage (H1)
        elif scenario_type == "gateway_failure":
            true_h = 1
            # Inject 100 sensors behind Gateway 1 at minute 4
            gw_events = self.corruptor.inject_gateway_failure("gw_1", num_sensors=100, failure_minute=4)
            events.extend(gw_events)

        # 7. Viral Rumor Mimic (H0 with U=1)
        elif scenario_type == "rumor_mimic":
            true_h = 0
            # 50 citizen and social reports sharing same claim_id
            for i in range(50):
                m = self.rng.randint(2, 6)
                sec = self.rng.randint(0, 59)
                events.append(StreamEvent(
                    id=f"rumor_rep_{i}",
                    source_id=f"social_user_{i}",
                    source_type=SourceType.SOCIAL if i % 2 == 0 else SourceType.CITIZEN,
                    event_time=m * 60 + sec,
                    arrival_time=m * 60 + sec + 5,
                    kind=EventKind.SOCIAL_POST if i % 2 == 0 else EventKind.CITIZEN_REPORT,
                    value=0.95,
                    location="zone_north",
                    claim_id="claim_dam_collapse_rumor"
                ))

        # 8. Isolated Incident (H2)
        elif scenario_type == "isolated_incident":
            true_h = 2
            for m in range(3, 15):
                events.append(StreamEvent(
                    id=f"iso_ev_{m}",
                    source_id="local_zone_cam",
                    source_type=SourceType.CAMERAS,
                    event_time=m * 60 + 10,
                    arrival_time=m * 60 + 15,
                    kind=EventKind.CAMERA_FLAG,
                    value=0.75,
                    location="zone_isolated",
                    gateway_id="gw_2"
                ))

        # 9. Background Noise (H0)
        else: # noise
            true_h = 0
            for m in range(1, 31):
                if self.rng.random() < 0.3:
                    events.append(StreamEvent(
                        id=f"noise_{m}",
                        source_id="random_sensor",
                        source_type=SourceType.DRAINAGE,
                        event_time=m * 60 + 30,
                        arrival_time=m * 60 + 35,
                        kind=EventKind.DRAIN_ANOMALY,
                        value=0.25,
                        location="zone_random"
                    ))

        # Apply Corruptions if enabled
        if enable_corruptions and scenario_type not in ("twin_cascade", "twin_benign"):
            events = self.corruptor.inject_delays(events)
            events = self.corruptor.inject_duplicates(events, dup_fraction=0.10)
            events = self.corruptor.inject_retractions(events, retract_fraction=0.05)

        # Sort all events by arrival_time
        events.sort(key=lambda x: x.arrival_time)
        return events, true_h, meta
