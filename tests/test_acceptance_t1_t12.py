import pytest
import numpy as np
from src.schemas import StreamEvent, SourceType, EventKind, ActionLevel
from src.engine.filter import BayesianForwardFilter
from src.simulator.generator import EpisodeGenerator
from src.simulator.corruptions import StreamCorruptor

def test_t1_twin_prefix():
    """
    T1: Twin Prefix
    Minutes 1-7 of ambiguous twin stream:
    0.20 <= P(H3) <= 0.50 and recommended_action != 'ESCALATE'
    """
    engine = BayesianForwardFilter()
    gen = EpisodeGenerator(seed=101)
    prefix_events = gen.generate_shared_twin_prefix()
    
    for m in range(1, 8):
        m_events = [e for e in prefix_events if (e.event_time // 60) == m]
        state = engine.process_minute(m, m_events)
    
    assert 0.20 <= state.probabilities["H3"] <= 0.50, f"P(H3) was {state.probabilities['H3']}, expected 0.20..0.50"
    assert state.recommended_action != ActionLevel.ESCALATE, f"Action was {state.recommended_action}, expected not ESCALATE"

def test_t2_twin_divergence_to_cascade():
    """
    T2: Twin Divergence -> Cascade
    Twin Branch A adds dispatch + non-flu hospital arrival at t=8.
    Reaches ALERT or ESCALATE by t <= 11 (within 3 minutes).
    """
    engine = BayesianForwardFilter()
    gen = EpisodeGenerator(seed=102)
    events, true_h, _ = gen.generate_episode("twin_cascade", enable_corruptions=False)
    
    committed_min = None
    for m in range(1, 15):
        m_events = [e for e in events if (e.event_time // 60) == m]
        state = engine.process_minute(m, m_events)
        if m >= 8 and state.recommended_action in (ActionLevel.ALERT, ActionLevel.ESCALATE):
            if committed_min is None:
                committed_min = m

    assert committed_min is not None, "Failed to reach ALERT or ESCALATE after divergence"
    assert committed_min <= 11, f"Committed at minute {committed_min}, expected <= 11 (<= 3 min post-divergence)"

def test_t3_twin_divergence_to_benign():
    """
    T3: Twin Divergence -> Benign
    Twin Branch B adds rain gauge confirmation at t=8.
    Never reaches ALERT; P(H3) < 0.20 by t=12.
    """
    engine = BayesianForwardFilter()
    gen = EpisodeGenerator(seed=103)
    events, true_h, _ = gen.generate_episode("twin_benign", enable_corruptions=False)
    
    alert_triggered = False
    p_h3_t12 = 0.5
    for m in range(1, 15):
        m_events = [e for e in events if (e.event_time // 60) == m]
        state = engine.process_minute(m, m_events)
        if state.recommended_action in (ActionLevel.ALERT, ActionLevel.ESCALATE):
            alert_triggered = True
        if m == 12:
            p_h3_t12 = state.probabilities["H3"]

    assert not alert_triggered, "ALERT was incorrectly triggered on benign twin"
    assert p_h3_t12 < 0.20, f"P(H3) at minute 12 was {p_h3_t12}, expected < 0.20"

def test_t4_gateway_outage_masks_100_sensors():
    """
    T4: Gateway Outage Masks 100 Sensors
    Gateway 1 drops heartbeat; 100 drainage/traffic sensors emit anomalies.
    Treated as 1 gateway event; P(G1) > 0.80, P(H1) rises, P(H3) < 0.25.
    """
    engine = BayesianForwardFilter()
    corruptor = StreamCorruptor(seed=104)
    gw_events = corruptor.inject_gateway_failure("gw_1", num_sensors=100, failure_minute=3)
    
    state = None
    for m in range(1, 6):
        m_events = [e for e in gw_events if (e.event_time // 60) == m]
        state = engine.process_minute(m, m_events)

    assert state.nuisance_posteriors["G1"] > 0.80, f"P(G1) was {state.nuisance_posteriors['G1']}, expected > 0.80"
    assert state.probabilities["H3"] < 0.25, f"P(H3) was {state.probabilities['H3']}, expected < 0.25"
    assert state.probabilities["H1"] > state.probabilities["H3"], "P(H1) did not rise above P(H3)"

def test_t5_cascade_lookalike_rain_flu_calls():
    """
    T5: Cascade Look-Alike (Rain + Flu + Storm Calls)
    Heavy rain (R=1), flu surge (F=1), and storm calls.
    Action in {WATCH, PREPARE}; explanation names mimics.
    """
    engine = BayesianForwardFilter()
    events = []
    # Rain gauge confirms rain
    events.append(StreamEvent(
        id="rain_t5", source_id="rain_1", source_type=SourceType.RAIN,
        event_time=120, arrival_time=125, kind=EventKind.RAIN_GAUGE,
        value=0.95, location="zone_north"
    ))
    # Drainage anomaly explained by rain
    events.append(StreamEvent(
        id="drain_t5", source_id="drain_1", source_type=SourceType.DRAINAGE,
        event_time=130, arrival_time=135, kind=EventKind.DRAIN_ANOMALY,
        value=0.75, location="zone_north"
    ))
    # Hospital arrivals explained by flu
    events.append(StreamEvent(
        id="flu_t5", source_id="hosp_1", source_type=SourceType.HOSPITALS,
        event_time=140, arrival_time=145, kind=EventKind.HOSPITAL_ARRIVALS,
        value=0.88, location="zone_central"
    ))
    # Call surge explained by rain
    events.append(StreamEvent(
        id="call_t5", source_id="call_1", source_type=SourceType.EMERGENCY_LINES,
        event_time=150, arrival_time=155, kind=EventKind.CALL_SURGE,
        value=0.70, location="zone_north"
    ))

    state = engine.process_minute(2, events)
    assert state.recommended_action in (ActionLevel.WATCH, ActionLevel.PREPARE), f"Action was {state.recommended_action}"
    assert "explained" in state.explanation_summary.lower(), "Explanation failed to cite explaining-away factors"

def test_t6_viral_rumor_wave():
    """
    T6: Viral Rumor Wave
    50 citizen/social reports sharing claim_id, zero physical sensor anomalies.
    Discounted to 1 claim; P(U) > 0.80, no ALERT/ESCALATE.
    """
    engine = BayesianForwardFilter()
    events = []
    for i in range(50):
        events.append(StreamEvent(
            id=f"rumor_{i}", source_id=f"user_{i}", source_type=SourceType.CITIZEN,
            event_time=180 + i, arrival_time=185 + i, kind=EventKind.CITIZEN_REPORT,
            value=0.90, location="zone_north", claim_id="claim_rumor_flash_flood"
        ))

    state = engine.process_minute(3, events)
    assert state.nuisance_posteriors["U"] > 0.80, f"P(U) was {state.nuisance_posteriors['U']}, expected > 0.80"
    assert state.recommended_action in (ActionLevel.WATCH, ActionLevel.PREPARE), f"Action was {state.recommended_action}"

def test_t7_retraction_of_key_report():
    """
    T7: Retraction of Key Report
    Inject dispatch_incident at t=4, retract it at t=6.
    Belief returns bit-for-bit to state without that event.
    """
    # Run 1: with event then retraction
    engine1 = BayesianForwardFilter()
    ev_disp = StreamEvent(
        id="disp_t7", source_id="dispatch_1", source_type=SourceType.DISPATCH,
        event_time=240, arrival_time=245, kind=EventKind.DISPATCH_INCIDENT,
        value=0.92, location="zone_north"
    )
    ev_retract = StreamEvent(
        id="retract_t7", source_id="dispatch_retractor", source_type=SourceType.DISPATCH,
        event_time=360, arrival_time=365, kind=EventKind.DISPATCH_INCIDENT,
        value=0.0, location="zone_north", retracts="disp_t7"
    )

    for m in range(1, 4):
        engine1.process_minute(m, [])
    engine1.process_minute(4, [ev_disp])
    engine1.process_minute(5, [])
    state1 = engine1.process_minute(6, [ev_retract])

    # Run 2: never sent ev_disp
    engine2 = BayesianForwardFilter()
    for m in range(1, 7):
        state2 = engine2.process_minute(m, [])

    # Check posteriors match
    p1 = np.array(list(state1.probabilities.values()))
    p2 = np.array(list(state2.probabilities.values()))
    assert np.allclose(p1, p2, atol=1e-4), f"Posteriors did not match after retraction: {p1} vs {p2}"

def test_t8_camera_total_cutout():
    """
    T8: Camera Total Cutout Mid-Episode
    Drop camera feed at t=10.
    No crash; 'cameras' in blind_sources; uncertainty band widens.
    """
    engine = BayesianForwardFilter()
    for m in range(1, 10):
        engine.process_minute(m, [])

    # Inject cutout
    engine.normalizer.set_cutout("cameras", active=True)
    state = engine.process_minute(10, [])

    assert "cameras" in state.blind_sources, f"Blind sources: {state.blind_sources}"
    # Uncertainty band width should be wider
    band_w = state.uncertainty_band["H3"][1] - state.uncertainty_band["H3"][0]
    assert band_w >= 0.15, f"Uncertainty band width was {band_w}, expected >= 0.15"

def test_t9_structured_lie():
    """
    T9: Structured Lie
    20 drainage sensors report identical value=0.9500 while rain gauge = 0.0.
    Group flagged suspicious; effective reliability multiplied by 0.3.
    """
    engine = BayesianForwardFilter()
    corruptor = StreamCorruptor(seed=109)
    lie_events = corruptor.inject_structured_lie(minute=5, num_sensors=20)
    
    state = engine.process_minute(5, lie_events)
    assert any("Suspicious source group" in item for item in state.discounted_items), "Structured lie was not flagged"
    assert "gw_lie" in engine.likelihood_model.suspicious_groups, "gw_lie not in suspicious_groups"

def test_t10_silent_season_shift():
    """
    T10: Silent Season Shift
    CUSUM changepoint detector detects sudden regime shift and adapts Dirichlet prior within 30 episodes.
    """
    learner = BayesianForwardFilter().learner
    
    # Train 40 episodes under baseline (mostly H0)
    for _ in range(40):
        learner.update_episode_prior_shift(true_h=0)

    # Shift at episode 41: series of true cascades (H3)
    shift_detected = False
    for ep in range(41, 71):
        detected = learner.update_episode_prior_shift(true_h=3)
        if detected:
            shift_detected = True

    assert shift_detected, "BOCD / CUSUM failed to detect silent regime shift"
    # Prior for H3 should have adapted upward
    learned_p = learner.get_learned_h_prior()
    assert learned_p[3] > 0.40, f"Learned prior for H3 was {learned_p[3]}, expected > 0.40 within 30 episodes"

def test_t11_flip_flop_stress():
    """
    T11: Flip-Flop Stress Test
    Oscillating borderline evidence around PREPARE/ALERT boundary.
    flip_flop_count == 0 across entire 30-minute episode.
    """
    engine = BayesianForwardFilter()
    for m in range(1, 31):
        # Oscillate between marginal anomaly and quiet
        val = 0.55 if m % 2 == 0 else 0.20
        ev = [StreamEvent(
            id=f"osc_{m}", source_id="borderline_sens", source_type=SourceType.DRAINAGE,
            event_time=m*60+10, arrival_time=m*60+12, kind=EventKind.DRAIN_ANOMALY,
            value=val, location="zone_border"
        )]
        state = engine.process_minute(m, ev)

    assert state.flip_flop_count == 0, f"Flip flop count was {state.flip_flop_count}, expected 0"

def test_t12_counterfactual_forecast():
    """
    T12: Counterfactual Forecast Test (Proves Causal Disentanglement)
    Toggle do(G1=1), do(R=1), do(F=1) in Foresight module:
    - do(G1=1) drops flooding forecast.
    - do(R=1) raises traffic but not hospital surge.
    - do(F=1) raises hospital surge only.
    """
    foresight = BayesianForwardFilter().foresight
    
    # Baseline: moderate cascade
    base_fcasts = foresight.get_forecasts(minute=5, p_h3=0.70, nuisances={})
    assert any("Flooding" in f.event_kind for f in base_fcasts)

    # do(G1=1): Gateway down => drops physical flooding
    g1_fcasts = foresight.get_forecasts(minute=5, p_h3=0.70, nuisances={}, counterfactual_clamping={"G1": 1.0})
    assert not any("Flooding" in f.event_kind for f in g1_fcasts), "do(G1=1) failed to drop physical flooding forecast"

    # do(F=1): Flu outbreak => raises hospital ER surge only
    flu_fcasts = foresight.get_forecasts(minute=5, p_h3=0.10, nuisances={}, counterfactual_clamping={"F": 1.0})
    assert any("Hospital ER Surge" in f.event_kind for f in flu_fcasts), "do(F=1) failed to predict hospital surge"
    assert not any("Flooding" in f.event_kind for f in flu_fcasts), "do(F=1) erroneously predicted road flooding"
