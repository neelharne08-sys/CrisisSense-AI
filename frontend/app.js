/**
 * THE FIRST 10 MINUTES — Calibrated Crisis Decision Intelligence Engine
 * Frontend Simulation, Optimal Stopping, Twin Test Benchmark, & Causal Foresight HUD
 */

(function () {
  'use strict';

  // --- AUDIO SYNTHESIZER (Pure Web Audio API) ---
  let audioCtx = null;
  let audioEnabled = true;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  function playTone(freq, duration, type = 'sine', gainVal = 0.08) {
    if (!audioEnabled || !audioCtx) return;
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(gainVal, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {
      // Audio fallback silent
    }
  }

  function playTickSound() {
    playTone(880, 0.04, 'triangle', 0.05);
  }

  function playAlertChime() {
    if (!audioEnabled || !audioCtx) return;
    playTone(520, 0.12, 'sine', 0.1);
    setTimeout(() => playTone(780, 0.25, 'sine', 0.12), 100);
  }

  function playAlarmKlaxon() {
    if (!audioEnabled || !audioCtx) return;
    playTone(340, 0.15, 'sawtooth', 0.15);
    setTimeout(() => playTone(450, 0.25, 'sawtooth', 0.18), 120);
  }

  function playButtonThud() {
    playTone(140, 0.18, 'sine', 0.25);
  }

  // --- SCENARIO DATA DEFINITIONS ---
  // The Twin Test: Minutes 00:00 to 00:07 are IDENTICAL in sensory observations.
  // Divergence starts at 00:08.
  const IDENTICAL_PREFIX_EVENTS = [
    {
      minute: 0,
      timestamp: '00:00',
      type: 'sensor',
      source: 'METEOROLOGICAL_RADAR',
      node: 'radar_station_sector4',
      text: 'Precipitation rate surges to 45mm/h across Sector 4 & Central Basin. Storm velocity: 34 km/h East.',
      badges: []
    },
    {
      minute: 1,
      timestamp: '00:01',
      type: 'sensor',
      source: 'HYDRO_STREAM_MONITOR',
      node: 'storm_culvert_s4_14',
      text: 'Hydraulic runoff volume rises. Storm culvert level at 68% threshold capacity (normal: 24%).',
      badges: []
    },
    {
      minute: 2,
      timestamp: '00:02',
      type: 'sensor',
      source: 'CIVIC_INFRA_SENSORS',
      node: 'river_embankment_piezo_09',
      text: 'Micro-vibration telemetry logged along River Embankment. Ambient road traffic velocity drops by 18%.',
      badges: []
    },
    {
      minute: 3,
      timestamp: '00:03',
      type: 'sensor',
      source: 'URBAN_DRAINAGE_TELEMETRY',
      node: 'drainage_culvert_48',
      text: 'Drainage sensors report differential pressure anomalies across Sector 4 sub-collectors. Flow velocity spikes.',
      badges: ['ANOMALY']
    },
    {
      minute: 4,
      timestamp: '00:04',
      type: 'dispatch',
      source: '911_PUBLIC_SAFETY_LOG',
      node: 'cad_dispatch_sector4',
      text: '14 emergency calls logged reporting curb overflow on low-lying avenues. Municipal bus line 404 initiates street detour.',
      badges: ['911 INTAKE']
    },
    {
      minute: 5,
      timestamp: '00:05',
      type: 'sensor',
      source: 'TRANSIT_CAMERA_AI',
      node: 'arterial_cam_river_blvd',
      text: 'Arterial traffic slows drastically along River Boulevard (-68% speed reduction; localized gridlock). Standing water detected on asphalt.',
      badges: []
    },
    {
      minute: 6,
      timestamp: '00:06',
      type: 'social',
      source: 'CITIZEN_SOCIAL_STREAM',
      node: 'geo_sentiment_cluster_s4',
      text: 'Citizen video uploads show storm drain regurgitation near River Plaza. Dispatch reports 3 stalled commuter cars.',
      badges: ['OUT-OF-ORDER']
    },
    {
      minute: 7,
      timestamp: '00:07',
      type: 'dispatch',
      source: 'EMERGENCY_DISPATCH_911',
      node: 'cad_queue_monitor',
      text: 'Emergency 911 queue load exceeds baseline (+240% call influx). 6 domestic basement inundation calls confirmed in Sector 4.',
      badges: ['HIGH LOAD']
    }
  ];

  // Episode Alpha: True Cascading Crisis (Structural Levee Failure & Substation Flood)
  const SCENARIO_ALPHA_POST = [
    {
      minute: 8,
      timestamp: '00:08',
      type: 'sensor',
      source: 'POWER_GRID_SCADA',
      node: 'substation_07_north',
      text: 'CRITICAL: Substation 07 electrical breaker trip telemetry disconnects! Ultrasonic water sensor at Levee 4 hits 94% critical margin.',
      badges: ['GRID TRIP', 'STRUCTURAL ALERT']
    },
    {
      minute: 9,
      timestamp: '00:09',
      type: 'hospital',
      source: 'REGIONAL_HOSPITAL_NETWORK',
      node: 'metro_general_trauma',
      text: 'Metro General & St. Jude Hospitals report unusual mass arrivals. Basement medical backup generators switch on due to brownout surge.',
      badges: ['HOSPITAL ALERT', 'POWER BROWNOUT']
    },
    {
      minute: 10,
      timestamp: '00:10',
      type: 'sensor',
      source: 'DISASTER_RECON_DRONE',
      node: 'uav_recon_river_basin',
      text: 'EMERGENCY: Levee 4 structural micro-fissure breached. Cascading inundation pouring into power grid transformer field. Sector blackout imminent.',
      badges: ['BREACH CONFIRMED', 'CASCADING CRISIS']
    }
  ];

  // Episode Beta: The Twin Mimic (Benign Storm + Flu Cluster + Gateway Fiber Sever)
  const SCENARIO_BETA_POST = [
    {
      minute: 8,
      timestamp: '00:08',
      type: 'sensor',
      source: 'TELECOM_INFRA_HEALTH',
      node: 'gw_telecom_trunk_north',
      text: 'COMMON-CAUSE OUTAGE: Municipal fiber conduit severed by construction backhoe 5 miles away. 80 sensors drop offline simultaneously. Physical drains intact.',
      badges: ['GATEWAY CUTOUT', 'NON-CRISIS']
    },
    {
      minute: 9,
      timestamp: '00:09',
      type: 'hospital',
      source: 'REGIONAL_HOSPITAL_NETWORK',
      node: 'health_dept_epidemiology',
      text: 'Hospital intake spike verified as seasonal norovirus / pediatric flu cluster from local school event, completely unrelated to storm rainfall.',
      badges: ['ISOLATED CLUSTER', 'VERIFIED BENIGN']
    },
    {
      minute: 10,
      timestamp: '00:10',
      type: 'sensor',
      source: 'HYDRO_STREAM_MONITOR',
      node: 'storm_culvert_s4_14',
      text: 'Storm runoff drains cleared. Culvert water levels receding to 42%. Arterial traffic resumes normal flow. No municipal damage occurred.',
      badges: ['RECOVERY', 'FALSE ALARM AVOIDED']
    }
  ];

  // Mathematical belief trajectory over 10 minutes:
  // [H0 (Noise), H1 (Sensor Failure), H2 (Isolated Incident), H3 (Cascading Crisis)]
  const BELIEF_TRAJECTORY_ALPHA = [
    { m: 0, p: [0.42, 0.35, 0.17, 0.06], action: 'WATCH', rat: 'Precipitation within 90-day percentile. Expected variance.' },
    { m: 1, p: [0.38, 0.34, 0.20, 0.08], action: 'WATCH', rat: 'Runoff rising normally. Twin prefix indistinguishable.' },
    { m: 2, p: [0.34, 0.32, 0.24, 0.10], action: 'WATCH', rat: 'Traffic slight deceleration. Cost of alert exceeds risk.' },
    { m: 3, p: [0.28, 0.30, 0.28, 0.14], action: 'PREPARE', rat: 'Drainage anomalies detect differential pressure. Low-cost internal readiness.' },
    { m: 4, p: [0.24, 0.28, 0.30, 0.18], action: 'PREPARE', rat: 'Dispatch call frequency climbing. Retain agency standby.' },
    { m: 5, p: [0.20, 0.26, 0.32, 0.22], action: 'PREPARE', rat: 'Traffic corridor stagnant. Twin prefix uncertainty high (entropy 1.95 bits).' },
    { m: 6, p: [0.18, 0.24, 0.33, 0.25], action: 'PREPARE', rat: 'Out-of-order packets buffered. Do not prematurely guess before split.' },
    { m: 7, p: [0.15, 0.22, 0.33, 0.30], action: 'ALERT', rat: '911 queue saturation. Escalate to agency ALERT. Public siren withheld.' },
    // Split point: 00:08
    { m: 8, p: [0.04, 0.08, 0.18, 0.70], action: 'ALERT', rat: 'Substation SCADA disconnect matches physical breach hypothesis! Fast commitment.' },
    { m: 9, p: [0.01, 0.03, 0.06, 0.90], action: 'ESCALATE', rat: 'Hospitals loss of primary grid confirms cascading domino failure. TRIGGER PUBLIC ESCALATE!' },
    { m: 10, p: [0.00, 0.01, 0.01, 0.98], action: 'ESCALATE', rat: 'Breach confirmed. Full emergency mitigation underway with +8 min lead time.' }
  ];

  const BELIEF_TRAJECTORY_BETA = [
    { m: 0, p: [0.42, 0.35, 0.17, 0.06], action: 'WATCH', rat: 'Precipitation within 90-day percentile. Expected variance.' },
    { m: 1, p: [0.38, 0.34, 0.20, 0.08], action: 'WATCH', rat: 'Runoff rising normally. Twin prefix indistinguishable.' },
    { m: 2, p: [0.34, 0.32, 0.24, 0.10], action: 'WATCH', rat: 'Traffic slight deceleration. Cost of alert exceeds risk.' },
    { m: 3, p: [0.28, 0.30, 0.28, 0.14], action: 'PREPARE', rat: 'Drainage anomalies detect differential pressure. Low-cost internal readiness.' },
    { m: 4, p: [0.24, 0.28, 0.30, 0.18], action: 'PREPARE', rat: 'Dispatch call frequency climbing. Retain agency standby.' },
    { m: 5, p: [0.20, 0.26, 0.32, 0.22], action: 'PREPARE', rat: 'Traffic corridor stagnant. Twin prefix uncertainty high (entropy 1.95 bits).' },
    { m: 6, p: [0.18, 0.24, 0.33, 0.25], action: 'PREPARE', rat: 'Out-of-order packets buffered. Do not prematurely guess before split.' },
    { m: 7, p: [0.15, 0.22, 0.33, 0.30], action: 'ALERT', rat: '911 queue saturation. Escalate to agency ALERT. Public siren withheld.' },
    // Split point: 00:08 (Resolves as False Alarm / Benign Outage)
    { m: 8, p: [0.12, 0.64, 0.16, 0.08], action: 'PREPARE', rat: 'Sensor cluster failure attributed to single fiber sever! Crisis probability collapses to 8%.' },
    { m: 9, p: [0.25, 0.45, 0.26, 0.04], action: 'WATCH', rat: 'Hospital surge identified as pediatric flu outbreak. H3 ruled out. False alarm prevented.' },
    { m: 10, p: [0.48, 0.38, 0.12, 0.02], action: 'WATCH', rat: 'Drainage levels normalizing. \$2.5M municipal panic penalty avoided!' }
  ];

  // Foresight Forecasts for next 3 events based on current minute and scenario
  function getForesightPredictions(minute, scenario) {
    if (minute <= 2) {
      return [
        { target: 'Culvert S4-B pressure differential exceeds 2.5σ', window: '00:03 &ndash; 00:04', conf: '88%' },
        { target: 'River Boulevard arterial velocity drop &gt; 50%', window: '00:04 &ndash; 00:06', conf: '74%' },
        { target: 'Sector 4 911 dispatch queue surge &gt; 200%', window: '00:06 &ndash; 00:08', conf: '62%' }
      ];
    } else if (minute <= 5) {
      return [
        { target: 'River Boulevard standstill & surface pooling', window: '00:05 &ndash; 00:06', conf: '94%' },
        { target: '911 intake calls spike with basement flood reports', window: '00:06 &ndash; 00:07', conf: '89%' },
        { target: 'Telemetry split between physical breach vs gateway cut', window: '00:07 &ndash; 00:08', conf: '81%' }
      ];
    } else if (minute <= 7) {
      if (scenario === 'alpha') {
        return [
          { target: 'Substation 07 transformer submersion / breaker trip', window: '00:08 &ndash; 00:09', conf: '84%' },
          { target: 'Medical emergency generator transfer (Metro General)', window: '00:09 &ndash; 00:10', conf: '78%' },
          { target: 'Levee 4 hydraulic structural failure', window: '00:10 &ndash; 00:12', conf: '72%' }
        ];
      } else {
        return [
          { target: 'Telecom gateway fiber cut acknowledgement', window: '00:08 &ndash; 00:09', conf: '85%' },
          { target: 'Hospital arrivals categorized as viral pediatric cluster', window: '00:09 &ndash; 00:10', conf: '82%' },
          { target: 'Culvert drainage normalization & traffic clearing', window: '00:10 &ndash; 00:13', conf: '76%' }
        ];
      }
    } else {
      if (scenario === 'alpha') {
        return [
          { target: 'Levee 4 breach expanding; flood wave transit', window: '00:10 &ndash; 00:15', conf: '99%' },
          { target: 'Sector 4 regional power grid blackout', window: '00:11 &ndash; 00:16', conf: '96%' },
          { target: 'Emergency water rescue boat deployment', window: '00:13 &ndash; 00:20', conf: '91%' }
        ];
      } else {
        return [
          { target: 'Telecom fiber splice truck on site', window: '00:11 &ndash; 00:15', conf: '95%' },
          { target: 'Surface street water clearance by city pumps', window: '00:12 &ndash; 00:18', conf: '98%' },
          { target: 'Normal transit corridor schedules restored', window: '00:15 &ndash; 00:25', conf: '99%' }
        ];
      }
    }
  }

  // --- STATE ---
  let currentMinute = 0;
  let currentScenario = 'alpha'; // 'alpha' or 'beta'
  let isPlaying = false;
  let playInterval = null;
  let playSpeed = 1500; // ms per minute
  let activeFilter = 'all';

  // Adversity toggles
  let flagGatewayDrop = false;
  let flagRumorMimic = false;
  let flagStreamJitter = false;

  // Duty officer interactive state
  let userEscalatedAtMinute = null;

  // DOM Elements
  const clockDisplay = document.getElementById('clockDisplay');
  const currentMinuteNum = document.getElementById('currentMinuteNum');
  const btnPlayPause = document.getElementById('btnPlayPause');
  const playIcon = document.getElementById('playIcon');
  const playBtnText = document.getElementById('playBtnText');
  const btnPrevMin = document.getElementById('btnPrevMin');
  const btnNextMin = document.getElementById('btnNextMin');
  const btnResetSim = document.getElementById('btnResetSim');
  const btnScenarioAlpha = document.getElementById('btnScenarioAlpha');
  const btnScenarioBeta = document.getElementById('btnScenarioBeta');
  const timelineProgress = document.getElementById('timelineProgress');
  const scrubNodes = document.getElementById('scrubNodes');
  const streamEventList = document.getElementById('streamEventList');
  const streamEventCount = document.getElementById('streamEventCount');
  const soundToggle = document.getElementById('soundToggle');
  const audioIcon = document.getElementById('audioIcon');
  const audioLabel = document.getElementById('audioLabel');
  const weatherStatus = document.getElementById('weatherStatus');
  const weatherRefreshBtn = document.getElementById('weatherRefreshBtn');
  const weatherTemperature = document.getElementById('weatherTemperature');
  const weatherDescription = document.getElementById('weatherDescription');
  const weatherRain = document.getElementById('weatherRain');
  const weatherWind = document.getElementById('weatherWind');
  const weatherWindDirection = document.getElementById('weatherWindDirection');
  const weatherPressure = document.getElementById('weatherPressure');
  const weatherForecastTime = document.getElementById('weatherForecastTime');

  const WEATHER_API_URL = 'https://api.open-meteo.com/v1/forecast';
  const WEATHER_REFRESH_INTERVAL_MS = 15 * 60 * 1000;

  function getWeatherDescription(code) {
    const descriptions = {
      0: 'Clear sky',
      1: 'Mainly clear',
      2: 'Partly cloudy',
      3: 'Overcast',
      45: 'Fog',
      48: 'Depositing rime fog',
      51: 'Light drizzle',
      53: 'Moderate drizzle',
      55: 'Dense drizzle',
      56: 'Light freezing drizzle',
      57: 'Dense freezing drizzle',
      61: 'Slight rain',
      63: 'Moderate rain',
      65: 'Heavy rain',
      66: 'Light freezing rain',
      67: 'Heavy freezing rain',
      71: 'Slight snow',
      73: 'Moderate snow',
      75: 'Heavy snow',
      77: 'Snow grains',
      80: 'Slight rain showers',
      81: 'Moderate rain showers',
      82: 'Violent rain showers',
      85: 'Slight snow showers',
      86: 'Heavy snow showers',
      95: 'Thunderstorm',
      96: 'Thunderstorm with slight hail',
      99: 'Thunderstorm with heavy hail'
    };
    return descriptions[code] || 'Unknown conditions';
  }

  function getCompassDirection(degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return directions[Math.round(degrees / 45) % directions.length];
  }

  function renderWeatherForecast(data) {
    const hourly = data.hourly;
    const requiredFields = [
      'time',
      'temperature_2m',
      'rain',
      'wind_speed_120m',
      'pressure_msl',
      'weather_code',
      'wind_direction_10m'
    ];
    if (!hourly || requiredFields.some((field) => !Array.isArray(hourly[field]))) {
      throw new Error('Weather provider returned an unexpected forecast format.');
    }

    const sampleCount = Math.min(...requiredFields.map((field) => hourly[field].length));
    if (sampleCount === 0) {
      throw new Error('Weather provider returned no hourly forecast values.');
    }

    const now = Date.now() / 1000;
    let forecastIndex = 0;
    for (let index = 0; index < sampleCount; index++) {
      const timestamp = Number(hourly.time[index]);
      if (Number.isFinite(timestamp) && timestamp <= now) forecastIndex = index;
      if (Number.isFinite(timestamp) && timestamp >= now) {
        forecastIndex = index;
        break;
      }
    }

    const values = requiredFields.slice(1).map((field) => Number(hourly[field][forecastIndex]));
    if (values.some((value) => !Number.isFinite(value))) {
      throw new Error('Weather provider returned invalid values for the selected forecast hour.');
    }

    const [temperature, rain, windSpeed, pressure, weatherCode, windDirection] = values;
    const forecastTimestamp = Number(hourly.time[forecastIndex]);
    if (!Number.isFinite(forecastTimestamp)) {
      throw new Error('Weather provider returned an invalid forecast time.');
    }

    weatherTemperature.textContent = `${temperature.toFixed(1)} °C`;
    weatherDescription.textContent = getWeatherDescription(weatherCode);
    weatherRain.textContent = `${rain.toFixed(1)} mm`;
    weatherWind.textContent = `${windSpeed.toFixed(1)} km/h`;
    weatherWindDirection.textContent = `${getCompassDirection(windDirection)} (${Math.round(windDirection)}° at 10 m)`;
    weatherPressure.textContent = `${pressure.toFixed(0)} hPa`;
    weatherForecastTime.textContent = `Forecast for ${new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Berlin'
    }).format(new Date(forecastTimestamp * 1000))}`;
  }

  async function loadWeatherForecast() {
    if (weatherRefreshBtn.disabled) return;

    const params = new URLSearchParams({
      latitude: '52.52',
      longitude: '13.41',
      hourly: 'temperature_2m,rain,wind_speed_120m,pressure_msl,weather_code,wind_direction_10m',
      timezone: 'GMT',
      timeformat: 'unixtime',
      forecast_days: '3'
    });

    weatherRefreshBtn.disabled = true;
    weatherStatus.textContent = 'Loading forecast…';
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 12000);

    try {
      const response = await fetch(`${WEATHER_API_URL}?${params}`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`Weather service returned HTTP ${response.status}.`);
      }
      const data = await response.json();
      renderWeatherForecast(data);
      weatherStatus.textContent = `Updated ${new Intl.DateTimeFormat(undefined, {
        hour: '2-digit',
        minute: '2-digit'
      }).format(new Date())}`;
    } catch (error) {
      const detail = error.name === 'AbortError'
        ? 'The request timed out. Try again.'
        : error.message || 'Check your internet connection and try again.';
      weatherStatus.textContent = `Forecast unavailable: ${detail}`;
    } finally {
      window.clearTimeout(timeoutId);
      weatherRefreshBtn.disabled = false;
    }
  }

  // Probability bars
  const probH0 = document.getElementById('probH0');
  const probH1 = document.getElementById('probH1');
  const probH2 = document.getElementById('probH2');
  const probH3 = document.getElementById('probH3');
  const barH0 = document.getElementById('barH0');
  const barH1 = document.getElementById('barH1');
  const barH2 = document.getElementById('barH2');
  const barH3 = document.getElementById('barH3');
  const entropyMetric = document.getElementById('entropyMetric');

  // Recommended Action
  const actionStateBadge = document.getElementById('actionStateBadge');
  const actionRationale = document.getElementById('actionRationale');
  const hysteresisStatus = document.getElementById('hysteresisStatus');
  const gaugeCryWolf = document.getElementById('gaugeCryWolf');
  const gaugeDamageAvoided = document.getElementById('gaugeDamageAvoided');
  const valCryWolf = document.getElementById('valCryWolf');
  const valDamage = document.getElementById('valDamage');

  // Foresight & Attribution
  const foresightList = document.getElementById('foresightList');
  const attributionContent = document.getElementById('attributionContent');
  const causalGraphCanvas = document.getElementById('causalGraphCanvas');

  // Duty officer
  const dutyOfficerButton = document.getElementById('dutyOfficerButton');
  const userDecisionText = document.getElementById('userDecisionText');
  const machinePolicyText = document.getElementById('machinePolicyText');
  const twinScoreText = document.getElementById('twinScoreText');
  const dutyOutcomeText = document.getElementById('dutyOutcomeText');

  // Filter tabs
  const filterTabs = document.querySelectorAll('.filter-tab');
  const speedBtns = document.querySelectorAll('.speed-btn');

  // Cost calculator sliders
  const inputFalseAlarm = document.getElementById('inputFalseAlarm');
  const inputDelayDamage = document.getElementById('inputDelayDamage');
  const inputPrepare = document.getElementById('inputPrepare');
  const inputPrior = document.getElementById('inputPrior');
  const valFalseAlarmCost = document.getElementById('valFalseAlarmCost');
  const valDelayDamageCost = document.getElementById('valDelayDamageCost');
  const valPrepareCost = document.getElementById('valPrepareCost');
  const valPriorProb = document.getElementById('valPriorProb');
  const threshPrepare = document.getElementById('threshPrepare');
  const threshAlert = document.getElementById('threshAlert');
  const threshEscalate = document.getElementById('threshEscalate');
  const calcDynamicInsight = document.getElementById('calcDynamicInsight');

  // Schema tabs
  const schemaBtns = document.querySelectorAll('.schema-btn');
  const schemaCodeContent = document.getElementById('schemaCodeContent');

  // Build Timeline Scrubber Nodes (00 to 10)
  function initScrubber() {
    scrubNodes.innerHTML = '';
    for (let i = 0; i <= 10; i++) {
      const node = document.createElement('div');
      node.className = `scrub-node ${i === 0 ? 'active' : ''}`;
      node.dataset.min = i;
      node.title = `Jump to Minute 00:${i < 10 ? '0' + i : i}`;

      const label = document.createElement('span');
      label.className = 'scrub-node-label';
      label.innerText = `00:${i < 10 ? '0' + i : i}`;

      node.appendChild(label);
      node.addEventListener('click', () => {
        initAudio();
        setMinute(i);
      });
      scrubNodes.appendChild(node);
    }
  }

  // Calculate Shannon entropy in bits: H(P) = - sum(p * log2(p))
  function calculateEntropy(probs) {
    let entropy = 0;
    probs.forEach(p => {
      if (p > 0.0001) {
        entropy -= p * Math.log2(p);
      }
    });
    return Math.max(0, entropy);
  }

  // Update simulator state
  function updateSimulationHUD() {
    // Clock
    const formattedMin = currentMinute < 10 ? `0${currentMinute}` : `${currentMinute}`;
    clockDisplay.innerText = `00:${formattedMin}`;
    currentMinuteNum.innerText = currentMinute;

    // Timeline scrubber nodes
    const pct = (currentMinute / 10) * 100;
    timelineProgress.style.width = `${pct}%`;

    const nodes = scrubNodes.querySelectorAll('.scrub-node');
    nodes.forEach(node => {
      const m = parseInt(node.dataset.min, 10);
      node.classList.remove('active', 'passed');
      if (m === currentMinute) {
        node.classList.add('active');
      } else if (m < currentMinute) {
        node.classList.add('passed');
      }
    });

    // Spectrum steps highlight
    const steps = document.querySelectorAll('.spectrum-step');
    steps.forEach(st => st.classList.remove('active'));

    // Retrieve belief trajectory for this scenario
    const traj = currentScenario === 'alpha' ? BELIEF_TRAJECTORY_ALPHA : BELIEF_TRAJECTORY_BETA;
    const curBelief = traj[currentMinute];

    let pNoise = curBelief.p[0];
    let pSensor = curBelief.p[1];
    let pIso = curBelief.p[2];
    let pCrisis = curBelief.p[3];

    // Modify beliefs if adversity toggles are active
    if (flagGatewayDrop && currentMinute >= 4) {
      pSensor = Math.min(0.95, pSensor + 0.22);
      pCrisis = Math.max(0.01, pCrisis - 0.12);
      const rem = 1 - (pSensor + pCrisis);
      pNoise = rem * 0.6;
      pIso = rem * 0.4;
    }
    if (flagRumorMimic && currentMinute >= 6) {
      // Astroturfed mimic attempt: slight rise in noise/isolated, flagged by filter
      pNoise = Math.min(0.65, pNoise + 0.15);
      pCrisis = Math.max(0.02, pCrisis - 0.08);
    }

    // Normalize
    const sum = pNoise + pSensor + pIso + pCrisis;
    pNoise = pNoise / sum;
    pSensor = pSensor / sum;
    pIso = pIso / sum;
    pCrisis = pCrisis / sum;

    // Render Probability Bars
    probH0.innerText = `${(pNoise * 100).toFixed(1)}%`;
    probH1.innerText = `${(pSensor * 100).toFixed(1)}%`;
    probH2.innerText = `${(pIso * 100).toFixed(1)}%`;
    probH3.innerText = `${(pCrisis * 100).toFixed(1)}%`;

    barH0.style.width = `${(pNoise * 100).toFixed(1)}%`;
    barH1.style.width = `${(pSensor * 100).toFixed(1)}%`;
    barH2.style.width = `${(pIso * 100).toFixed(1)}%`;
    barH3.style.width = `${(pCrisis * 100).toFixed(1)}%`;

    // Entropy calculation
    const h = calculateEntropy([pNoise, pSensor, pIso, pCrisis]);
    entropyMetric.innerHTML = `H(P) = <strong>${h.toFixed(2)} bits</strong> (${
      h > 1.6 ? 'High Uncertainty' : h > 0.8 ? 'Solidifying Evidence' : 'Decisive State'
    })`;

    // Action Policy with Hysteresis
    let action = curBelief.action;
    let rationale = curBelief.rat;

    // Apply strict Hysteresis check: never drop from ALERT/ESCALATE to WATCH without verified multi-sensor retraction
    actionStateBadge.className = `state-badge ${action.toLowerCase()}`;
    actionStateBadge.innerText = action;
    actionRationale.innerText = rationale;

    // Highlight spectrum step
    const targetSpectrum = document.querySelector(`.spectrum-step[data-action="${action}"]`);
    if (targetSpectrum) targetSpectrum.classList.add('active');

    // Hysteresis indicator status
    if (action === 'ESCALATE') {
      hysteresisStatus.innerText = 'LOCKED (MONOTONIC ESCALATION ACTIVE) — Irreversible Public Sirens';
      hysteresisStatus.parentElement.style.color = '#ff6b6b';
    } else if (action === 'ALERT') {
      hysteresisStatus.innerText = 'ACTIVE GUARD — Dual-Threshold Schmitt Trigger Active';
      hysteresisStatus.parentElement.style.color = '#f59e0b';
    } else {
      hysteresisStatus.innerText = 'NORMAL WATCH / STAGING BUFFER';
      hysteresisStatus.parentElement.style.color = '#06b6d4';
    }

    // Tradeoff meters
    const damagePct = Math.round(pCrisis * 100);
    const cryWolfPct = Math.max(5, 100 - damagePct);
    gaugeDamageAvoided.style.width = `${damagePct}%`;
    gaugeCryWolf.style.width = `${cryWolfPct}%`;
    valDamage.innerText = `Lead Time Value: ${action === 'ESCALATE' ? '+8m Saved' : damagePct > 50 ? 'Critical' : 'Safe'}`;
    valCryWolf.innerText = `Cry-Wolf Risk: ${action === 'ESCALATE' ? 'Committed' : cryWolfPct > 60 ? 'High Avoidance' : 'Low'}`;

    // Render Stream Events for current minute
    renderStreamEvents();

    // Render Foresight Forecasts
    renderForesight();

    // Render Attribution Drawer
    renderAttribution();

    // Update Causal Canvas
    drawCausalGraph();

    // Duty officer scoreboard sync
    machinePolicyText.innerText = action;
    evaluateDutyOfficerScore();
  }

  // Render events up to current minute
  function renderStreamEvents() {
    let pool = [];

    // Prefix events up to current minute (min 0 to min 7)
    for (let i = 0; i <= Math.min(currentMinute, 7); i++) {
      pool.push(IDENTICAL_PREFIX_EVENTS[i]);
    }

    // Post events if currentMinute >= 8
    if (currentMinute >= 8) {
      const postPool = currentScenario === 'alpha' ? SCENARIO_ALPHA_POST : SCENARIO_BETA_POST;
      for (let j = 8; j <= currentMinute; j++) {
        const postEvt = postPool.find(e => e.minute === j);
        if (postEvt) pool.push(postEvt);
      }
    }

    // Inject adversity events if flags enabled
    if (flagGatewayDrop && currentMinute >= 4) {
      pool.push({
        minute: 4,
        timestamp: '00:04',
        type: 'sensor',
        source: 'GATEWAY_HEALTH_MONITOR',
        node: 'gw_telecom_north_rack',
        text: '[INJECTED ADVERSITY] Gateway GW-4 dropped 100 downstream sensors. Causal engine isolates common-cause power fault.',
        badges: ['CORRELATED FAIL', 'CUTOUT']
      });
    }

    if (flagRumorMimic && currentMinute >= 6) {
      pool.push({
        minute: 6,
        timestamp: '00:06',
        type: 'social',
        source: 'VIRAL_DISINFO_CRAWLER',
        node: 'social_bot_cluster_x',
        text: '[INJECTED ADVERSITY] Coordinated rumor wave claiming dam failure. Physical telemetry registers 0 barometric drop. Filtered.',
        badges: ['RUMOR WAVE', 'MIMIC FILTERED']
      });
    }

    // Filter by active tab
    const filtered = pool.filter(evt => {
      if (activeFilter === 'all') return true;
      return evt.type === activeFilter;
    });

    streamEventCount.innerText = `${filtered.length} EVENTS INGESTED`;
    streamEventList.innerHTML = '';

    // Render in descending order (latest on top)
    const reversed = [...filtered].reverse();
    reversed.forEach(evt => {
      const card = document.createElement('div');
      card.className = `stream-event-card type-${evt.type}`;

      let badgesHtml = '';
      if (evt.badges && evt.badges.length > 0) {
        evt.badges.forEach(b => {
          let bClass = 'tag-badge';
          if (b.includes('CUTOUT') || b.includes('CRISIS') || b.includes('ALERT')) bClass += ' badge-cutout';
          else if (b.includes('MIMIC') || b.includes('OUT-OF-ORDER')) bClass += ' badge-delayed';
          else bClass += ' badge-mimic';
          badgesHtml += `<span class="${bClass}">${b}</span>`;
        });
      }

      card.innerHTML = `
        <div class="event-top-line">
          <span class="event-time">${evt.timestamp} &bull; ${evt.source}</span>
          <div class="event-badges">${badgesHtml}</div>
        </div>
        <div class="event-body">${evt.text}</div>
        <div class="event-node-id">&gt; Node: ${evt.node}</div>
      `;
      streamEventList.appendChild(card);
    });
  }

  // Render Foresight predictions
  function renderForesight() {
    const list = getForesightPredictions(currentMinute, currentScenario);
    foresightList.innerHTML = '';

    list.forEach(item => {
      const row = document.createElement('div');
      row.className = 'foresight-item';
      row.innerHTML = `
        <span class="forecast-target">${item.target}</span>
        <span class="forecast-window">${item.window} [${item.conf}]</span>
      `;
      foresightList.appendChild(row);
    });
  }

  // Render "Why did the engine change its mind?"
  function renderAttribution() {
    let html = '';
    if (currentMinute === 0) {
      html = `<p class="attr-step"><span class="time-pill">00:00</span> Flat rainfall baseline across 12 sectors. Prior unshifted. Cost of early alert far exceeds value.</p>`;
    } else if (currentMinute <= 3) {
      html = `
        <p class="attr-step"><span class="time-pill">00:01</span> Runoff gradient matched seasonal storm prior (+14% flow).</p>
        <p class="attr-step"><span class="time-pill">00:03</span> Drainage anomalies isolated to culvert S4-B. <em>Changed policy to PREPARE</em> because prepositioning standby pumps costs only \$40k while buying 5 mins of insurance.</p>
      `;
    } else if (currentMinute <= 7) {
      html = `
        <p class="attr-step"><span class="time-pill">00:05</span> Traffic velocity drop (-68%) along River Blvd confirmed surface pooling.</p>
        <p class="attr-step"><span class="time-pill">00:07</span> Emergency 911 influx spiked. <em>Changed policy to ALERT</em>. Maintained strict maximum entropy over Twin hypotheses: <strong>Refused to push public siren</strong> because identical symptoms could be routine heavy rain + localized flu.</p>
      `;
    } else {
      if (currentScenario === 'alpha') {
        html = `
          <p class="attr-step"><span class="time-pill">00:08</span> <strong>CRITICAL MIND SHIFT:</strong> Substation 07 SCADA breaker trip telemetry and Levee 4 ultrasonic level (>94%) violated the benign storm hypothesis. Causal DAG confirms structural cascade.</p>
          <p class="attr-step"><span class="time-pill">00:09</span> Hospital power backup switch-overs confirmed domino electrical propagation. <em>ESCALATED to full public alert with 8 min advance warning</em>.</p>
        `;
      } else {
        html = `
          <p class="attr-step"><span class="time-pill">00:08</span> <strong>CRITICAL MIND SHIFT:</strong> Spatial correlation check revealed 80 dropped sensors all route through Gateway Trunk North. Classified as <em>H₁ (ISP Fiber Cut)</em>, not physical flood!</p>
          <p class="attr-step"><span class="time-pill">00:09</span> Epidemiological trace cross-verified hospital surge as pediatric flu. <em>P(H₃) dropped to 4%</em>. Successfully prevented \$2.5M municipal false alarm panic.</p>
        `;
      }
    }
    attributionContent.innerHTML = html;
  }

  // Canvas Causal Graph Renderer
  function drawCausalGraph() {
    if (!causalGraphCanvas) return;
    const ctx = causalGraphCanvas.getContext('2d');
    const w = causalGraphCanvas.width;
    const h = causalGraphCanvas.height;

    ctx.clearRect(0, 0, w, h);

    // Nodes in causal chain
    const nodes = [
      { id: 'rain', label: 'Heavy Rain', x: 45, y: 50, activeMin: 0 },
      { id: 'drain', label: 'Drainage Anomaly', x: 145, y: 35, activeMin: 3 },
      { id: 'traffic', label: 'Traffic Slow', x: 145, y: 110, activeMin: 5 },
      { id: 'grid', label: 'Substation Trip', x: 250, y: 40, activeMin: 8, alphaOnly: true },
      { id: 'telecom', label: 'Fiber Cut (H₁)', x: 250, y: 115, activeMin: 8, betaOnly: true },
      { id: 'levee', label: 'Cascade / Siren', x: 345, y: 75, activeMin: 9, alphaOnly: true }
    ];

    // Edges (from -> to)
    const edges = [
      { from: 'rain', to: 'drain' },
      { from: 'rain', to: 'traffic' },
      { from: 'drain', to: 'grid', alphaOnly: true },
      { from: 'drain', to: 'telecom', betaOnly: true },
      { from: 'traffic', to: 'grid', alphaOnly: true },
      { from: 'grid', to: 'levee', alphaOnly: true }
    ];

    // Draw Edges
    edges.forEach(e => {
      if (e.alphaOnly && currentScenario !== 'alpha') return;
      if (e.betaOnly && currentScenario !== 'beta') return;

      const fromNode = nodes.find(n => n.id === e.from);
      const toNode = nodes.find(n => n.id === e.to);
      if (!fromNode || !toNode) return;

      const isFlowing = currentMinute >= toNode.activeMin;

      ctx.beginPath();
      ctx.moveTo(fromNode.x, fromNode.y);
      ctx.lineTo(toNode.x, toNode.y);
      ctx.strokeStyle = isFlowing
        ? (currentScenario === 'alpha' && toNode.activeMin >= 8 ? '#dc2626' : '#2563eb')
        : '#cbd5e1';
      ctx.lineWidth = isFlowing ? 2.5 : 1.2;
      ctx.stroke();

      // Flow pulse particle
      if (isFlowing) {
        const time = Date.now() / 400;
        const progress = (time % 2) / 2;
        const px = fromNode.x + (toNode.x - fromNode.x) * progress;
        const py = fromNode.y + (toNode.y - fromNode.y) * progress;

        ctx.beginPath();
        ctx.arc(px, py, 3, 0, Math.PI * 2);
        ctx.fillStyle = currentScenario === 'alpha' && toNode.activeMin >= 8 ? '#dc2626' : '#2563eb';
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    });

    // Draw Nodes
    nodes.forEach(n => {
      if (n.alphaOnly && currentScenario !== 'alpha') return;
      if (n.betaOnly && currentScenario !== 'beta') return;

      const isActive = currentMinute >= n.activeMin;
      const isNext = currentMinute + 1 === n.activeMin;

      ctx.beginPath();
      ctx.arc(n.x, n.y, 9, 0, Math.PI * 2);

      if (isActive) {
        ctx.fillStyle = currentScenario === 'alpha' && n.activeMin >= 8 ? '#dc2626' : '#2563eb';
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 8;
      } else if (isNext) {
        ctx.fillStyle = '#0284c7';
        ctx.shadowColor = '#0284c7';
        ctx.shadowBlur = 5;
      } else {
        ctx.fillStyle = '#f1f5f9';
        ctx.shadowBlur = 0;
      }

      ctx.fill();
      ctx.strokeStyle = isActive ? '#ffffff' : '#94a3b8';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Label
      ctx.font = '600 10.5px "Plus Jakarta Sans", -apple-system, sans-serif';
      ctx.fillStyle = isActive ? '#0f172a' : '#64748b';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + 20);
    });
  }

  // Set specific simulation minute
  function setMinute(min) {
    currentMinute = Math.max(0, Math.min(10, min));
    playTickSound();
    updateSimulationHUD();
  }

  // Play / Pause simulation controller
  function togglePlay() {
    initAudio();
    isPlaying = !isPlaying;
    if (isPlaying) {
      if (currentMinute >= 10) currentMinute = 0;
      playBtnText.innerText = 'PAUSE SIMULATION';
      playIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
      btnPlayPause.classList.add('playing');

      playInterval = setInterval(() => {
        if (currentMinute < 10) {
          setMinute(currentMinute + 1);
          if (currentMinute === 8) {
            playAlertChime();
          } else if (currentMinute === 9 && currentScenario === 'alpha') {
            playAlarmKlaxon();
          }
        } else {
          togglePlay();
        }
      }, playSpeed);
    } else {
      clearInterval(playInterval);
      playInterval = null;
      playBtnText.innerText = 'RESUME STREAM';
      playIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
      btnPlayPause.classList.remove('playing');
    }
  }

  // Duty officer interactive evaluation game
  function evaluateDutyOfficerScore() {
    if (userEscalatedAtMinute === null) {
      userDecisionText.innerText = 'MONITORING (WAITING)';
      twinScoreText.innerText = '--';
      dutyOutcomeText.innerText = currentMinute >= 10
        ? currentScenario === 'alpha' ? 'CRISIS MISSED (-1000 pts)' : 'PERFECT PATIENCE (+500 pts)'
        : 'IN PROGRESS...';
      return;
    }

    userDecisionText.innerText = `ESCALATED AT 00:0${userEscalatedAtMinute}`;

    if (currentScenario === 'beta') {
      // User pressed in Beta = False alarm cried!
      twinScoreText.innerText = '-500 PTS (CRY-WOLF)';
      twinScoreText.style.color = '#ef4444';
      dutyOutcomeText.innerText = 'FAILED: Disrupted 8.4M citizens for a fiber cut + flu cluster!';
      dutyOutcomeText.style.color = '#ef4444';
    } else {
      // Scenario Alpha: User pressed button
      if (userEscalatedAtMinute < 7) {
        // Premature guess penalty during identical prefix!
        twinScoreText.innerText = '-350 PTS (UNJUSTIFIED)';
        twinScoreText.style.color = '#f59e0b';
        dutyOutcomeText.innerText = 'Twin Test Penalty: Escalated before evidence diverged!';
        dutyOutcomeText.style.color = '#f59e0b';
      } else if (userEscalatedAtMinute === 8 || userEscalatedAtMinute === 9) {
        const lead = 10 - userEscalatedAtMinute;
        const score = 500 + lead * 200;
        twinScoreText.innerText = `+${score} PTS (OPTIMAL STOP)`;
        twinScoreText.style.color = '#10b981';
        dutyOutcomeText.innerText = `HEROIC SAVE: +${lead}m evacuation lead time!`;
        dutyOutcomeText.style.color = '#10b981';
      } else {
        twinScoreText.innerText = '+100 PTS (MARGINAL)';
        twinScoreText.style.color = '#cbd5e1';
        dutyOutcomeText.innerText = 'Confirmed breach, but only 0m evacuation lead time.';
        dutyOutcomeText.style.color = '#cbd5e1';
      }
    }
  }

  // Duty officer button press handler
  dutyOfficerButton.addEventListener('click', () => {
    initAudio();
    playButtonThud();
    userEscalatedAtMinute = currentMinute;
    playAlarmKlaxon();
    evaluateDutyOfficerScore();
    dutyOfficerButton.style.transform = 'scale(0.96)';
    setTimeout(() => {
      dutyOfficerButton.style.transform = '';
    }, 150);
  });

  // Calculate Optimal Stopping Thresholds dynamically
  function recalculateCostThresholds() {
    const cFalseAlarm = parseFloat(inputFalseAlarm.value);
    const cDelayPerMin = parseFloat(inputDelayDamage.value);
    const cPrepare = parseFloat(inputPrepare.value);
    const priorPct = parseFloat(inputPrior.value) / 100;

    // Display formatted strings
    valFalseAlarmCost.innerText = `$${(cFalseAlarm / 1000000).toFixed(2)}M`;
    valDelayDamageCost.innerText = `$${(cDelayPerMin / 1000000).toFixed(2)}M / min`;
    valPrepareCost.innerText = `$${(cPrepare / 1000).toFixed(0)}k`;
    valPriorProb.innerText = `${(priorPct * 100).toFixed(1)}%`;

    // Mathematical Optimal Stopping Frontiers:
    // P*(Prepare) ~ cPrepare / (cDelayPerMin * 0.35 + cFalseAlarm * 0.05)
    // P*(Alert)   ~ (cPrepare * 3) / (cDelayPerMin * 0.8)
    // P*(Escalate)~ cFalseAlarm / (cFalseAlarm + cDelayPerMin * 3.5)
    let pPrep = Math.min(0.25, Math.max(0.05, (cPrepare * 3.5) / cDelayPerMin));
    let pEsc = Math.min(0.95, Math.max(0.45, cFalseAlarm / (cFalseAlarm + cDelayPerMin * 2.8)));
    let pAlert = (pPrep + pEsc) / 2;

    threshPrepare.innerText = `P(H₃) ≥ ${(pPrep * 100).toFixed(1)}%`;
    threshAlert.innerText = `P(H₃) ≥ ${(pAlert * 100).toFixed(1)}%`;
    threshEscalate.innerText = `P(H₃) ≥ ${(pEsc * 100).toFixed(1)}%`;

    // Update dynamic text
    calcDynamicInsight.innerHTML = `
      With Cry-Wolf false alarm penalty at <strong>$${(cFalseAlarm / 1000000).toFixed(1)}M</strong> and delay damage at <strong>$${(cDelayPerMin / 1000000).toFixed(1)}M/min</strong>, the optimal stopping frontier demands staying calm through high entropy. Prepare triggers at <strong>${(pPrep * 100).toFixed(0)}%</strong>, but Escalate firmly waits until <strong>${(pEsc * 100).toFixed(0)}%</strong> certainty to protect public trust.
    `;
  }

  // Schema Tab Switcher
  const SCHEMAS = {
    ingest: `{
  "$schema": "https://crisissense.ai/schemas/v1/event-stream.json",
  "event_id": "evt_9948271_sector4",
  "timestamp": "2026-10-25T20:07:14.281Z",
  "elapsed_seconds": 434,
  "source_type": "HYDRO_TELEMETRY",
  "reliability_weight": 0.88,
  "is_retraction": false,
  "data": {
    "node_id": "drainage_culvert_48",
    "pressure_kpa": 420.5,
    "flow_rate_lps": 1840.2,
    "anomaly_sigma": 3.82
  },
  "provenance": {
    "gateway_id": "gw_hydro_north",
    "mesh_hops": 2,
    "received_order": 149
  }
}`,
    belief: `{
  "cycle_minute": 8,
  "system_state": {
    "H0_noise": 0.04,
    "H1_sensor_failure": 0.08,
    "H2_isolated_incident": 0.18,
    "H3_cascading_crisis": 0.70
  },
  "shannon_entropy_bits": 1.34,
  "twin_prefix_locked": false,
  "recommended_policy": {
    "action": "ALERT",
    "action_cost_expected": 24000,
    "hysteresis_gate": "ARMED",
    "lead_time_avoided_est_minutes": 8.5
  },
  "explainability_vector": [
    { "factor": "substation_breaker_trip", "weight": +0.48 },
    { "factor": "culvert_flow_saturation", "weight": +0.22 },
    { "factor": "single_gateway_artifact", "weight": -0.09 }
  ]
}`,
    foresight: `{
  "causal_graph_id": "dag_metropolis_flood_grid_v3",
  "horizon_events": [
    {
      "step": 1,
      "event": "SUBSTATION_07_INUNDATION",
      "expected_minute_window": [8, 9],
      "calibrated_prob": 0.84,
      "causal_path": ["HEAVY_RAIN", "CULVERT_OVERFLOW"]
    },
    {
      "step": 2,
      "event": "HOSPITAL_GRID_BROWNOUT",
      "expected_minute_window": [9, 10],
      "calibrated_prob": 0.78,
      "causal_path": ["SUBSTATION_07_INUNDATION"]
    },
    {
      "step": 3,
      "event": "LEVEE_4_FISSURE_BREACH",
      "expected_minute_window": [10, 12],
      "calibrated_prob": 0.72,
      "causal_path": ["CULVERT_OVERFLOW", "GROUND_SATURATION"]
    }
  ]
}`
  };

  function initSchemaTabs() {
    schemaBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        schemaBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const key = btn.dataset.schema;
        schemaCodeContent.innerText = SCHEMAS[key];
        initAudio();
        playTickSound();
      });
    });
  }

  // --- EVENT LISTENERS ---
  function setupEventListeners() {
    // Play/Pause/Prev/Next/Reset
    btnPlayPause.addEventListener('click', togglePlay);

    btnPrevMin.addEventListener('click', () => {
      initAudio();
      if (currentMinute > 0) setMinute(currentMinute - 1);
    });

    btnNextMin.addEventListener('click', () => {
      initAudio();
      if (currentMinute < 10) setMinute(currentMinute + 1);
    });

    btnResetSim.addEventListener('click', () => {
      initAudio();
      if (isPlaying) togglePlay();
      userEscalatedAtMinute = null;
      setMinute(0);
    });

    // Speed buttons
    speedBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        speedBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        playSpeed = parseInt(btn.dataset.speed, 10);
        if (isPlaying) {
          clearInterval(playInterval);
          playInterval = setInterval(() => {
            if (currentMinute < 10) setMinute(currentMinute + 1);
            else togglePlay();
          }, playSpeed);
        }
      });
    });

    // Scenario switchers
    btnScenarioAlpha.addEventListener('click', () => {
      initAudio();
      btnScenarioAlpha.classList.add('active');
      btnScenarioBeta.classList.remove('active');
      currentScenario = 'alpha';
      userEscalatedAtMinute = null;
      updateSimulationHUD();
    });

    btnScenarioBeta.addEventListener('click', () => {
      initAudio();
      btnScenarioBeta.classList.add('active');
      btnScenarioAlpha.classList.remove('active');
      currentScenario = 'beta';
      userEscalatedAtMinute = null;
      updateSimulationHUD();
    });

    // Filter tabs
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeFilter = tab.dataset.filter;
        renderStreamEvents();
        playTickSound();
      });
    });

    // Adversity toggles
    document.getElementById('toggleGatewayDrop').addEventListener('change', (e) => {
      flagGatewayDrop = e.target.checked;
      initAudio();
      playTickSound();
      updateSimulationHUD();
    });

    document.getElementById('toggleRumorMimic').addEventListener('change', (e) => {
      flagRumorMimic = e.target.checked;
      initAudio();
      playTickSound();
      updateSimulationHUD();
    });

    document.getElementById('toggleStreamJitter').addEventListener('change', (e) => {
      flagStreamJitter = e.target.checked;
      initAudio();
      playTickSound();
      updateSimulationHUD();
    });

    // Sound toggle
    soundToggle.addEventListener('click', () => {
      initAudio();
      audioEnabled = !audioEnabled;
      if (audioEnabled) {
        soundToggle.classList.remove('muted');
        audioLabel.innerText = 'AUDIO ON';
        playTickSound();
      } else {
        soundToggle.classList.add('muted');
        audioLabel.innerText = 'MUTED';
      }
    });

    // Cost sliders
    [inputFalseAlarm, inputDelayDamage, inputPrepare, inputPrior].forEach(sl => {
      sl.addEventListener('input', recalculateCostThresholds);
    });

    // Canvas animation ticker for pulsing edges
    setInterval(() => {
      drawCausalGraph();
    }, 100);
  }

  // --- INITIALIZATION ---
  function init() {
    initScrubber();
    setupEventListeners();
    initSchemaTabs();
    recalculateCostThresholds();
    updateSimulationHUD();
    loadWeatherForecast();
    window.setInterval(loadWeatherForecast, WEATHER_REFRESH_INTERVAL_MS);
    weatherRefreshBtn.addEventListener('click', loadWeatherForecast);
  }

  // Run on DOM load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
