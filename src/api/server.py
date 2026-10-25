import asyncio
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global runtime state
class RuntimeState:
    def __init__(self):
        self.engine = BayesianForwardFilter()
        self.generator = EpisodeGenerator(seed=42)
        self.corruptor = StreamCorruptor(seed=42)
        self.active_events: List[StreamEvent] = []
        self.current_minute = 0
        self.is_running = False
        self.scenario = "cascade"
        self.speed = 1.0
        self.stream_queue: asyncio.Queue = asyncio.Queue()

state = RuntimeState()

class StartEpisodeRequest(BaseModel):
    scenario: str = "cascade"
    seed: int = 42
    speed: float = 1.0

class InjectRequest(BaseModel):
    inject_type: str # cutout, retraction, lie, shift
    target: Optional[str] = None
    value: Optional[float] = None

class CounterfactualRequest(BaseModel):
    clamps: Dict[str, float] # e.g. {"R": 1.0, "G1": 1.0, "F": 1.0}

@app.get("/")
def read_root():
    return {
        "system": "CrisisSense AI",
        "version": "3.0.0",
        "status": "online",
        "active_scenario": state.scenario,
        "current_minute": state.current_minute
    }

@app.post("/episode/start")
def start_episode(req: StartEpisodeRequest):
    state.engine = BayesianForwardFilter()
    state.generator = EpisodeGenerator(seed=req.seed)
    state.corruptor = StreamCorruptor(seed=req.seed)
    state.scenario = req.scenario
    state.speed = req.speed
    state.current_minute = 0
    state.active_events, true_h, meta = state.generator.generate_episode(
        req.scenario, enable_corruptions=True
    )
    state.is_running = True

    return {
        "status": "started",
        "scenario": req.scenario,
        "seed": req.seed,
        "total_events": len(state.active_events),
        "true_h": true_h,
        "meta": meta
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
            
            # Extract events for minute m
            m_events = [e for e in state.active_events if (e.event_time // 60) == m]
            payload = state.engine.process_minute(m, m_events)
            state.current_minute = m

            yield {
                "event": "minute_update",
                "id": str(m),
                "data": payload.model_dump_json()
            }
            # Sim speed delay: 1s base divided by speed
            await asyncio.sleep(max(0.1, 1.0 / max(0.1, state.speed)))

        yield {
            "event": "episode_complete",
            "data": json.dumps({"status": "completed", "minutes": state.current_minute})
        }

    return EventSourceResponse(event_generator())

@app.post("/inject")
def inject_event(req: InjectRequest):
    """
    Live demo controls:
    - cutout: cuts out a source (e.g. 'cameras')
    - retraction: injects retraction of latest incident
    - lie: injects structured lie (frozen drainage values with dry rain)
    - shift: detects season shift
    """
    if req.inject_type == "cutout":
        target_src = req.target or "cameras"
        state.engine.normalizer.set_cutout(target_src, active=True)
        return {"status": "injected", "detail": f"Source {target_src} set to BLIND_CUTOUT"}

    elif req.inject_type == "retraction":
        # Find latest dispatch or citizen event
        candidates = [e for e in state.engine.history_events if e.kind in (EventKind.DISPATCH_INCIDENT, EventKind.CITIZEN_REPORT)]
        if candidates:
            target = candidates[-1]
            retract_ev = StreamEvent(
                id=f"live_retract_{target.id}",
                source_id="officer_override",
                source_type=target.source_type,
                event_time=state.current_minute * 60 + 5,
                arrival_time=state.current_minute * 60 + 6,
                kind=target.kind,
                value=0.0,
                location=target.location,
                retracts=target.id
            )
            state.engine.process_minute(state.current_minute, [retract_ev])
            return {"status": "injected", "detail": f"Retracted event {target.id}"}
        return {"status": "failed", "detail": "No candidate event found to retract"}

    elif req.inject_type == "lie":
        lie_events = state.corruptor.inject_structured_lie(minute=state.current_minute, num_sensors=20)
        state.engine.process_minute(state.current_minute, lie_events)
        return {"status": "injected", "detail": "Injected 20 frozen drainage sensors with dry rain gauge"}

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
    last_payload = state.engine.minute_payloads.get(curr_min)
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
    payload = state.engine.minute_payloads.get(minute)
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
    curr_min = max(1, state.current_minute)
    payload = state.engine.minute_payloads.get(curr_min)
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
    results_path = "benchmark_results.json"
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            return json.load(f)
    return {"status": "pending", "message": "Run evaluation benchmark to view detailed metrics."}
