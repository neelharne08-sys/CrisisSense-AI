# CrisisSense AI

##### Crisis inference, optimal stopping, and causal foresight — interactive frontend demo

> A disaster rarely begins at the moment it becomes visible. This demo explores how a duty officer might distinguish ordinary noise, sensor failure, a local incident, and the first minutes of a cascading crisis.

## Overview

**CrisisSense AI** is a browser-based crisis decision simulation. It presents a minute-by-minute event stream, evolving belief estimates, recommended actions, and causal forecasts across two deliberately similar scenarios.

The application demonstrates:

- A live-style stream of simulated sensor, dispatch, hospital, and citizen/social events.
- Four competing hypotheses:
  - **H₀ — Noise or weather variation**
  - **H₁ — Sensor failure or correlated gateway outage**
  - **H₂ — Isolated local incident**
  - **H₃ — Cascading crisis**
- A graduated response policy: `WATCH` → `PREPARE` → `ALERT` → `ESCALATE`.
- The **Twin Test**: both scenarios share the same early event prefix and diverge at minute 8.
- A foresight panel, causal graph, and explanation of changes in the displayed policy.
- A responsive, styled crisis inference HUD with playback controls, event filters, probability bars, and the duty officer decision desk.
- A decision-theory playground for exploring how cost assumptions affect policy thresholds.

> **Demo limitations:** The simulator's event streams, belief trajectories, and forecasts are illustrative browser-side data; they are not connected to live city systems. Supabase Auth provides account sign-in after configuration, but it does not make the crisis data real. Do not use the demo to make operational decisions.

The simulator page also displays an hourly Open-Meteo forecast for Berlin (52.52, 13.41), refreshed every 15 minutes. This is weather context only: it is not an emergency alert and does not feed the simulated crisis probabilities. Open-Meteo is linked in the weather panel for attribution.

## Run the demo

No package installation or build step is required. The Supabase JavaScript client is loaded as an ES module from a CDN, so an internet connection is needed.

### Windows

- Configure Supabase as described below, then double-click [`start.bat`](./start.bat).
- Or run [`server.ps1`](./server.ps1) in PowerShell:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\server.ps1
  ```

  The script serves the app at `http://localhost:8085/` and opens the login screen. Use localhost rather than opening the HTML files directly; the app uses JavaScript modules and Supabase Auth.

### Configure Supabase Auth

1. Create a Supabase project and enable Email and Google authentication. For Google, configure the OAuth client credentials in the Supabase Google provider settings.
2. Confirm the Supabase **Project URL** in [`supabase-config.js`](./supabase-config.js) matches **Project Settings → API** for your project.
3. Confirm the publishable/anon key in that file belongs to the same project. A publishable key is intended for browser use; never put a service-role key in frontend code.
4. In Supabase Auth settings, add the deployed app URL (and `http://localhost:8085`) to the allowed redirect/site URLs as applicable. The Google sign-in flow returns to `index.html`, so its origin must be allowed.
5. Open the app through localhost or its deployed HTTPS URL. Choose **Create account** to register a student using email and password; Supabase Auth stores the account record. If email confirmation is enabled, confirm the address before signing in.

The **Keep me signed in** option controls whether the Supabase session uses persistent browser storage or session-only storage. Google Fonts are loaded when internet access is available; local system fonts are used as fallbacks.

Student registration currently saves only the authentication account (email and a securely managed password credential) in Supabase Auth. It does not create a separate student profile or save additional school records.

## Using the crisis inference HUD

1. Choose **Episode Alpha** or **Episode Beta**.
2. Use the timeline nodes or previous/next controls to inspect a minute, or press **Start 10-Min Stream** to play through the episode. Playback can run at `1x`, `2x`, or `4x`.
3. Review the live Berlin weather forecast separately from the simulated event feed; use **Refresh** to request an updated forecast.
4. Review the event feed and filter it by source category.
5. Compare the four hypothesis probabilities, entropy, recommended policy, and cost tradeoff.
6. Review predicted events, causal attribution, and the causal graph.
7. Press the duty officer's **ESCALATE** button to compare your decision with the scenario outcome.
8. Optionally toggle gateway cutout, rumor swarm, or out-of-order stream adversity. Use the cost-model sliders to explore alternative assumptions.

## Scenarios

- **Episode Alpha — Cascading disaster:** The shared storm-and-infrastructure warning pattern is followed by evidence consistent with a flood and electrical-grid cascade.
- **Episode Beta — Twin mimic:** The early pattern is the same, but later events point to a gateway/fiber outage and a benign hospital surge rather than a cascading disaster.

The identical prefix is intended to illustrate why early signals can be ambiguous and why later evidence should change the response.

## Project files

| File | Purpose |
| --- | --- |
| [`index.html`](./index.html) | Main dashboard, simulator, benchmark sections, and decision-theory playground |
| [`styles.css`](./styles.css) | Main application styling, including the responsive crisis inference HUD |
| [`app.js`](./app.js) | Scenario data, playback, simulated inference displays, and interactions |
| [`login.html`](./login.html) | Supabase email and Google sign-in screen |
| [`login.css`](./login.css) | Sign-in screen styles |
| [`login.js`](./login.js) | Supabase email and Google sign-in flows |
| [`register.html`](./register.html) | Student account registration page |
| [`register.js`](./register.js) | Creates student accounts through Supabase Auth |
| [`supabase-config.js`](./supabase-config.js) | Supabase project URL, publishable key, and auth client |
| [`start.bat`](./start.bat) | Starts the local server on Windows |
| [`server.ps1`](./server.ps1) | Lightweight local static web server |

## Mathematical concepts shown

### Shannon entropy

The HUD displays entropy for its four-hypothesis belief distribution:

$$H(P) = -\sum_{i=0}^{3} P(H_i)\log_2 P(H_i)$$

Higher entropy represents more uncertainty across the displayed hypotheses. The scenario belief trajectories are predefined demo data rather than probabilities learned from incoming real-world evidence.

### Optimal stopping

The demo introduces the choice between acting now and continuing to observe:

$$J^*(x) = \min \left\{C_{\text{stop}}(x),\ C_{\text{continue}}(x) + \mathbb{E}\left[J^*(x_{t+1}) \mid x_t\right]\right\}$$

The cost sliders provide an interactive way to explore false-alarm costs, delay damage, internal preparation costs, and the background prior. The displayed policy thresholds are illustrative.

### Hysteresis

The interface describes separate escalation and de-escalation thresholds as a way to reduce rapid policy reversals. This is an explanatory demo concept, not a production alerting state machine.
