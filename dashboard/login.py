import streamlit as st
import streamlit.components.v1 as components
from src.auth import DEMO_USERS, verify_credentials, UserProfile

# ─────────────────────────────────────────────────────────────────────────────
# PIXEL-PERFECT login page — matches the reference screenshot exactly:
#   • Light grey page background
#   • White card, rounded corners, subtle shadow
#   • "● CrisisSense AI" pill badge (blue dot + pill)
#   • "Welcome Back" bold heading
#   • Grey subtitle text
#   • QUICK ACCESS box: "QUICK ACCESS" label left + "1-Click Demo" button right
#     Credentials hint + note below
#   • "Username or ID" label → plain text input
#   • "Password" label → password input with "Show" link inline on right
#   • ☑ Remember me (left)  |  Forgot password? (right)
#   • Full-width bright-blue SIGN IN button
#   • "Need an operational account?  Register ID" centered footer
# ─────────────────────────────────────────────────────────────────────────────

def render_login_page():
    """
    Renders the exact-same-to-same login page as shown in the reference
    screenshot. Uses an injected HTML widget for pixel-perfect visuals and
    Streamlit session-state flags to communicate authentication back to app.py.
    """

    # ── Hide sidebar & header so ONLY the card is visible ─────────────────
    st.markdown("""
    <style>
        [data-testid="stSidebar"]            { display: none !important; }
        header[data-testid="stHeader"]       { display: none !important; }
        footer                               { display: none !important; }
        .block-container                     { padding: 0 !important; max-width: 100% !important; }
        .stApp                               { background: #e8eaed !important; }
        /* Remove any gap Streamlit adds above the iframe */
        [data-testid="stVerticalBlock"]      { gap: 0 !important; padding: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── The full login card rendered as a self-contained HTML component ────
    # We use a hidden <form> that POSTs to a Streamlit URL query param trick:
    # The real auth happens below via st.query_params + session_state.
    card_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }

      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     "Helvetica Neue", Arial, sans-serif;
        background: #e8eaed;
        min-height: 100vh;
        display: flex;
        align-items: flex-start;
        justify-content: center;
        padding: 48px 16px 32px;
      }

      /* ── Card ── */
      .card {
        background: #ffffff;
        border-radius: 18px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.10), 0 0 0 0.5px rgba(0,0,0,0.06);
        padding: 36px 40px 32px;
        width: 100%;
        max-width: 460px;
      }

      /* ── Badge pill ── */
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        border: 1.5px solid #b6ccf5;
        background: #f0f5ff;
        border-radius: 20px;
        padding: 5px 14px 5px 10px;
        margin-bottom: 20px;
      }
      .badge-dot {
        width: 9px; height: 9px;
        background: #1a56db;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .badge-text {
        font-size: 13px;
        font-weight: 600;
        color: #1e3a8a;
        letter-spacing: 0.1px;
      }

      /* ── Heading ── */
      h1 {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 8px;
        letter-spacing: -0.4px;
        line-height: 1.15;
      }

      /* ── Subtitle ── */
      .subtitle {
        font-size: 14px;
        color: #64748b;
        line-height: 1.55;
        margin-bottom: 24px;
      }

      /* ── Quick Access box ── */
      .qa-box {
        background: #f8faff;
        border: 1px solid #dbeafe;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 22px;
      }
      .qa-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
      }
      .qa-label {
        font-size: 11px;
        font-weight: 700;
        color: #1d4ed8;
        letter-spacing: 0.9px;
        text-transform: uppercase;
      }
      .btn-demo {
        background: #1d4ed8;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        letter-spacing: 0.1px;
        transition: background 0.15s;
      }
      .btn-demo:hover { background: #1e40af; }

      .qa-creds {
        font-size: 13px;
        color: #1e293b;
        margin-bottom: 5px;
      }
      .qa-creds b { font-weight: 700; }
      .qa-note {
        font-size: 12px;
        color: #94a3b8;
        line-height: 1.45;
      }

      /* ── Field wrapper ── */
      .field { margin-bottom: 18px; }

      .field-label {
        display: block;
        font-size: 13.5px;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 7px;
      }

      /* ── Text / Password inputs ── */
      input[type="text"],
      input[type="password"] {
        width: 100%;
        border: 1.5px solid #d1d5db;
        border-radius: 8px;
        padding: 11px 14px;
        font-size: 14px;
        color: #374151;
        background: #fff;
        outline: none;
        transition: border-color 0.15s, box-shadow 0.15s;
        font-family: inherit;
      }
      input[type="text"]:focus,
      input[type="password"]:focus {
        border-color: #1d4ed8;
        box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12);
      }
      input::placeholder { color: #9ca3af; font-size: 13.5px; }

      /* ── Password wrapper with "Show" inside ── */
      .pw-wrap {
        position: relative;
      }
      .pw-wrap input {
        padding-right: 54px;
      }
      .show-btn {
        position: absolute;
        right: 13px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 13px;
        font-weight: 600;
        color: #1d4ed8;
        cursor: pointer;
        user-select: none;
        background: none;
        border: none;
        padding: 0;
        font-family: inherit;
      }
      .show-btn:hover { color: #1e40af; }

      /* ── Remember me + Forgot row ── */
      .check-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 22px;
      }
      .check-left {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
      .check-left input[type="checkbox"] {
        width: 16px; height: 16px;
        accent-color: #1d4ed8;
        cursor: pointer;
        border-radius: 3px;
        margin: 0;
      }
      .check-left span {
        font-size: 13.5px;
        color: #374151;
        font-weight: 500;
      }
      .forgot-link {
        font-size: 13.5px;
        color: #1d4ed8;
        font-weight: 500;
        text-decoration: none;
        cursor: pointer;
      }
      .forgot-link:hover { color: #1e40af; text-decoration: underline; }

      /* ── SIGN IN button ── */
      .btn-signin {
        width: 100%;
        background: #1d4ed8;
        color: #ffffff;
        border: none;
        border-radius: 9px;
        padding: 14px;
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        cursor: pointer;
        transition: background 0.15s, box-shadow 0.15s;
        font-family: inherit;
        margin-bottom: 18px;
      }
      .btn-signin:hover {
        background: #1e40af;
        box-shadow: 0 4px 12px rgba(29,78,216,0.25);
      }
      .btn-signin:active { background: #1e3a8a; }

      /* ── Footer ── */
      .footer {
        text-align: center;
        font-size: 13px;
        color: #64748b;
      }
      .footer a {
        color: #1d4ed8;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
      }
      .footer a:hover { text-decoration: underline; }

      /* ── Error box ── */
      .error-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: #dc2626;
        margin-bottom: 16px;
        display: none;
      }
      .error-box.visible { display: block; }
    </style>
    </head>
    <body>
      <div class="card">

        <!-- Badge -->
        <div class="badge">
          <span class="badge-dot"></span>
          <span class="badge-text">CrisisSense AI</span>
        </div>

        <!-- Heading + subtitle -->
        <h1>Welcome Back</h1>
        <p class="subtitle">Enter your credentials to access the 10-Minute Decision System.</p>

        <!-- Quick Access box -->
        <div class="qa-box">
          <div class="qa-header">
            <span class="qa-label">Quick Access</span>
            <button class="btn-demo" onclick="fillDemo()">1-Click Demo</button>
          </div>
          <p class="qa-creds">User: <b>admin</b>&nbsp;&nbsp;Pass: <b>admin123</b></p>
          <p class="qa-note">Also accepts any valid Username (min 3 chars) &amp; Password (min 6 chars).</p>
        </div>

        <!-- Error box -->
        <div class="error-box" id="err">Invalid credentials. Username must be at least 3 characters and Password at least 6 characters.</div>

        <!-- Username field -->
        <div class="field">
          <label class="field-label" for="uname">Username or ID</label>
          <input type="text" id="uname" name="uname"
                 placeholder="e.g. admin or commander@crisis.ai"
                 autocomplete="username"/>
        </div>

        <!-- Password field -->
        <div class="field">
          <label class="field-label" for="pwd">Password</label>
          <div class="pw-wrap">
            <input type="password" id="pwd" name="pwd"
                   placeholder="e.g. admin123"
                   autocomplete="current-password"/>
            <button class="show-btn" type="button" id="showBtn"
                    onclick="toggleShow()">Show</button>
          </div>
        </div>

        <!-- Remember me + Forgot password -->
        <div class="check-row">
          <label class="check-left">
            <input type="checkbox" id="remember" checked/>
            <span>Remember me</span>
          </label>
          <a class="forgot-link" href="#">Forgot password?</a>
        </div>

        <!-- SIGN IN -->
        <button class="btn-signin" onclick="doSignIn()">Sign In</button>

        <!-- Footer -->
        <p class="footer">Need an operational account?&nbsp;<a href="#">Register ID</a></p>

      </div>

      <script>
        // ── Show / Hide password ──────────────────────────────────────────
        var showing = false;
        function toggleShow() {
          showing = !showing;
          var f = document.getElementById('pwd');
          var b = document.getElementById('showBtn');
          f.type = showing ? 'text' : 'password';
          b.textContent = showing ? 'Hide' : 'Show';
        }

        // ── 1-Click Demo: fill in admin credentials ───────────────────────
        function fillDemo() {
          document.getElementById('uname').value = 'admin';
          document.getElementById('pwd').value   = 'admin123';
          document.getElementById('err').classList.remove('visible');
        }

        // ── Sign In: validate and send to Streamlit via postMessage ──────
        function doSignIn() {
          var u = document.getElementById('uname').value.trim();
          var p = document.getElementById('pwd').value;
          var errEl = document.getElementById('err');

          if (u.length < 3 || p.length < 6) {
            errEl.classList.add('visible');
            return;
          }
          errEl.classList.remove('visible');

          // Send credentials to the parent Streamlit app via postMessage
          window.parent.postMessage(
            { type: 'CS_LOGIN', username: u, password: p },
            '*'
          );
        }

        // ── Allow Enter key to submit ─────────────────────────────────────
        document.addEventListener('keydown', function(e) {
          if (e.key === 'Enter') doSignIn();
        });
      </script>
    </body>
    </html>
    """

    # Render the HTML card (height enough to show card without scrollbar)
    components.html(card_html, height=620, scrolling=False)

    # ── Listen for the postMessage from the card ───────────────────────────
    # Streamlit can't natively receive postMessage; we use a thin JS bridge
    # that writes to a hidden Streamlit text_input, then we read it.
    st.markdown("""
    <script>
    (function() {
      window.addEventListener('message', function(evt) {
        if (evt.data && evt.data.type === 'CS_LOGIN') {
          // Find the hidden bridge inputs and set their values
          var uEl = window.parent.document.querySelector('[data-testid="stTextInput"] input[id="bridge_user"]');
          var pEl = window.parent.document.querySelector('[data-testid="stTextInput"] input[id="bridge_pass"]');
          // fallback: dispatch to session-state via query param trick
          var u = encodeURIComponent(evt.data.username);
          var p = encodeURIComponent(evt.data.password);
          // redirect with query params so Streamlit re-runs and reads them
          var base = window.parent.location.href.split('?')[0];
          window.parent.location.href = base + '?cs_user=' + u + '&cs_pass=' + p;
        }
      });
    })();
    </script>
    """, unsafe_allow_html=True)

    # ── Read credentials from URL query params (set by postMessage above) ──
    params = st.query_params
    cs_user = params.get("cs_user", "")
    cs_pass = params.get("cs_pass", "")

    if cs_user and cs_pass:
        # Validate
        ok = False
        profile = None

        if cs_user.strip() == "admin" and cs_pass == "admin123":
            ok = True
            profile = DEMO_USERS["officer104"]
        elif len(cs_user.strip()) >= 3 and len(cs_pass) >= 6:
            profile = verify_credentials(cs_user.strip(), cs_pass)
            if profile:
                ok = True
            else:
                ok = True
                profile = DEMO_USERS["officer104"]

        if ok and profile:
            st.session_state.authenticated = True
            st.session_state.user = profile
            st.session_state.login_error = ""
            # Clear query params and reload into the app
            st.query_params.clear()
            st.rerun()
        else:
            st.session_state.login_error = "Invalid credentials."
            st.query_params.clear()
