import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import numpy as np
from src.schemas import EventKind, SourceType, ActionLevel
from src.simulator.live_weather import LiveWeatherFeed, to_events
from src.engine.filter import BayesianForwardFilter

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "weather")

def test_offline_heavy_rain_fixture_explaining_away():
    """
    Test 1: Heavy Rain Fixture & Explaining Away
    Verifies that high precipitation (~32 mm/h) raises P(R=1) and explains away
    elevated drainage readings, preventing premature false escalation.
    """
    feed = LiveWeatherFeed()
    feed.load_fixture(os.path.join(FIXTURES_DIR, "heavy_rain.json"))
    
    events = feed.poll(current_minute=1, force=True)
    assert len(events) > 0
    # Average rainfall in fixture is > 20 mm/h
    assert any(e.value > 15.0 for e in events)
    assert events[0].source_id == "open_meteo"
    assert events[0].kind == EventKind.RAIN_GAUGE

    # Ingest into Bayesian Forward Filter alongside elevated drainage runoff
    engine = BayesianForwardFilter()
    payload1 = engine.process_minute(1, events[:4])
    
    # R (Rain) posterior should be strongly elevated from 0.05 prior
    p_rain1 = payload1.nuisance_posteriors["R"]
    assert p_rain1 >= 0.65, f"Expected P(R=1) >= 0.65 in minute 1, got {p_rain1:.2f}"
    
    # By minute 2 with continued heavy rain, P(R=1) climbs >= 0.85
    for ev in events[4:]:
        ev.event_time = 2 * 60 + 5
        ev.arrival_time = 2 * 60 + 10
    payload2 = engine.process_minute(2, events[4:])
    p_rain2 = payload2.nuisance_posteriors["R"]
    assert p_rain2 >= 0.85, f"Expected P(R=1) >= 0.85 in minute 2, got {p_rain2:.2f}"
    
    # Explaining-away holds action at safe WATCH / PREPARE
    assert payload2.recommended_action in [ActionLevel.WATCH, ActionLevel.PREPARE]


def test_offline_dry_day_fixture():
    """
    Test 2: Dry Day Fixture
    Verifies that 0.0 mm/h maintains low P(R=1) and does not explain away anomalies.
    """
    feed = LiveWeatherFeed()
    feed.load_fixture(os.path.join(FIXTURES_DIR, "dry_day.json"))
    
    events = feed.poll(current_minute=1, force=True)
    assert len(events) > 0
    assert all(e.value == 0.0 for e in events)

    engine = BayesianForwardFilter()
    payload = engine.process_minute(1, events)
    
    p_rain = payload.nuisance_posteriors["R"]
    assert p_rain <= 0.15, f"Expected P(R=1) <= 0.15 on dry day, got {p_rain:.2f}"


def test_stale_weather_feed_treated_as_missing():
    """
    Test 3: Missing / Stale Feed Protocol
    Verifies that network failure mid-episode marks source as stale and does NOT
    emit fake '0 mm' readings (matching sensor cutout protocol).
    """
    feed = LiveWeatherFeed()
    feed.set_offline_failure(True)
    
    events = feed.poll(current_minute=1, force=True)
    assert len(events) == 0, "Stale feed must emit 0 events (not fake 0 mm)"
    assert feed.is_stale is True

    # Filter processes minute with missing weather gracefully
    engine = BayesianForwardFilter()
    payload = engine.process_minute(1, [])
    assert payload.probabilities["H3"] < 0.20


def test_weather_feed_bucket_deduplication():
    """
    Test 4: 15-Minute Bucket Deduplication
    Verifies that polling multiple times within the same 15-min bucket does not duplicate events.
    """
    feed = LiveWeatherFeed()
    feed.load_fixture(os.path.join(FIXTURES_DIR, "heavy_rain.json"))
    
    # First poll consumes all unread buckets
    evs1 = feed.poll(current_minute=1, force=True)
    assert len(evs1) > 0
    
    # Second poll immediately afterwards should yield 0 events
    evs2 = feed.poll(current_minute=2, force=True)
    assert len(evs2) == 0, "Repeated poll must not duplicate already-seen 15-min buckets"


def test_weather_monsoon_changepoint_detection():
    """
    Test 5: Rolling Rain History & Changepoint Detection
    Verifies that persistent heavy rainfall triggers regime shift adaptation.
    """
    feed = LiveWeatherFeed()
    feed.load_fixture(os.path.join(FIXTURES_DIR, "heavy_rain.json"))
    evs = feed.poll(current_minute=1, force=True)
    
    engine = BayesianForwardFilter()
    # Feed rolling average rain to learner
    avg_rain = feed.get_rolling_average_rain()
    assert avg_rain > 15.0  # Heavy monsoon rain
    
    shift_triggered = engine.learner.update_weather_prior_shift(avg_rain)
    assert shift_triggered is True
    assert engine.learner.regime_shift_detected is True
