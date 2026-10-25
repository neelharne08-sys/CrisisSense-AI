import streamlit as st
from src.auth import (
    DEMO_USERS,
    supabase_sign_in,
    supabase_sign_up,
    supabase_reset_password,
    get_google_auth_url,
    handle_oauth_code,
    SUPABASE_URL
)

def render_login_page():
    """
    Renders the CrisisSense AI login portal — identical to the reference design
    and connected directly to Supabase Auth API with Google OAuth support.
    """
    # ── Check for incoming Google OAuth callback code ──────────────────────
    oauth_code = st.query_params.get("code")
    if oauth_code and not st.session_state.get("authenticated", False):
        with st.spinner("Authenticating with Google via Supabase..."):
            ok, profile, msg = handle_oauth_code(oauth_code)
            if ok and profile:
                st.session_state.authenticated = True
                st.session_state.user = profile
                st.session_state.login_error = ""
                st.query_params.clear()
                st.rerun()
            else:
                st.session_state.login_error = f"Google Auth Error: {msg}"
                st.query_params.clear()

    # ── View Mode: 'login', 'register', or 'forgot' ─────────────────────────
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    if "show_password" not in st.session_state:
        st.session_state.show_password = False

    # ── Global CSS: Light Page Background & Pixel-Perfect White Card ───────
    st.markdown("""
    <style>
        /* Hide sidebar & header on login screen */
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        
        .block-container {
            padding-top: 40px !important;
            padding-bottom: 40px !important;
            max-width: 520px !important;
            margin: 0 auto !important;
        }

        .stApp {
            background-color: #eef1f5 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* ── Main White Card ── */
        .cs-login-card {
            background: #ffffff;
            border-radius: 18px;
            padding: 38px 42px 34px 42px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
            border: 1px solid rgba(226, 232, 240, 0.8);
            margin-bottom: 24px;
        }

        /* ── Badge Pill ── */
        .cs-badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            background: #eef4ff;
            border: 1px solid #c7d9fc;
            color: #1e40af;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 5px 14px 5px 10px;
            border-radius: 20px;
            margin-bottom: 16px;
        }
        .cs-badge-dot {
            width: 8px;
            height: 8px;
            background-color: #1d4ed8;
            border-radius: 50%;
            display: inline-block;
        }

        /* ── Headings ── */
        .cs-title {
            font-size: 1.85rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }
        .cs-subtitle {
            font-size: 0.90rem;
            color: #64748b;
            margin: 0 0 22px 0;
            line-height: 1.45;
        }

        /* ── Quick Access Box ── */
        .cs-qa-box {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 13px 16px;
            margin-bottom: 20px;
        }
        .cs-qa-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .cs-qa-label {
            font-size: 0.72rem;
            font-weight: 700;
            color: #1d4ed8;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }
        .cs-qa-creds {
            font-size: 0.86rem;
            color: #1e293b;
            margin-bottom: 4px;
        }
        .cs-qa-note {
            font-size: 0.76rem;
            color: #94a3b8;
            line-height: 1.35;
        }

        /* ── Field Labels ── */
        .cs-field-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 6px;
            display: block;
        }

        /* ── Form Inputs ── */
        div[data-testid="stTextInput"] input {
            border-radius: 8px !important;
            border: 1.5px solid #d1d5db !important;
            padding: 11px 14px !important;
            font-size: 0.90rem !important;
            color: #1e293b !important;
            background-color: #ffffff !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #1d4ed8 !important;
            box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12) !important;
        }

        /* ── Primary Submit Button ── */
        div[data-testid="stFormSubmitButton"] button,
        div.stButton > button[kind="primary"] {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 9px !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.6px !important;
            text-transform: uppercase !important;
            padding: 12px 20px !important;
            width: 100% !important;
            box-shadow: 0 2px 8px rgba(29, 78, 216, 0.25) !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stFormSubmitButton"] button:hover,
        div.stButton > button[kind="primary"]:hover {
            background-color: #1e40af !important;
            box-shadow: 0 4px 12px rgba(29, 78, 216, 0.35) !important;
        }

        /* ── Secondary Demo / Action Button ── */
        .qa-demo-btn button {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            padding: 4px 12px !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            border: none !important;
            height: auto !important;
            min-height: 28px !important;
        }

        /* ── Google OAuth Button ── */
        .cs-google-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            background-color: #ffffff;
            color: #374151;
            border: 1.5px solid #d1d5db;
            border-radius: 9px;
            padding: 10px 16px;
            font-size: 0.88rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.15s ease;
            margin-top: 10px;
            box-sizing: border-box;
        }
        .cs-google-btn:hover {
            background-color: #f8fafc;
            border-color: #9ca3af;
            color: #111827;
        }

        /* ── Footer ── */
        .cs-footer-text {
            text-align: center;
            font-size: 0.82rem;
            color: #64748b;
            margin-top: 18px;
        }
        .cs-footer-link {
            color: #1d4ed8;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
        }
        .cs-footer-link:hover {
            text-decoration: underline;
        }

        /* ── Divider ── */
        .cs-divider {
            display: flex;
            align-items: center;
            text-align: center;
            margin: 16px 0;
            color: #94a3b8;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .cs-divider::before, .cs-divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #e2e8f0;
        }
        .cs-divider:not(:empty)::before { margin-right: 12px; }
        .cs-divider:not(:empty)::after { margin-left: 12px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Wrap Card ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cs-login-card">
        <div class="cs-badge-pill">
            <span class="cs-badge-dot"></span>
            <span>CrisisSense AI</span>
        </div>
    """, unsafe_allow_html=True)

    # ── MODE: LOGIN ───────────────────────────────────────────────────────
    if st.session_state.auth_mode == "login":
        st.markdown("""
            <h1 class="cs-title">Welcome Back</h1>
            <p class="cs-subtitle">Enter your credentials to access the 10-Minute Decision System.</p>
        """, unsafe_allow_html=True)

        # QUICK ACCESS Box with 1-Click Demo
        c_qa_info, c_qa_btn = st.columns([3, 1.2])
        with c_qa_info:
            st.markdown("""
            <div class="cs-qa-box" style="margin-bottom:0;">
                <div class="cs-qa-label">QUICK ACCESS</div>
                <div class="cs-qa-creds">User: <b>admin</b>&nbsp;&nbsp;Pass: <b>admin123</b></div>
                <div class="cs-qa-note">Also accepts any valid Supabase email or custom operator ID.</div>
            </div>
            """, unsafe_allow_html=True)
        with c_qa_btn:
            st.write("")
            st.markdown('<div class="qa-demo-btn" style="margin-top:8px;">', unsafe_allow_html=True)
            if st.button("⚡ 1-Click Demo", use_container_width=True, help="Instantly log in as Duty Officer Sarah Chen"):
                st.session_state.authenticated = True
                st.session_state.user = DEMO_USERS["officer104"]
                st.session_state.login_error = ""
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("")

        # Sign-in Form
        with st.form("login_form", clear_on_submit=False):
            st.markdown('<span class="cs-field-label">Username or ID</span>', unsafe_allow_html=True)
            uname = st.text_input(
                "Username or ID",
                placeholder="e.g. admin or commander@crisis.ai",
                value="admin" if st.session_state.get("fill_admin") else "",
                label_visibility="collapsed"
            )

            # Password row with inline Show toggle
            c_pw_lbl, c_pw_tgl = st.columns([3, 1])
            with c_pw_lbl:
                st.markdown('<span class="cs-field-label">Password</span>', unsafe_allow_html=True)
            with c_pw_tgl:
                show_pw = st.checkbox("Show", value=st.session_state.show_password, key="chk_show_pw")
                st.session_state.show_password = show_pw

            passwd = st.text_input(
                "Password",
                placeholder="e.g. admin123",
                type="default" if show_pw else "password",
                value="admin123" if st.session_state.get("fill_admin") else "",
                label_visibility="collapsed"
            )

            # Remember me & Forgot Password Row
            c_rem, c_fgt = st.columns([1, 1])
            with c_rem:
                st.checkbox("Remember me", value=True)
            with c_fgt:
                st.markdown(
                    '<div style="text-align:right; padding-top:6px;">'
                    '<span style="font-size:0.84rem; color:#1d4ed8; font-weight:500;">Secured with Supabase</span>'
                    '</div>',
                    unsafe_allow_html=True
                )

            st.write("")
            submit_btn = st.form_submit_button("SIGN IN", use_container_width=True)

            if submit_btn:
                if not uname.strip() or not passwd:
                    st.session_state.login_error = "Please enter both Username/Email and Password."
                else:
                    # Authenticate via Supabase Auth API
                    ok, profile, msg = supabase_sign_in(uname.strip(), passwd)
                    if ok and profile:
                        st.session_state.authenticated = True
                        st.session_state.user = profile
                        st.session_state.login_error = ""
                        st.rerun()
                    else:
                        st.session_state.login_error = msg

        # Error notification
        if st.session_state.get("login_error"):
            st.error(f"⚠️ {st.session_state.login_error}")

        # ── Google OAuth Sign-In (Configurable in Google Cloud Console) ────
        st.markdown('<div class="cs-divider">or continue with</div>', unsafe_allow_html=True)
        
        # Build Google OAuth URL pointing to current host
        google_oauth_url = get_google_auth_url("http://localhost:8503")
        st.markdown(f"""
        <a class="cs-google-btn" href="{google_oauth_url}" target="_self">
            <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            Sign in with Google
        </a>
        """, unsafe_allow_html=True)

        # Footer switcher
        c_f1, c_f2 = st.columns([1, 1])
        with c_f1:
            if st.button("Need an operational account? Register ID", key="btn_goto_reg"):
                st.session_state.auth_mode = "register"
                st.session_state.login_error = ""
                st.rerun()
        with c_f2:
            if st.button("Forgot password?", key="btn_goto_forgot"):
                st.session_state.auth_mode = "forgot"
                st.session_state.login_error = ""
                st.rerun()

    # ── MODE: REGISTER (SUPABASE AUTH) ────────────────────────────────────
    elif st.session_state.auth_mode == "register":
        st.markdown("""
            <h1 class="cs-title">Register ID</h1>
            <p class="cs-subtitle">Create a certified operator account on the Supabase Auth server.</p>
        """, unsafe_allow_html=True)

        with st.form("register_form"):
            reg_name = st.text_input("Full Name / Officer Title", placeholder="e.g. Officer Sarah Chen")
            reg_email = st.text_input("Official Email Address", placeholder="e.g. officer@mema.gov")
            reg_pass = st.text_input("Security Password (min 6 characters)", type="password", placeholder="••••••••••")
            
            reg_submit = st.form_submit_button("CREATE SUPABASE ACCOUNT", use_container_width=True)
            if reg_submit:
                if not reg_email or not reg_pass:
                    st.session_state.login_error = "Email and password are required."
                elif len(reg_pass) < 6:
                    st.session_state.login_error = "Password must be at least 6 characters."
                else:
                    ok, profile, msg = supabase_sign_up(reg_email, reg_pass, reg_name)
                    if ok and profile:
                        st.session_state.authenticated = True
                        st.session_state.user = profile
                        st.session_state.login_error = ""
                        st.rerun()
                    else:
                        st.session_state.login_error = msg

        if st.session_state.get("login_error"):
            st.error(f"⚠️ {st.session_state.login_error}")

        if st.button("← Back to Sign In", key="btn_back_login_from_reg"):
            st.session_state.auth_mode = "login"
            st.session_state.login_error = ""
            st.rerun()

    # ── MODE: FORGOT PASSWORD (SUPABASE AUTH) ─────────────────────────────
    elif st.session_state.auth_mode == "forgot":
        st.markdown("""
            <h1 class="cs-title">Reset Password</h1>
            <p class="cs-subtitle">Enter your registered email to receive a password reset link.</p>
        """, unsafe_allow_html=True)

        with st.form("forgot_form"):
            fgt_email = st.text_input("Registered Email Address", placeholder="e.g. officer@mema.gov")
            fgt_submit = st.form_submit_button("SEND RESET LINK", use_container_width=True)
            if fgt_submit:
                if not fgt_email:
                    st.session_state.login_error = "Please enter your email."
                else:
                    ok, msg = supabase_reset_password(fgt_email)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"⚠️ {msg}")

        if st.button("← Back to Sign In", key="btn_back_login_from_fgt"):
            st.session_state.auth_mode = "login"
            st.session_state.login_error = ""
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # Close cs-login-card
