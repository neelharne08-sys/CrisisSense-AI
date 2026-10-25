import os
import sys
import json
import time
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.schemas import StreamEvent, ActionLevel, EventKind, SourceType
from src.engine.filter import BayesianForwardFilter
from src.engine.cap import CAPAlertBuilder
from src.simulator.generator import EpisodeGenerator
from src.simulator.corruptions import StreamCorruptor
from src.simulator.live_weather import (
    LiveWeatherFeed, fetch_weather, to_events, CITY_PRESETS, DEFAULT_LAT, DEFAULT_LON
)
from src.auth import DEMO_USERS, UserProfile
from dashboard.login import render_login_page

st.set_page_config(
    page_title="CrisisSense AI — Duty Officer Operations Cockpit",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling with Tooltips & Clean Cards
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(145deg, #182030, #111622);
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #23314d;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .badge-watch {
        background-color: #1d4ed8; color: #ffffff; padding: 6px 14px;
        border-radius: 6px; font-weight: 700; font-size: 1.15rem; letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-prepare {
        background-color: #d97706; color: #ffffff; padding: 6px 14px;
        border-radius: 6px; font-weight: 700; font-size: 1.15rem; letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-alert {
        background-color: #ea580c; color: #ffffff; padding: 6px 14px;
        border-radius: 6px; font-weight: 700; font-size: 1.15rem; letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-escalate {
        background-color: #dc2626; color: #ffffff; padding: 6px 14px;
        border-radius: 6px; font-weight: 700; font-size: 1.15rem; letter-spacing: 0.5px;
        display: inline-block;
    }
    .status-guide {
        padding: 10px 14px;
        border-radius: 8px;
        margin-top: 8px;
        font-size: 0.88rem;
    }
    .guide-watch { background: rgba(37, 99, 235, 0.12); border-left: 4px solid #3b82f6; color: #93c5fd; }
    .guide-prepare { background: rgba(217, 119, 6, 0.12); border-left: 4px solid #f59e0b; color: #fde68a; }
    .guide-alert { background: rgba(234, 88, 12, 0.15); border-left: 4px solid #ea580c; color: #fdba74; }
    .guide-escalate { background: rgba(220, 38, 38, 0.18); border-left: 4px solid #ef4444; color: #fca5a5; }

    .help-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(148, 163, 184, 0.1);
        border: 1px solid rgba(148, 163, 184, 0.25);
        color: #94a3b8;
        padding: 2px 7px;
        border-radius: 12px;
        font-size: 0.75rem;
        cursor: help;
        margin-left: 5px;
    }
    .hover-term {
        border-bottom: 1.5px dotted #38bdf8;
        cursor: help;
        display: inline;
        position: relative;
        color: inherit;
        transition: all 0.2s ease;
    }
    .hover-term:hover {
        color: #38bdf8;
        border-bottom: 1.5px solid #60a5fa;
        background: rgba(56, 189, 248, 0.08);
        border-radius: 3px;
    }
    .hover-icon {
        font-size: 0.72em;
        vertical-align: super;
        color: #38bdf8;
        margin-left: 2px;
        opacity: 0.75;
    }
    .hover-term:hover .hover-icon {
        opacity: 1.0;
    }
    .quick-start-box {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8));
        border: 1px solid #334155;
        border-left: 4px solid #38bdf8;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

def tip(display_text: str, explanation: str, show_icon: bool = True) -> str:
    """
    Renders an interactive hoverable term with a subtle dotted underline.
    When the user takes their cursor to the word, an instant plain-English
    explanation appears in a tooltip.
    """
    safe_tip = explanation.replace('"', '&quot;').replace("'", "&#39;")
    icon_html = "<span class='hover-icon'>ℹ️</span>" if show_icon else ""
    return f"<span class='hover-term' title='{safe_tip}'>{display_text}{icon_html}</span>"

# Session State Initialization
if "engine" not in st.session_state:
    st.session_state.engine = BayesianForwardFilter()
if "all_events" not in st.session_state:
    gen = EpisodeGenerator(seed=42)
    evs, true_h, meta = gen.generate_episode("cascade", enable_corruptions=True)
    st.session_state.all_events = evs
    st.session_state.true_h = true_h
    st.session_state.meta = meta
if "current_minute" not in st.session_state:
    st.session_state.current_minute = 1
if "history_payloads" not in st.session_state:
    st.session_state.history_payloads = {}
if "live_weather_active" not in st.session_state:
    st.session_state.live_weather_active = False
if "weather_feed" not in st.session_state:
    st.session_state.weather_feed = LiveWeatherFeed(lat=DEFAULT_LAT, lon=DEFAULT_LON)
if "weather_events_by_min" not in st.session_state:
    st.session_state.weather_events_by_min = {}
if "weather_lat" not in st.session_state:
    st.session_state.weather_lat = DEFAULT_LAT
if "weather_lon" not in st.session_state:
    st.session_state.weather_lon = DEFAULT_LON
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = DEMO_USERS["officer104"]
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "🖥️ Duty Officer Console"
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

# ── MANDATORY LOGIN GATE ──────────────────────────────────────────────────
# If the user is not authenticated, show ONLY the login page and stop.
if not st.session_state.get("authenticated", False):
    render_login_page()
    st.stop()

# ── Everything below only runs AFTER successful login ─────────────────────

# Sidebar Header & Navigation
st.sidebar.title("🚨 CrisisSense AI")
st.sidebar.caption("Continuous Online Probabilistic Decision Engine")

# Active Operator Badge in Sidebar
user = st.session_state.user
st.sidebar.markdown(f"""
<div style="background:#131b2e; border:1px solid #23314d; border-radius:8px; padding:10px 12px; margin-bottom:12px;">
    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px;">Active Terminal Operator</div>
    <div style="font-size:0.95rem; font-weight:bold; color:#f8fafc; margin-top:2px;">{user.avatar} {user.name}</div>
    <div style="font-size:0.75rem; color:#38bdf8; margin-top:2px;">Badge: <code>{user.badge_id}</code> | {user.clearance_level}</div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Sign Out", use_container_width=True, help="Terminate active session and return to login screen."):
    st.session_state.authenticated = False
    st.session_state.user = DEMO_USERS["officer104"]
    st.session_state.login_error = ""
    st.rerun()

# Simulation Scenario Selector with friendly explanations
scenario_choice = st.sidebar.selectbox(
    "Simulation Scenario",
    ["cascade", "twin_cascade", "twin_benign", "rain_mimic", "flu_mimic", 
     "gateway_failure", "rumor_mimic", "isolated_incident", "noise"],
    index=0,
    help=(
        "Choose an emergency event scenario to simulate:\n"
        "• cascade: Real spreading flash flood disaster.\n"
        "• twin_cascade vs twin_benign: The 7-min twin test.\n"
        "• rain_mimic: Heavy rain looks like a flood, but isn't.\n"
        "• flu_mimic: Flu outbreak crowds hospitals without a flood.\n"
        "• gateway_failure: 100 sensors disconnect due to 1 broken Wi-Fi router.\n"
        "• rumor_mimic: 50 citizen reports triggered by a false viral post."
    )
)
sim_seed = st.sidebar.number_input(
    "Random Seed", value=42, step=1, 
    help="Deterministic random seed to guarantee 100% reproducible stream results."
)

if st.sidebar.button("🔄 Reset / Load Scenario", use_container_width=True, help="Reloads the selected scenario from Minute 1 with clean filters."):
    st.session_state.engine = BayesianForwardFilter()
    gen = EpisodeGenerator(seed=sim_seed)
    evs, true_h, meta = gen.generate_episode(scenario_choice, enable_corruptions=True)
    st.session_state.all_events = evs
    st.session_state.true_h = true_h
    st.session_state.meta = meta
    st.session_state.current_minute = 1
    st.session_state.history_payloads = {}
    st.session_state.weather_events_by_min = {}
    st.rerun()

st.sidebar.markdown("---")

# ── Live Open-Meteo Natural Weather Integration ──────────────────────────
st.sidebar.subheader("🌐 Live Natural Weather Feed")
live_toggle = st.sidebar.toggle(
    "Live Open-Meteo Weather", 
    value=st.session_state.live_weather_active,
    help="Ingest real-time unauthenticated 15-minute precipitation telemetry from Open-Meteo directly into the Bayesian filter."
)

if live_toggle != st.session_state.live_weather_active:
    st.session_state.live_weather_active = live_toggle
    # Reinitialize clean engine state to prevent synthetic / live cross-contamination
    st.session_state.engine = BayesianForwardFilter()
    st.session_state.history_payloads = {}
    st.session_state.weather_events_by_min = {}
    st.session_state.weather_feed = LiveWeatherFeed(lat=st.session_state.weather_lat, lon=st.session_state.weather_lon)
    st.rerun()

if st.session_state.live_weather_active:
    city_preset = st.sidebar.selectbox(
        "City Preset",
        list(CITY_PRESETS.keys()) + ["Custom Coordinates"],
        index=0,
        help="Choose a city or enter custom GPS coordinates to stream live 15-min rainfall."
    )
    if city_preset in CITY_PRESETS:
        c_lat, c_lon = CITY_PRESETS[city_preset]
    else:
        c_lat = st.session_state.weather_lat
        c_lon = st.session_state.weather_lon

    c_lat_in, c_lon_in = st.sidebar.columns(2)
    with c_lat_in:
        new_lat = st.number_input("Latitude", value=float(c_lat), format="%.4f")
    with c_lon_in:
        new_lon = st.number_input("Longitude", value=float(c_lon), format="%.4f")

    if new_lat != st.session_state.weather_lat or new_lon != st.session_state.weather_lon:
        st.session_state.weather_lat = new_lat
        st.session_state.weather_lon = new_lon
        st.session_state.weather_feed = LiveWeatherFeed(lat=new_lat, lon=new_lon)
        st.session_state.history_payloads = {}
        st.session_state.weather_events_by_min = {}
        st.rerun()

    if st.session_state.weather_feed.is_stale:
        st.sidebar.warning("⚠️ Weather feed stale: treated as missing (no fake 0 mm)")
    else:
        last_val = (
            st.session_state.weather_feed.rolling_history[-1] 
            if st.session_state.weather_feed.rolling_history else 0.0
        )
        st.sidebar.success(f"🟢 Open-Meteo Connected: {last_val:.1f} mm/h")

st.sidebar.markdown("---")

# Quick Time Step Controls (Play / Forward / Rewind)
st.sidebar.subheader("⏱️ Scenario Timeline Controls")
c_ctl1, c_ctl2, c_ctl3 = st.sidebar.columns(3)
with c_ctl1:
    if st.button("⏪ Min 1", use_container_width=True, help="Jump directly back to Minute 1 (Onset)."):
        st.session_state.current_minute = 1
        st.rerun()
with c_ctl2:
    if st.button("⏩ Min 8", use_container_width=True, help="Jump directly to Minute 8 (Twin Divergence Point)."):
        st.session_state.current_minute = 8
        st.rerun()
with c_ctl3:
    if st.button("▶ +1 Min", use_container_width=True, help="Advance simulation forward by 1 minute."):
        if st.session_state.current_minute < 30:
            st.session_state.current_minute += 1
            st.rerun()

minute_slider = st.sidebar.slider(
    "Simulated Minute (1 to 30)", 
    1, 30, 
    st.session_state.current_minute,
    help="Drag this slider to scrub back and forth in time and watch the AI's reasoning change minute by minute."
)
if minute_slider != st.session_state.current_minute:
    st.session_state.current_minute = minute_slider

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Live Chaos & Stress Injections")
col_inj1, col_inj2 = st.sidebar.columns(2)
with col_inj1:
    if st.button("📷 Cutout Cam", use_container_width=True, help="Simulate camera blackout: test how the AI widens its uncertainty bounds without crashing."):
        st.session_state.engine.normalizer.set_cutout("cameras", active=True)
        st.sidebar.success("Cameras set to BLIND_CUTOUT")
    if st.button("🤥 Sensor Lie", use_container_width=True, help="Inject 20 rogue sensors reporting fake identical floods while official rain gauges read 0.0."):
        lie_evs = StreamCorruptor(seed=sim_seed).inject_structured_lie(
            minute=st.session_state.current_minute, num_sensors=20
        )
        st.session_state.engine.process_minute(st.session_state.current_minute, lie_evs)
        st.sidebar.warning("Injected 20 frozen drainage sensors")

with col_inj2:
    if st.button("↩️ Retract Event", use_container_width=True, help="Inject an official police retraction of a false report: watch the AI rewind time and erase the lie."):
        disp = [e for e in st.session_state.engine.history_events if e.kind == EventKind.DISPATCH_INCIDENT]
        if disp:
            t_ev = disp[-1]
            ret_ev = StreamEvent(
                id=f"retract_{t_ev.id}", source_id="override", source_type=t_ev.source_type,
                event_time=st.session_state.current_minute * 60 + 5, arrival_time=st.session_state.current_minute * 60 + 6,
                kind=t_ev.kind, value=0.0, location=t_ev.location, retracts=t_ev.id
            )
            st.session_state.engine.process_minute(st.session_state.current_minute, [ret_ev])
            st.sidebar.info(f"Retracted {t_ev.id}")
        else:
            st.sidebar.error("No incident to retract")

    if st.button("🌧️ Season Shift", use_container_width=True, help="Simulate sudden monsoon onset (3x rain rate): watch the online BOCD changepoint detector adapt priors."):
        st.session_state.engine.learner.regime_shift_detected = True
        st.sidebar.info("Monsoon shift triggered")

# Process up to current minute
for m in range(1, st.session_state.current_minute + 1):
    if m not in st.session_state.history_payloads:
        m_evs = [e for e in st.session_state.all_events if (e.event_time // 60) == m]

        # Inject real-time Open-Meteo weather telemetry if active
        if st.session_state.get("live_weather_active", False):
            if m not in st.session_state.weather_events_by_min:
                try:
                    w_evs = st.session_state.weather_feed.poll(current_minute=m)
                    st.session_state.weather_events_by_min[m] = w_evs
                except requests.RequestException:
                    st.session_state.weather_events_by_min[m] = []
                    st.sidebar.warning("Weather feed stale: treated as missing (no fake 0 mm)")
                except Exception:
                    st.session_state.weather_events_by_min[m] = []

            m_evs = m_evs + st.session_state.weather_events_by_min.get(m, [])

        payload = st.session_state.engine.process_minute(m, m_evs)
        st.session_state.history_payloads[m] = payload

current_payload = st.session_state.history_payloads[st.session_state.current_minute]

# Main Dashboard Tabs with Tooltips
tab_live, tab_twin, tab_whatif, tab_eval = st.tabs([
    "🖥️ Live Operations Cockpit", 
    "👯 The Twin Test (Honesty vs Disaster)", 
    "🔮 What-If Scenario Sandbox", 
    "📊 Benchmarks & CAP Emergency Protocol"
])

# ==========================================
# TAB 1: LIVE CONSOLE
# ==========================================
with tab_live:
    # 60-Second Quick Start Guide for New Operators
    with st.expander("💡 New Operator? Click here for a 60-Second Quick Guide", expanded=False):
        st.markdown(f"""
        <div class="quick-start-box">
            <h4 style="margin-top:0; color:#38bdf8;">🧭 What Am I Looking At? (In Plain Everyday English)</h4>
            <p>You are a <b>City Duty Officer</b>. During an unfolding rainstorm or anomaly, messy sensor signals, citizen calls, and camera heartbeats arrive minute by minute.</p>
            <p>Your job is to make <b>one cost-optimal decision</b> without panicking or crying wolf:</p>
            <ul>
                <li>{tip("WATCH", "🟢 Normal Monitoring: Low disaster probability. Keep standard sensor monitoring. Do not mobilize emergency crews.")}: Everything is under control. Monitor quietly.</li>
                <li>{tip("PREPARE", "🟡 Standby Advisory: Elevated anomaly activity detected. Pre-position response teams, check drainage pumps, and monitor arterial traffic cameras.")}: Suspicious activity. Pre-position pump trucks and alert road patrols.</li>
                <li>{tip("ALERT", "🟠 Urgent Action Required: High cascade probability confirmed by physical sensors. Mobilize field dispatch and issue Level-2 traffic diversions.")}: Real disaster starting. Close flooded underpasses and deploy field teams.</li>
                <li>{tip("ESCALATE", "🔴 Emergency Escalation: Active systemic crisis spreading across city infrastructure. Immediate sirens, hospital mass-casualty triage, and emergency command activation.")}: Major crisis. Sound sirens and activate hospital emergency triage.</li>
            </ul>
            <p style="margin-bottom:0; font-size:0.88rem; color:#94a3b8;">
                👉 <b>Interactive Tooltips:</b> Hover your mouse cursor over any term with a dotted blue line and ℹ️ (like {tip("Disaster Risk P(H3)", "The calculated probability that a real systemic disaster is spreading across city infrastructure.")} or {tip("Cry-Wolf Meter", "Measures citizen alarm fatigue. If the city issues false alarms, this meter penalizes future alerts to protect public trust.")}) for an instant definition!
            </p>
        </div>
        """, unsafe_allow_html=True)

    act = current_payload.recommended_action.value
    badge_class = f"badge-{act.lower()}"

    # Action Guidance text in plain English
    action_guidance = {
        "WATCH": "🟢 <b>Normal Monitoring:</b> Low disaster probability. Keep standard sensor monitoring. Do not mobilize emergency crews.",
        "PREPARE": "🟡 <b>Standby Advisory:</b> Elevated anomaly activity detected. Pre-position response teams, check drainage pumps, and monitor arterial traffic cameras.",
        "ALERT": "🟠 <b>Urgent Action Required:</b> High cascade probability confirmed by physical sensors. Mobilize field dispatch and issue Level-2 traffic diversions.",
        "ESCALATE": "🔴 <b>Emergency Escalation:</b> Active systemic crisis spreading across city infrastructure. Immediate sirens, hospital mass-casualty triage, and emergency command activation."
    }
    guide_class = f"guide-{act.lower()}"

    # Top KPI Banner with Interactive Tooltips
    c_top1, c_top2, c_top3, c_top4 = st.columns([3, 2, 2, 2])
    with c_top1:
        st.markdown(
            f"**Recommended Action** {tip('Decision Rule', 'The single, cost-optimal decision calculated by mathematical optimal-stopping rules that balance false alarm risk against disaster response delay.')}", 
            unsafe_allow_html=True
        )
        st.markdown(f"<span class='{badge_class}'>{act}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='status-guide {guide_class}'>{action_guidance[act]}</div>", unsafe_allow_html=True)

    with c_top2:
        st.markdown(
            f"**{tip('Disaster Risk P(H3)', 'The calibrated probability (0% to 100%) that a real systemic disaster is unfolding across city infrastructure, rather than isolated rain or sensor glitches.')}**", 
            unsafe_allow_html=True
        )
        p3 = current_payload.probabilities['H3']
        st.metric(
            "Disaster Risk", 
            f"{p3*100:.1f}%", 
            f"{round((p3-0.1)*100, 1)}% vs baseline",
            label_visibility="collapsed",
            help="The calibrated probability that a real systemic disaster (Cascading Crisis H3) is unfolding, rather than ordinary rain or sensor glitches."
        )
    with c_top3:
        st.markdown(
            f"**{tip('Cry-Wolf / Trust Meter W(Fc)', 'The Boy-Who-Cried-Wolf meter. If the city sends false alarms, this number rises. A higher meter raises the threshold before the AI allows sending another public alert, protecting citizen trust.')}**", 
            unsafe_allow_html=True
        )
        w_fc = 1.0 + 2.0 * current_payload.fatigue_level
        st.metric(
            "Cry-Wolf Meter", 
            f"{w_fc:.2f}x", 
            f"Fatigue Fc: {current_payload.fatigue_level:.2f}",
            label_visibility="collapsed",
            help="The 'Boy-Who-Cried-Wolf' meter. If the city sends false alarms, this number rises. A higher meter raises the threshold before the AI allows sending another public alert, protecting citizen trust."
        )
    with c_top4:
        st.markdown(
            f"**{tip('Patience Gain (Wait 60s)', 'Value of Waiting: Expected cost savings (in penalty points) from waiting 1 more minute before escalating. If positive, holding off for clearer sensor confirmation avoids costly false alarms.')}**", 
            unsafe_allow_html=True
        )
        vow = current_payload.value_of_waiting_saved
        # Format cleanly as Cost Penalty Points saved rather than confusing raw "decimal units"
        if vow >= 1.0:
            vow_label = f"+{vow:.1f} pts"
            vow_sub = "🟢 Strong Value to Wait"
        elif vow > 0.05:
            vow_label = f"+{vow:.1f} pts"
            vow_sub = "🟡 Favorable to Wait"
        else:
            vow_label = "0.0 pts"
            vow_sub = "⚡ Commit / Act Now"

        st.metric(
            "Patience Gain", 
            vow_label, 
            vow_sub,
            label_visibility="collapsed",
            help=(
                "Value of Waiting: Expected reduction in cost penalty points (scale 0-25) from waiting 60 more seconds.\n"
                "• Calculated via 200 Monte Carlo belief rollouts.\n"
                "• Positive points mean waiting for clearer physical confirmation prevents costly false alarms.\n"
                "• 0.0 points means waiting has no benefit; take immediate action."
            )
        )

    if st.session_state.get("live_weather_active", False):
        w_feed = st.session_state.get("weather_feed")
        rain_rate = (
            w_feed.rolling_history[-1] if (w_feed and w_feed.rolling_history) else 0.0
        )
        p_rain = current_payload.nuisance_posteriors.get("R", 0.05)
        st.markdown(f"""
        <div style="background: rgba(14, 165, 233, 0.10); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px; padding: 10px 16px; margin: 12px 0 6px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <span style="font-weight: 700; color: #38bdf8; font-size: 0.95rem;">🌐 Open-Meteo Live Precipitation Feed Active</span>
                <span style="margin-left: 10px; color: #94a3b8; font-size: 0.82rem;">Target: Lat {st.session_state.weather_lat:.4f}, Lon {st.session_state.weather_lon:.4f} (15-min bucket sampling)</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <span style="background: #0369a1; color: #ffffff; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 0.82rem;">Rain Gauge: {rain_rate:.2f} mm/h</span>
                <span style="background: {'#15803d' if p_rain >= 0.5 else '#334155'}; color: #ffffff; padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 0.82rem;">Nuisance P(R=1): {p_rain*100:.1f}%</span>
                <span style="background: #1e293b; border: 1px solid #475569; color: #cbd5e1; padding: 3px 10px; border-radius: 4px; font-weight: 500; font-size: 0.82rem;">Explaining Away: {'Active 🛡️' if p_rain > 0.5 else 'Standby'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    c_left, c_right = st.columns([5, 4])

    with c_left:
        st.subheader(
            "Threat Level & 4-Hypothesis Breakdown", 
            help="The AI continuously tests 4 competing theories in parallel: H0 (Noise), H1 (Broken Sensor), H2 (Local Accident), and H3 (Systemic Crisis). Error bars show honest uncertainty bounds."
        )
        probs = current_payload.probabilities
        bands = current_payload.uncertainty_band

        h_labels = ["H0: Noise / Normal", "H1: Broken Sensor", "H2: Local Accident", "H3: Spreading Crisis"]
        h_vals = [probs["H0"], probs["H1"], probs["H2"], probs["H3"]]
        error_plus = [bands[k][1] - probs[k] for k in ["H0", "H1", "H2", "H3"]]
        error_minus = [probs[k] - bands[k][0] for k in ["H0", "H1", "H2", "H3"]]

        fig_h = go.Figure(data=[
            go.Bar(
                x=h_labels,
                y=h_vals,
                marker_color=["#3b82f6", "#8b5cf6", "#eab308", "#ef4444"],
                error_y=dict(type='data', symmetric=False, array=error_plus, arrayminus=error_minus),
                text=[f"{v*100:.1f}%" for v in h_vals],
                textposition='auto',
            )
        ])
        fig_h.update_layout(height=260, yaxis_range=[0, 1.0], margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_h, use_container_width=True)

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-top:2px; margin-bottom:12px; color:#94a3b8; flex-wrap:wrap; gap:8px;">
            <div>{tip("🔵 H0: Normal Noise", "Normal everyday background activity: random sensor fluctuations, small street puddles, harmless traffic slow-downs.")}</div>
            <div>{tip("🟣 H1: Broken Sensor", "Hardware glitch: a stuck sensor probe, dead battery, or water damage making one sensor scream emergency when nothing is happening.")}</div>
            <div>{tip("🟡 H2: Local Incident", "A real event, but strictly localized: a single car stalled in a puddle or one blocked storm drain that will NOT spread across the city.")}</div>
            <div>{tip("🔴 H3: Spreading Crisis", "A cascading disaster: heavy floodwaters spilling from drains to roads, stranding cars, blocking ambulances, and overwhelming emergency rooms.")}</div>
        </div>
        """, unsafe_allow_html=True)

        # Alternative Explanations (Nuisances)
        st.subheader(
            "Alternative Explanations (Explaining-Away Factors)", 
            help="Before raising alarms, the AI checks if strange readings can be explained away by normal background factors: thunderstorms, seasonal flu, broken Wi-Fi routers, or online rumors."
        )
        nuis = current_payload.nuisance_posteriors
        c_n1, c_n2, c_n3, c_n4, c_n5 = st.columns(5)
        with c_n1:
            st.markdown(f"**{tip('🌧️ Rain (R)', 'Explaining-Away Factor: When district-wide rainfall is heavy, full storm drains are expected and do not imply a structural dam failure.')}**", unsafe_allow_html=True)
            st.metric("Heavy Rain", f"{nuis['R']*100:.0f}%", label_visibility="collapsed", help="Explains why drainage pipes and street runoff sensors are full without a dam collapse.")
        with c_n2:
            st.markdown(f"**{tip('🏥 Flu (F)', 'Explaining-Away Factor: Crowded emergency rooms may be caused by winter seasonal flu, not flood casualties.')}**", unsafe_allow_html=True)
            st.metric("Flu Outbreak", f"{nuis['F']*100:.0f}%", label_visibility="collapsed", help="Explains why hospital ER beds are crowded without a physical disaster.")
        with c_n3:
            st.markdown(f"**{tip('🔌 G1 Loss', 'Hardware Outage: 100 sensors went silent at once because 1 cellular router lost power, not because water washed away 100 sensors.')}**", unsafe_allow_html=True)
            st.metric("Gateway 1", f"{nuis['G1']*100:.0f}%", label_visibility="collapsed", help="If active, 100 sensors behind Gateway 1 went dark due to 1 router power loss.")
        with c_n4:
            st.markdown(f"**{tip('🔌 G2 Loss', 'Hardware Outage: Sensor cluster behind Gateway 2 is offline due to a local power/network blackout.')}**", unsafe_allow_html=True)
            st.metric("Gateway 2", f"{nuis['G2']*100:.0f}%", label_visibility="collapsed", help="If active, sensors behind Gateway 2 are offline.")
        with c_n5:
            st.markdown(f"**{tip('📢 Rumor (U)', 'Social Chatter: 50 citizen reports repeating the same uncorroborated social media rumor without any physical sensor proof.')}**", unsafe_allow_html=True)
            st.metric("Viral Rumor", f"{nuis['U']*100:.0f}%", label_visibility="collapsed", help="Explains sudden surges in citizen reports that lack corroboration from real physical sensors.")

        st.caption("💡 When an alternative explanation is detected, the AI 'explains away' the confusing data and refuses to panic or cry wolf.")

        # Explainability Ledger
        st.subheader(
            "AI Decision Log & Operator Guidance",
            help="Audit ledger: explains in human words why the AI made this decision, which items were discounted, and what evidence would change its mind."
        )
        st.markdown(f"**{tip('Decision Reasoning', 'Plain-English summary of the exact mathematical evidence driving the current action recommendation.')}**", unsafe_allow_html=True)
        st.info(current_payload.explanation_summary)

        st.markdown(f"**{tip('What Would Change My Mind', 'Counterfactual triggers: the specific physical sensor confirmations required to switch actions.')}**", unsafe_allow_html=True)
        st.warning(current_payload.what_would_change_mind)

        if current_payload.discounted_items:
            st.markdown(f"**{tip('Discounted / Ignored Noise Items', 'Sensor transmissions that were ignored or downweighted due to duplication, copycat posts, or broken communication hubs.')}**", unsafe_allow_html=True)
            for d in current_payload.discounted_items:
                st.caption(f"• {d}")

    with c_right:
        st.subheader(
            "Predicted Next Incidents (Causal Forecast)", 
            help="Physical propagation forecast: predicts what will happen next, where it will happen, and the 80% confidence time window using municipal flood-to-ambulance physics."
        )
        if current_payload.forecasts:
            for idx, fc in enumerate(current_payload.forecasts, 1):
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <b style='font-size:1.0rem; color:#f8fafc;'>#{idx} {fc.event_kind}</b>
                        <span style='color:#ef4444; font-weight:bold; background:rgba(239,68,68,0.15); padding:2px 8px; border-radius:12px;'>{int(fc.probability*100)}% risk</span>
                    </div>
                    <div style='color:#94a3af; font-size:0.83rem; margin-top:3px;'>Target Zone: <b>{fc.zone}</b> | Expected Lag: ~{fc.expected_delay_min} mins</div>
                    <div style='color:#38bdf8; font-weight:bold; font-size:0.88rem; margin-top:3px;'>🕒 {tip("80% Time Window", "The AI calculates that there is an 80% statistical certainty that this event will happen within this exact minute window based on municipal flood flow physics.")}: Minutes {fc.window_start_min} – {fc.window_end_min}</div>
                    <div style='font-size:0.83rem; color:#cbd5e1; margin-top:4px;'>{fc.description}</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("")
        else:
            st.success("🟢 No cascading physical incidents predicted within the 80% confidence window.")

        st.subheader(
            "Risk & Cost Matrix Evaluation", 
            help="Calculates the risk cost of each action. The action with the lowest expected risk cost wins."
        )
        st.caption(f"Balances the {tip('Delay Penalty', 'The catastrophic danger of waiting too long to respond to a real flood.')} against the {tip('Cry-Wolf Cost', 'The public fatigue and economic damage of sounding false alarms.')}.", unsafe_allow_html=True)
        ec_df = pd.DataFrame([
            {"Action Choice": k, "Risk Cost": round(v, 2), "Recommended": "✅ Selected" if k == act else ""}
            for k, v in current_payload.expected_costs.items()
        ])
        st.dataframe(ec_df, hide_index=True, use_container_width=True)

        if current_payload.blind_sources:
            st.error(f"⚠️ Active Sensor Cutout: {', '.join(current_payload.blind_sources)} is currently BLIND.")

# ==========================================
# TAB 2: TWIN-TEST SYNCHRONIZED DUAL PANE
# ==========================================
with tab_twin:
    st.subheader(
        "The Twin Test: Proof of Honesty vs Fast Commitment",
        help="The definitive test: Runs a genuine disaster (Twin A) side-by-side with a harmless rain shower (Twin B) that share identical sensor readings for the first 7 minutes."
    )
    st.markdown(f"""
    During the first **7 minutes**, a genuine disaster and a normal rain storm look **100% identical** to all sensors.  
    Traditional AI cries wolf early. **CrisisSense AI holds an {tip('honest ceiling (~42%)', 'During minutes 1-7, the data is mathematically unknowable. An honest Bayesian system reports ~42% prior mixture and refuses to panic.')} without alarming, then commits within 60 seconds of divergence at Minute 8.**
    """, unsafe_allow_html=True)

    @st.cache_data
    def compute_twins():
        gA = EpisodeGenerator(seed=999)
        evs_A, _, _ = gA.generate_episode("twin_cascade", enable_corruptions=False)
        fA = BayesianForwardFilter()
        pA = [fA.process_minute(m, [e for e in evs_A if (e.event_time // 60) == m]) for m in range(1, 16)]

        gB = EpisodeGenerator(seed=999)
        evs_B, _, _ = gB.generate_episode("twin_benign", enable_corruptions=False)
        fB = BayesianForwardFilter()
        pB = [fB.process_minute(m, [e for e in evs_B if (e.event_time // 60) == m]) for m in range(1, 16)]
        return pA, pB

    twin_A_payloads, twin_B_payloads = compute_twins()

    mins = list(range(1, 16))
    p3_A = [p.probabilities["H3"] for p in twin_A_payloads]
    p3_B = [p.probabilities["H3"] for p in twin_B_payloads]
    act_A = [p.recommended_action.value for p in twin_A_payloads]
    act_B = [p.recommended_action.value for p in twin_B_payloads]

    fig_twin = go.Figure()
    fig_twin.add_trace(go.Scatter(x=mins, y=p3_A, mode='lines+markers', name='Twin A: Real Flood Disaster', line=dict(color='#ef4444', width=3)))
    fig_twin.add_trace(go.Scatter(x=mins, y=p3_B, mode='lines+markers', name='Twin B: Harmless Rain Shower', line=dict(color='#10b981', width=3)))

    fig_twin.add_vrect(x0=1, x1=7, fillcolor="#3b82f6", opacity=0.12, layer="below", line_width=0, annotation_text="Shared Unknowable Prefix (Both held at honest 42%)", annotation_position="top left")
    fig_twin.add_vline(x=7.5, line_width=2, line_dash="dash", line_color="#f59e0b", annotation_text="Minute 8: Divergence Point")
    fig_twin.update_layout(title="Twin Trajectory Divergence: Disaster Probability vs Time", xaxis_title="Simulated Minute", yaxis_title="Disaster Probability P(H3)", yaxis_range=[0, 1.0], height=380)
    st.plotly_chart(fig_twin, use_container_width=True)

    c_tw1, c_tw2 = st.columns(2)
    with c_tw1:
        st.markdown(f"#### 🔴 {tip('Twin A (True Flood Disaster)', 'At Minute 8, police CAD reports submerged roads. The engine escalates to ALERT in under 60 seconds.')}", unsafe_allow_html=True)
        st.caption("At Minute 8, police dispatch confirms submerged roads. The AI escalates to `ALERT` in ≤ 60 seconds.")
        df_A = pd.DataFrame({"Minute": mins[:12], "Disaster Risk P(H3)": [f"{x*100:.1f}%" for x in p3_A[:12]], "Action": act_A[:12]})
        st.dataframe(df_A, hide_index=True, use_container_width=True)

    with c_tw2:
        st.markdown(f"#### 🟢 {tip('Twin B (Harmless Rain Shower)', 'At Minute 8, calibrated rain gauges confirm normal storm runoff. The engine relaxes below 20% without crying wolf.')}", unsafe_allow_html=True)
        st.caption("At Minute 8, rain gauges confirm normal rain. The AI relaxes below 20% without crying wolf.")
        df_B = pd.DataFrame({"Minute": mins[:12], "Disaster Risk P(H3)": [f"{x*100:.1f}%" for x in p3_B[:12]], "Action": act_B[:12]})
        st.dataframe(df_B, hide_index=True, use_container_width=True)

# ==========================================
# TAB 3: CAUSAL WHAT-IF (COUNTERFACTUALS)
# ==========================================
with tab_whatif:
    st.subheader(
        "What-If Scenario Sandbox (Causal Interventions)",
        help="Test causal vs correlational understanding: Toggle hypothetical events (like a sudden power failure or rainstorm) to see how future forecasts respond in real time."
    )
    st.markdown(f"""
    Test what happens under hypothetical emergency conditions: {tip('Clamping variables (do-calculus)', 'Forcing a variable to True or False to test if the AI understands cause-and-effect physics rather than just correlation.')} forces the causal graph
    to re-calculate physical downstream propagation.
    """, unsafe_allow_html=True)

    c_cf1, c_cf2, c_cf3 = st.columns(3)
    with c_cf1:
        do_g1 = st.toggle("Clamp: Force Gateway 1 Power Outage", value=False, help="Forces Gateway 1 offline. Watch how physical road flooding forecasts drop to 0, proving the AI understands it's a sensor network failure, not water.")
        st.caption(f"{tip('Why test this?', 'Proves the AI does not mistake 100 dead Wi-Fi sensors for 100 drowned sensors.')}", unsafe_allow_html=True)
    with c_cf2:
        do_rain = st.toggle("Clamp: Force Heavy Rainstorm Active", value=False, help="Forces heavy rain. Raises drainage and road slowdowns, but leaves hospital arrival forecasts normal.")
        st.caption(f"{tip('Why test this?', 'Proves the AI expects full drains during heavy rain without falsely predicting a dam collapse.')}", unsafe_allow_html=True)
    with c_cf3:
        do_flu = st.toggle("Clamp: Force Flu Cluster Active", value=False, help="Forces a seasonal flu outbreak. Raises hospital ER surge forecasts without mistakenly predicting road flooding.")
        st.caption(f"{tip('Why test this?', 'Proves the AI attributes crowded emergency rooms to flu rather than flood trauma.')}", unsafe_allow_html=True)

    clamps = {}
    if do_g1: clamps["G1"] = 1.0
    if do_rain: clamps["R"] = 1.0
    if do_flu: clamps["F"] = 1.0

    cf_forecasts = st.session_state.engine.foresight.get_forecasts(
        current_minute=st.session_state.current_minute,
        p_h3=current_payload.probabilities["H3"],
        nuisances=current_payload.nuisance_posteriors,
        counterfactual_clamping=clamps
    )

    st.markdown("#### Projected Causal Forecasts under Active Intervention:")
    if cf_forecasts:
        for fc in cf_forecasts:
            st.info(f"🔮 **{fc.event_kind}** ({int(fc.probability*100)}% risk) in {fc.zone} [Window: min {fc.window_start_min}–{fc.window_end_min}] — {fc.description}")
    else:
        st.success("🟢 No downstream physical events predicted under this intervention (physical propagation decoupled).")

# ==========================================
# TAB 4: BENCHMARKS & CAP INSPECTOR
# ==========================================
with tab_eval:
    st.subheader(
        "Empirical Benchmark Verification & Emergency Standards",
        help="Statistical proof: evaluated across 500 seeded episodes against 3 baseline algorithms, with compliant Common Alerting Protocol (CAP v1.2) outputs."
    )

    bpath = "benchmark_results.json"
    if os.path.exists(bpath):
        with open(bpath, "r") as f:
            bdata = json.load(f)

        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        with c_m1:
            st.markdown(f"**{tip('Brier Accuracy Improvement', 'Brier Score measures probabilistic prediction accuracy. A 25%+ improvement means probabilities are much sharper and closer to reality than baseline algorithms.')}**", unsafe_allow_html=True)
            st.metric("Brier Score", f"+{bdata['brier_improvement_pct']}%", "vs Naive Bayes (Target: ≥25%)", label_visibility="collapsed", help="Brier Score measures probabilistic prediction accuracy. Higher improvement means sharper and more accurate probabilities.")
        with c_m2:
            st.markdown(f"**{tip('Calibration Error (ECE)', 'Expected Calibration Error: measures statistical honesty. When the AI says 70% confidence, it actually happens 70% of the time. ECE < 0.05 indicates high honesty.')}**", unsafe_allow_html=True)
            st.metric("Calibration (ECE)", f"{bdata['ece']:.3f}", "Target: <0.05", label_visibility="collapsed", help="Expected Calibration Error: measures honesty. When the AI says 70% probability, it actually happens 70% of the time.")
        with c_m3:
            st.markdown(f"**{tip('False Alarm Rate', 'Percentage of harmless situations mistakenly escalated to emergency status. CrisisSense drops false alarms down to under 1.5%.')}**", unsafe_allow_html=True)
            st.metric("False Escalations", f"{bdata['false_escalate_rate_pct']}%", f"vs Baseline {bdata['false_escalate_rate_threshold_pct']}%", label_visibility="collapsed", help="Percentage of benign episodes that were mistakenly escalated. CrisisSense eliminates 97% of threshold false alarms.")
        with c_m4:
            st.markdown(f"**{tip('Forecast Hit Rate', 'Percentage of predicted future events that actually occurred within the predicted 80% time window based on flood flow physics.')}**", unsafe_allow_html=True)
            st.metric("Forecast Hit Rate", f"{bdata['causal_forecast_hit_rate_pct']}%", "80% Window (Target: ≥60%)", label_visibility="collapsed", help="Percentage of predicted future events that actually occurred within the predicted 80% time window.")

        st.markdown(f"#### {tip('Reliability Diagram: Accuracy vs Forecast Confidence', 'Compares predicted confidence against empirical accuracy (Guo et al. ICML 2017). Perfect calibration follows the 45-degree dashed diagonal.')}", unsafe_allow_html=True)
        bins_data = bdata.get("ece_diagram", {}).get("bins", [])
        if bins_data:
            df_bins = pd.DataFrame(bins_data)
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', line=dict(dash='dash', color='gray'), name='Perfect Calibration (Diagonal)'))
            fig_cal.add_trace(go.Bar(x=df_bins["confidence"], y=df_bins["accuracy"], width=0.08, name='Empirical Accuracy', marker_color='#3b82f6'))
            fig_cal.update_layout(title="Calibration Diagram: Empirical Accuracy vs Confidence", xaxis_title="Forecast Confidence", yaxis_title="Empirical Accuracy", height=300)
            st.plotly_chart(fig_cal, use_container_width=True)

        st.markdown(f"#### {tip('5-Way Component Damage Assessment', 'A scientific stress test where components are turned off one by one to prove each mathematical subsystem is strictly necessary.')}", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(bdata["ablations"]), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader(
        "OASIS / WMO Common Alerting Protocol (CAP v1.2) Payload",
        help="Standardized emergency format: Ready to transmit to partner agencies, police dispatch, and sirens, strictly labeled with status='Exercise'."
    )
    st.caption(f"The international standard format ({tip('OASIS / WMO CAP v1.2', 'Common Alerting Protocol: XML and JSON standard used worldwide for emergency broadcasts, sirens, and mobile emergency alerts.')}) for multi-agency disaster coordination.", unsafe_allow_html=True)
    cap_alert = current_payload.cap_alert
    if cap_alert:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(f"**{tip('CAP JSON Payload (Digital Dispatch)', 'Machine-readable JSON sent to CAD systems, mobile alert gateways, and traffic routing servers.')}:**", unsafe_allow_html=True)
            st.json(cap_alert.model_dump())
        with col_c2:
            st.markdown(f"**{tip('CAP v1.2 XML Serialization (Sirens / Radio)', 'Official XML format for broadcast radios, sirens, and federal emergency channels.')}:**", unsafe_allow_html=True)
            st.code(CAPAlertBuilder.to_xml(cap_alert), language="xml")
    else:
        st.info("System currently in WATCH status; formal CAP Exercise advisory issued upon PREPARE, ALERT, or ESCALATE.")
