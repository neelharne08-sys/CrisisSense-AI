import asyncio
import json
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from sse_starlette.sse import EventSourceResponse

from src.schemas import (
    StreamEvent, MinuteStatePayload, CAPAlert, SourceType, EventKind, ActionLevel
)
from src.engine.filter import BayesianForwardFilter
from src.engine.cap import CAPAlertBuilder
from src.simulator.generator import EpisodeGenerator
from src.simulator.corruptions import StreamCorruptor

app = FastAPI(
    title="CrisisSense AI Decision API",
    description="Online 128-state Bayesian inference & optimal stopping engine for urban crisis cascades",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8085",
        "http://127.0.0.1:8085",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_minute_zero_payload() -> MinuteStatePayload:
    """Returns baseline pre-incident municipal monitoring state at t=00:00."""
    return MinuteStatePayload(
        minute=0,
        probabilities={"H0": 0.60, "H1": 0.15, "H2": 0.15, "H3": 0.10},
        uncertainty_band={"H0": [0.55, 0.65], "H1": [0.11, 0.19], "H2": [0.11, 0.19], "H3": [0.04, 0.16]},
        nuisance_posteriors={"R": 0.05, "F": 0.03, "G1": 0.02, "G2": 0.02, "U": 0.04},
        recommended_action=ActionLevel.WATCH,
        expected_costs={"WATCH": 0.0, "PREPARE": 1.0, "ALERT": 6.0, "ESCALATE": 25.0},
        value_of_waiting_saved=0.0,
        fatigue_level=0.0,
        forecasts=[],
        source_trust={
            "drainage_sensors": 0.85,
            "traffic_sensors": 0.82,
            "cameras": 0.90,
            "dispatch_logs": 0.95,
            "hospitals": 0.92,
            "rain_gauges": 0.96,
            "citizen_reports": 0.65,
            "social_rumor": 0.40
        },
        blind_sources=[],
        explanation_summary="Baseline municipal monitoring. Normal background variance across all sensor sectors.",
        top_drivers=[],
        discounted_items=[],
        what_would_change_mind="Multiple corroborating physical sensor anomalies or dispatch logs.",
        flip_flop_count=0,
        regime_shift_detected=False,
        temperature=1.0,
        cap_alert=None,
        events=[]
    )

def normalize_scenario_name(name: str) -> str:
    n = name.lower().strip()
    if n in ("alpha", "episode_alpha", "episode alpha", "scenario alpha", "twin_cascade"):
        return "twin_cascade"
    elif n in ("beta", "episode_beta", "episode beta", "scenario beta", "twin_benign"):
        return "twin_benign"
    return n

# Global runtime state
class RuntimeState:
    def __init__(self):
        self.engine = BayesianForwardFilter()
        self.generator = EpisodeGenerator(seed=42)
        self.corruptor = StreamCorruptor(seed=42)
        self.active_events: List[StreamEvent] = []
        self.current_minute = 0
        self.is_running = False
        self.scenario = "twin_cascade"
        self.speed = 1.0
        self.seed = 42
        self.timeline_cache: Dict[int, MinuteStatePayload] = {0: get_minute_zero_payload()}

state = RuntimeState()

def recompute_timeline():
    """Simulates active episode through BayesianForwardFilter and caches minute states."""
    engine = BayesianForwardFilter()
    timeline: Dict[int, MinuteStatePayload] = {0: get_minute_zero_payload()}
    for m in range(1, 31):
        m_events = [e for e in state.active_events if (e.event_time // 60) == m]
        payload = engine.process_minute(m, m_events)
        timeline[m] = payload
    state.engine = engine
    state.timeline_cache = timeline

class StartEpisodeRequest(BaseModel):
    scenario: str = "twin_cascade"
    seed: int = 42
    speed: float = 1.0

class InjectRequest(BaseModel):
    inject_type: str # cutout, retraction, lie, shift, rumor, jitter
    target: Optional[str] = None
    value: Optional[float] = None

class CounterfactualRequest(BaseModel):
    clamps: Dict[str, float] # e.g. {"R": 1.0, "G1": 1.0, "F": 1.0}

@app.get("/")
def read_root(request: Request):
    accept = request.headers.get("accept", "")
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if "text/html" in accept and os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "system": "CrisisSense AI",
        "version": "3.0.0",
        "status": "online",
        "active_scenario": state.scenario,
        "current_minute": state.current_minute
    }

@app.get("/scenarios")
def list_scenarios():
    return [
        {
            "id": "twin_cascade",
            "alias": "alpha",
            "name": "Episode Alpha (Cascading Crisis)",
            "description": "Shared storm-and-infrastructure prefix followed by levee failure and electrical cascade",
            "divergence_minute": 8,
            "ground_truth": "H3"
        },
        {
            "id": "twin_benign",
            "alias": "beta",
            "name": "Episode Beta (Twin Mimic)",
            "description": "Shared prefix resolving as telecom fiber conduit cut and benign pediatric flu cluster",
            "divergence_minute": 8,
            "ground_truth": "H0"
        },
        {
            "id": "cascade",
            "name": "Standard Cascading Crisis",
            "description": "Rapid multi-point infrastructure cascade",
            "ground_truth": "H3"
        },
        {
            "id": "rain_mimic",
            "name": "Rain Mimic",
            "description": "Heavy rainfall explaining drainage anomalies",
            "ground_truth": "H0"
        },
        {
            "id": "flu_mimic",
            "name": "Flu Mimic",
            "description": "Pediatric flu cluster explaining hospital arrivals",
            "ground_truth": "H0"
        },
        {
            "id": "gateway_failure",
            "name": "Gateway Outage",
            "description": "Telecommunications gateway drop masking 100 sensors",
            "ground_truth": "H1"
        },
        {
            "id": "rumor_mimic",
            "name": "Viral Rumor Wave",
            "description": "Coordinated social media misinformation wave",
            "ground_truth": "H0"
        },
        {
            "id": "isolated_incident",
            "name": "Isolated Incident",
            "description": "Localized incident without systemic cascade",
            "ground_truth": "H2"
        }
    ]

@app.post("/episode/start")
def start_episode(req: StartEpisodeRequest):
    scenario = normalize_scenario_name(req.scenario)
    state.engine = BayesianForwardFilter()
    state.generator = EpisodeGenerator(seed=req.seed)
    state.corruptor = StreamCorruptor(seed=req.seed)
    state.scenario = scenario
    state.speed = req.speed
    state.seed = req.seed
    state.current_minute = 0
    state.active_events, true_h, meta = state.generator.generate_episode(
        scenario, enable_corruptions=True
    )
    state.is_running = True
    
    # Precompute episode timeline for instant scrubbing & fast response
    recompute_timeline()

    return {
        "status": "started",
        "scenario": scenario,
        "seed": req.seed,
        "total_events": len(state.active_events),
        "true_h": true_h,
        "meta": meta
    }

@app.get("/episode/state/{minute}")
def get_minute_state(minute: int):
    if minute < 0 or minute > 30:
        raise HTTPException(status_code=400, detail="Minute must be between 0 and 30")
    if minute not in state.timeline_cache:
        recompute_timeline()
    state.current_minute = minute
    return state.timeline_cache.get(minute, get_minute_zero_payload())

@app.get("/episode/timeline")
def get_full_timeline():
    if not state.timeline_cache:
        recompute_timeline()
    return {
        "scenario": state.scenario,
        "seed": state.seed,
        "current_minute": state.current_minute,
        "timeline": {str(m): payload.model_dump() for m, payload in state.timeline_cache.items()}
    }

@app.get("/stream")
async def event_stream():
    """
    SSE stream yielding per-minute MinuteStatePayload for the active episode.
    """
    async def event_generator():
        for m in range(1, 31):
            if not state.is_running:
                break
            
            if m not in state.timeline_cache:
                m_events = [e for e in state.active_events if (e.event_time // 60) == m]
                payload = state.engine.process_minute(m, m_events)
                state.timeline_cache[m] = payload
            else:
                payload = state.timeline_cache[m]
            
            state.current_minute = m

            yield {
                "event": "minute_update",
                "id": str(m),
                "data": payload.model_dump_json()
            }
            # Sim speed delay: 1s base divided by speed
            await asyncio.sleep(max(0.05, 1.0 / max(0.1, state.speed)))

        yield {
            "event": "episode_complete",
            "data": json.dumps({"status": "completed", "minutes": state.current_minute})
        }

    return EventSourceResponse(event_generator())

@app.post("/inject")
def inject_event(req: InjectRequest):
    """
    Live demo adversity injection controls:
    - cutout: cuts out a gateway (e.g. 'gw_1') or sensor modality (e.g. 'cameras')
    - rumor / rumor_swarm: injects viral misinformation wave
    - jitter / out_of_order: injects delay packet shuffling
    - lie / structured_lie: injects 20 frozen drainage sensors with dry rain
    - retraction: injects retraction of latest incident report
    - shift: triggers silent monsoon regime shift
    """
    curr_min = state.current_minute

    if req.inject_type in ("cutout", "gateway_cutout", "gateway_drop"):
        target_src = req.target or "gw_1"
        if target_src in ("gw_1", "gateway", "gateway_1"):
            gw_events = state.corruptor.inject_gateway_failure(
                "gw_1", num_sensors=100, failure_minute=max(1, curr_min)
            )
            state.active_events.extend(gw_events)
            state.active_events.sort(key=lambda x: x.arrival_time)
            recompute_timeline()
            return {"status": "injected", "detail": "Injected Gateway 1 failure (heartbeat loss + 100 sensors masked)"}
        else:
            state.engine.normalizer.set_cutout(target_src, active=True)
            recompute_timeline()
            return {"status": "injected", "detail": f"Source {target_src} set to BLIND_CUTOUT"}

    elif req.inject_type in ("rumor", "rumor_swarm", "disinfo"):
        m = max(1, curr_min)
        rumor_events = []
        for i in range(50):
            sec = i % 60
            rumor_events.append(StreamEvent(
                id=f"live_rumor_{m}_{i}",
                source_id=f"social_user_{i}",
                source_type=SourceType.SOCIAL if i % 2 == 0 else SourceType.CITIZEN,
                event_time=m * 60 + sec,
                arrival_time=m * 60 + sec + 2,
                kind=EventKind.SOCIAL_POST if i % 2 == 0 else EventKind.CITIZEN_REPORT,
                value=0.95,
                location="zone_north",
                claim_id="claim_dam_collapse_rumor"
            ))
        state.active_events.extend(rumor_events)
        state.active_events.sort(key=lambda x: x.arrival_time)
        recompute_timeline()
        return {"status": "injected", "detail": "Injected viral rumor wave (50 citizen/social reports)"}

    elif req.inject_type in ("jitter", "out_of_order", "delays"):
        # Apply delay jitter to remaining events
        future_events = [e for e in state.active_events if (e.event_time // 60) >= curr_min]
        past_events = [e for e in state.active_events if (e.event_time // 60) < curr_min]
        delayed_future = state.corruptor.inject_delays(future_events, max_delay_sec=180)
        state.active_events = past_events + delayed_future
        state.active_events.sort(key=lambda x: x.arrival_time)
        recompute_timeline()
        return {"status": "injected", "detail": "Applied out-of-order delay jitter to event stream"}

    elif req.inject_type in ("lie", "structured_lie"):
        m = max(1, curr_min)
        lie_events = state.corruptor.inject_structured_lie(minute=m, num_sensors=20)
        state.active_events.extend(lie_events)
        state.active_events.sort(key=lambda x: x.arrival_time)
        recompute_timeline()
        return {"status": "injected", "detail": "Injected 20 frozen drainage sensors with dry rain gauge"}

    elif req.inject_type == "retraction":
        candidates = [e for e in state.engine.history_events if e.kind in (EventKind.DISPATCH_INCIDENT, EventKind.CITIZEN_REPORT)]
        if candidates:
            target = candidates[-1]
            retract_ev = StreamEvent(
                id=f"live_retract_{target.id}",
                source_id="officer_override",
                source_type=target.source_type,
                event_time=curr_min * 60 + 5,
                arrival_time=curr_min * 60 + 6,
                kind=target.kind,
                value=0.0,
                location=target.location,
                retracts=target.id
            )
            state.active_events.append(retract_ev)
            state.active_events.sort(key=lambda x: x.arrival_time)
            recompute_timeline()
            return {"status": "injected", "detail": f"Retracted event {target.id}"}
        return {"status": "failed", "detail": "No candidate event found to retract"}

    elif req.inject_type == "shift":
        state.engine.learner.regime_shift_detected = True
        return {"status": "injected", "detail": "Triggered silent monsoon season shift"}

    return {"status": "unknown_injection_type"}

@app.post("/counterfactual")
def compute_counterfactual(req: CounterfactualRequest):
    """
    do(X=x) API: recalculates next-3 event forecasts under clamped latent values.
    """
    curr_min = max(1, state.current_minute)
    last_payload = state.timeline_cache.get(curr_min) or state.engine.minute_payloads.get(curr_min)
    p_h3 = last_payload.probabilities["H3"] if last_payload else 0.50
    nuisances = last_payload.nuisance_posteriors if last_payload else {}

    forecasts = state.engine.foresight.get_forecasts(
        current_minute=curr_min,
        p_h3=p_h3,
        nuisances=nuisances,
        counterfactual_clamping=req.clamps
    )
    return {
        "clamps": req.clamps,
        "forecasts": [f.model_dump() for f in forecasts]
    }

@app.get("/explain/{minute}")
def get_explanation(minute: int):
    payload = state.timeline_cache.get(minute) or state.engine.minute_payloads.get(minute)
    if not payload:
        raise HTTPException(status_code=404, detail=f"No state found for minute {minute}")
    return {
        "minute": minute,
        "summary": payload.explanation_summary,
        "top_drivers": payload.top_drivers,
        "discounted_items": payload.discounted_items,
        "what_would_change_mind": payload.what_would_change_mind,
        "expected_costs": payload.expected_costs,
        "fatigue_level": payload.fatigue_level
    }

@app.get("/cap-alert")
def get_cap_alert(format: str = "json"):
    curr_min = max(0, state.current_minute)
    payload = state.timeline_cache.get(curr_min) or state.engine.minute_payloads.get(curr_min)
    if not payload or not payload.cap_alert:
        return {"status": "no_active_alert", "message": "System currently in WATCH status (Exercise)"}

    if format == "xml":
        xml_str = CAPAlertBuilder.to_xml(payload.cap_alert)
        return {"format": "xml", "content": xml_str}

    return {"format": "json", "content": payload.cap_alert.model_dump()}

@app.get("/metrics")
def get_metrics():
    """
    Returns latest benchmark metrics from file or computed on demand.
    """
    results_path = os.path.join(PROJECT_ROOT, "benchmark_results.json")
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            return json.load(f)
    return {"status": "pending", "message": "Run evaluation benchmark to view detailed metrics."}

# Mount static frontend files at root to serve index.html, styles.css, app.js, etc.
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
