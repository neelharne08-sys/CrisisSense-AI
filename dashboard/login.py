import streamlit as st
from src.auth import DEMO_USERS, verify_credentials, UserProfile, UserRole


def render_login_page():
    """
    Renders the CrisisSense AI login portal — closely matching the clean
    white-card design from the reference screenshot:
      • CrisisSense AI pill badge
      • "Welcome Back" heading
      • QUICK ACCESS info box + 1-Click Demo button
      • Username or ID field
      • Password field with Show/Hide toggle
      • Remember me checkbox + Forgot password link
      • SIGN IN button
      • Register ID footer link
    """

    # ── Global page styles (light background, white card) ─────────────────
    st.markdown("""
    <style>
        /* Hide default Streamlit chrome so the card is the hero */
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* Full-page light background matching the screenshot */
        .stApp {
            background: #f0f2f5 !important;
        }

        /* ── Card ── */
        .cs-card {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.10);
            padding: 40px 44px 36px 44px;
            max-width: 480px;
            margin: 60px auto 0 auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* ── Badge pill ── */
        .cs-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #e8f0fe;
            border: 1px solid #c5d8fc;
            color: #1a56db;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 4px 12px 4px 8px;
            border-radius: 20px;
            margin-bottom: 18px;
        }
        .cs-dot {
            width: 8px; height: 8px;
            background: #1a56db;
            border-radius: 50%;
            display: inline-block;
        }

        /* ── Heading ── */
        .cs-h1 {
            font-size: 1.85rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
        }
        .cs-sub {
            font-size: 0.9rem;
            color: #64748b;
            margin: 0 0 24px 0;
            line-height: 1.5;
        }

        /* ── Quick Access box ── */
        .cs-qa {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 22px;
        }
        .cs-qa-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .cs-qa-title {
            font-size: 0.72rem;
            font-weight: 700;
            color: #1a56db;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }
        .cs-creds {
            font-size: 0.84rem;
            color: #374151;
            margin-bottom: 4px;
        }
        .cs-creds-note {
            font-size: 0.76rem;
            color: #94a3b8;
            line-height: 1.4;
        }

        /* ── Field labels ── */
        .cs-label {
            font-size: 0.84rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 6px;
            display: block;
        }

        /* ── Footer text ── */
        .cs-footer {
            text-align: center;
            font-size: 0.82rem;
            color: #64748b;
            margin-top: 18px;
        }
        .cs-footer a {
            color: #1a56db;
            text-decoration: none;
            font-weight: 600;
        }

        /* ── Sign In button override ── */
        div[data-testid="stForm"] button[kind="primaryFormSubmit"],
        div[data-testid="stForm"] button[kind="primary"] {
            background: #1a56db !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.5px !important;
            padding: 14px !important;
            color: #ffffff !important;
        }

        /* ── Input fields ── */
        input[type="text"], input[type="password"] {
            border-radius: 8px !important;
            border: 1px solid #d1d5db !important;
            font-size: 0.9rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Outer centering wrapper ────────────────────────────────────────────
    st.markdown('<div class="cs-card">', unsafe_allow_html=True)

    # Badge
    st.markdown("""
        <div class="cs-badge">
            <span class="cs-dot"></span>CrisisSense AI
        </div>
    """, unsafe_allow_html=True)

    # Heading + subtitle
    st.markdown("""
        <h1 class="cs-h1">Welcome Back</h1>
        <p class="cs-sub">Enter your credentials to access the 10-Minute Decision System.</p>
    """, unsafe_allow_html=True)

    # ── Quick Access box ───────────────────────────────────────────────────
    st.markdown("""
        <div class="cs-qa">
            <div class="cs-qa-header">
                <span class="cs-qa-title">Quick Access</span>
            </div>
            <div class="cs-creds">User: <strong>admin</strong>&nbsp;&nbsp;Pass: <strong>admin123</strong></div>
            <div class="cs-creds-note">
                Also accepts any valid Username (min 3 chars) &amp; Password (min 6 chars).
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 1-Click Demo button (outside the form so it doesn't need form submit)
    col_demo, _ = st.columns([1, 2])
    with col_demo:
        if st.button("⚡ 1-Click Demo", key="one_click_demo",
                     use_container_width=True,
                     help="Instantly log in as Duty Officer Sarah Chen for a full demo."):
            st.session_state.user = DEMO_USERS["officer104"]
            st.session_state.authenticated = True
            st.session_state.login_error = ""
            st.rerun()

    st.write("")  # spacer

    # ── Main sign-in form ──────────────────────────────────────────────────
    with st.form("crisissense_login_form", clear_on_submit=False):

        st.markdown('<span class="cs-label">Username or ID</span>', unsafe_allow_html=True)
        uname = st.text_input(
            "Username or ID",
            placeholder="e.g. admin or commander@crisis.ai",
            label_visibility="collapsed"
        )

        # Password row: label on left, "Show" hint on right
        pw_col1, pw_col2 = st.columns([4, 1])
        with pw_col1:
            st.markdown('<span class="cs-label">Password</span>', unsafe_allow_html=True)
        with pw_col2:
            show_pw = st.checkbox("Show", value=False, key="show_password")

        passwd = st.text_input(
            "Password",
            placeholder="e.g. admin123",
            type="default" if show_pw else "password",
            label_visibility="collapsed"
        )

        # Remember me + Forgot password
        rem_col, fgt_col = st.columns([1, 1])
        with rem_col:
            remember = st.checkbox("Remember me", value=True)
        with fgt_col:
            st.markdown(
                '<div style="text-align:right; padding-top:6px;">'
                '<a href="#" style="font-size:0.82rem; color:#1a56db; text-decoration:none; font-weight:500;">Forgot password?</a>'
                '</div>',
                unsafe_allow_html=True
            )

        st.write("")
        submitted = st.form_submit_button(
            "SIGN IN",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            # Accept "admin"/"admin123" explicitly, plus any ≥3 char username & ≥6 char password
            ok = False
            matched_profile = None

            if uname.strip() == "admin" and passwd == "admin123":
                ok = True
                matched_profile = DEMO_USERS["officer104"]
            elif len(uname.strip()) >= 3 and len(passwd) >= 6:
                matched_profile = verify_credentials(uname.strip(), passwd)
                if matched_profile:
                    ok = True
                else:
                    # Generic allow: any ≥3 char username + ≥6 char password succeeds as Officer
                    ok = True
                    matched_profile = DEMO_USERS["officer104"]

            if ok and matched_profile:
                st.session_state.user = matched_profile
                st.session_state.authenticated = True
                st.session_state.login_error = ""
                st.rerun()
            else:
                st.session_state.login_error = "Invalid credentials. Username must be ≥ 3 characters and Password ≥ 6 characters."

    # Show error outside form
    if st.session_state.get("login_error", ""):
        st.error(st.session_state.login_error)

    # Footer
    st.markdown("""
        <div class="cs-footer">
            Need an operational account? <a href="#">Register ID</a>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close cs-card
