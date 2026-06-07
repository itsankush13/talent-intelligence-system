import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import tempfile

from app.core.feature_gate import can_access, get_upgrade_message
from app.core.auth import (
    send_phone_otp, send_email_otp, verify_otp,
    create_session, validate_session,
    get_tenant_by_identifier, log_action,
    verify_password_login,
)

REC_ICON = {"STRONG HIRE":"🟢","HIRE":"🔵","MAYBE":"🟡","NO HIRE":"🔴"}

def verdict_badge(rec):
    if rec in ["STRONG HIRE","HIRE"]:
        return '<span style="background:#052e16;color:#4ade80;border:1px solid #166534;padding:4px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;">✅ SUITABLE FOR HIRING</span>'
    elif rec == "MAYBE":
        return '<span style="background:#451a03;color:#fb923c;border:1px solid #9a3412;padding:4px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;">🟡 UNDER CONSIDERATION</span>'
    else:
        return '<span style="background:#450a0a;color:#f87171;border:1px solid #991b1b;padding:4px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;">❌ NOT SUITABLE FOR HIRING</span>'

def feature_locked(feature):
    plan = st.session_state.get("tenant", {}).get("plan", "trial")
    if not can_access(plan, feature):
        st.markdown(f"""
        <div style="background:#0a0f1e;border:1px solid #1e3a5f;border-radius:14px;
                    padding:32px;text-align:center;margin:16px 0;">
            <div style="font-size:2.5rem;margin-bottom:12px;">🔒</div>
            <div style="color:#60a5fa;font-weight:700;font-size:1.05rem;margin-bottom:8px;">Feature Locked</div>
            <div style="color:#64748b;font-size:0.85rem;line-height:1.7;">{get_upgrade_message(feature)}</div>
            <div style="margin-top:18px;color:#2563eb;font-size:0.78rem;font-weight:600;">Contact TechXdigisolutions to unlock</div>
        </div>
        """, unsafe_allow_html=True)
        return True
    return False

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;}
.stApp{background:#060a12!important;}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;}
.block-container{padding:2rem 2.5rem!important;max-width:1400px!important;margin:0 auto!important;}
[data-testid="stSidebar"]{background:#080d18!important;border-right:1px solid #0f1f38!important;}
[data-testid="stSidebar"]>div{padding-top:1.5rem!important;}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stTextArea"] textarea{background:#0b1221!important;border:1px solid #1e3a5f!important;border-radius:10px!important;color:#e2e8f0!important;font-family:'DM Sans',sans-serif!important;}
div[data-testid="stTextInput"] input:focus,div[data-testid="stTextArea"] textarea:focus{border-color:#2563eb!important;box-shadow:0 0 0 3px rgba(37,99,235,0.15)!important;}
div[data-testid="stButton"]>button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8,#2563eb)!important;color:white!important;border:none!important;border-radius:10px!important;font-weight:600!important;font-family:'DM Sans',sans-serif!important;box-shadow:0 4px 16px rgba(37,99,235,0.3)!important;transition:all 0.2s!important;}
div[data-testid="stButton"]>button[kind="primary"]:hover{transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(37,99,235,0.45)!important;}
div[data-testid="stButton"]>button[kind="secondary"]{background:#0f1f38!important;color:#93c5fd!important;border:1px solid #1e3a5f!important;border-radius:10px!important;font-family:'DM Sans',sans-serif!important;}
div[data-testid="stExpander"]{background:#080d18!important;border:1px solid #0f1f38!important;border-radius:12px!important;margin-bottom:8px!important;}
div[data-testid="stExpander"] summary{color:#cbd5e1!important;font-weight:500!important;}
div[data-baseweb="tab-list"]{background:#080d18!important;border-bottom:1px solid #0f1f38!important;}
div[data-baseweb="tab"]{color:#475569!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
div[aria-selected="true"][data-baseweb="tab"]{color:#60a5fa!important;border-bottom:2px solid #2563eb!important;}
div[data-testid="stTabsContent"]{background:#080d18;border:1px solid #0f1f38;border-top:none;border-radius:0 0 12px 12px;padding:20px;}
div[data-testid="stMetric"]{background:#080d18!important;border:1px solid #0f1f38!important;border-radius:12px!important;padding:16px!important;}
div[data-testid="stMetricValue"]{color:#f1f5f9!important;font-weight:700!important;}
div[data-testid="stMetricLabel"]{color:#475569!important;font-size:0.75rem!important;}
div[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,#1d4ed8,#2563eb)!important;}
div[data-testid="stFileUploader"]{background:#0b1221!important;border:2px dashed #1e3a5f!important;border-radius:12px!important;}
div[data-testid="stDataFrame"]{border:1px solid #0f1f38!important;border-radius:10px!important;}
div[data-testid="stSelectbox"]>div{background:#0b1221!important;border:1px solid #1e3a5f!important;border-radius:10px!important;color:#e2e8f0!important;}
div[data-testid="stRadio"] label{color:#94a3b8!important;}
div[data-testid="stToggle"] label{color:#94a3b8!important;}
.section-lbl{display:inline-flex;align-items:center;gap:8px;font-family:'DM Mono',monospace;font-size:0.65rem;color:#2563eb;letter-spacing:3px;text-transform:uppercase;font-weight:500;margin:28px 0 12px;padding:4px 12px;background:rgba(37,99,235,0.08);border-radius:6px;border-left:2px solid #2563eb;}
hr{border-color:#0f1f38!important;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:#060a12;}
::-webkit-scrollbar-thumb{background:#0f1f38;border-radius:3px;}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_login_page():
    st.set_page_config(page_title="TechX Digital Solutions", page_icon="🔍", layout="centered")
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');
    html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;}
    .stApp{background:radial-gradient(ellipse at 20% 20%,#0d1b4b 0%,#060a12 50%),radial-gradient(ellipse at 80% 80%,#0a1a3a 0%,#060a12 60%);background-color:#060a12;min-height:100vh;}
    .block-container{padding:48px 20px!important;max-width:460px!important;margin:0 auto!important;}
    #MainMenu,footer,header{visibility:hidden!important;}
    [data-testid="stSidebar"]{display:none!important;}
    .orb-a{position:fixed;width:500px;height:500px;border-radius:50%;background:radial-gradient(circle,rgba(37,99,235,0.12) 0%,transparent 70%);top:-150px;left:-150px;pointer-events:none;z-index:0;}
    .orb-b{position:fixed;width:400px;height:400px;border-radius:50%;background:radial-gradient(circle,rgba(99,102,241,0.08) 0%,transparent 70%);bottom:-100px;right:-100px;pointer-events:none;z-index:0;}
    .watermark{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);font-size:20vw;font-weight:900;color:rgba(37,99,235,0.025);white-space:nowrap;pointer-events:none;z-index:0;font-family:'DM Sans',sans-serif;letter-spacing:-6px;user-select:none;}
    .login-card{position:relative;z-index:1;background:rgba(8,13,24,0.97);border:1px solid #1e3a5f;border-radius:24px;padding:40px 36px 36px;box-shadow:0 0 0 1px rgba(37,99,235,0.05),0 24px 64px rgba(0,0,0,0.7),0 0 80px rgba(37,99,235,0.06);}
    .brand-icon{width:64px;height:64px;border-radius:18px;background:linear-gradient(135deg,#1d4ed8,#2563eb);display:flex;align-items:center;justify-content:center;margin:0 auto 14px;box-shadow:0 8px 28px rgba(37,99,235,0.4);font-size:1.8rem;}
    .brand-name{font-size:1.45rem;font-weight:800;color:#f1f5f9;line-height:1.1;letter-spacing:-0.3px;text-align:center;}
    .brand-name span{color:#3b82f6;}
    .brand-tag{font-family:'DM Mono',monospace;font-size:0.65rem;color:#334155;letter-spacing:3px;text-transform:uppercase;margin-top:5px;font-weight:400;text-align:center;}
    .plans{background:rgba(37,99,235,0.05);border:1px solid #1e3a5f;border-radius:12px;padding:12px 14px;margin-bottom:24px;}
    .plan-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.78rem;}
    .plan-row:last-child{border-bottom:none;}
    .plan-n{color:#64748b;}
    .plan-p{color:#60a5fa;font-weight:700;font-family:'DM Mono',monospace;}
    div[data-testid="stTextInput"] input{background:#0b1221!important;border:1px solid #1e3a5f!important;border-radius:12px!important;color:#e2e8f0!important;font-size:0.95rem!important;padding:12px 16px!important;font-family:'DM Sans',sans-serif!important;}
    div[data-testid="stTextInput"] input:focus{border-color:#2563eb!important;box-shadow:0 0 0 3px rgba(37,99,235,0.15)!important;}
    div[data-testid="stTextInput"] label{color:#475569!important;font-size:0.78rem!important;}
    div[data-testid="stTextInput"]:has(input[maxlength="6"]) input{font-size:1.8rem!important;letter-spacing:14px!important;text-align:center!important;font-weight:700!important;color:#3b82f6!important;font-family:'DM Mono',monospace!important;}
    div[data-testid="stRadio"]>div{background:#0b1221;border:1px solid #1e3a5f;border-radius:10px;padding:3px;gap:3px;}
    div[data-testid="stRadio"] label{color:#64748b!important;font-size:0.85rem!important;}
    div[data-testid="stButton"]>button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8,#2563eb)!important;color:white!important;border:none!important;border-radius:12px!important;font-weight:700!important;font-size:0.95rem!important;padding:13px!important;box-shadow:0 4px 20px rgba(37,99,235,0.4)!important;font-family:'DM Sans',sans-serif!important;transition:all 0.2s!important;}
    div[data-testid="stButton"]>button[kind="primary"]:hover{transform:translateY(-2px)!important;box-shadow:0 8px 28px rgba(37,99,235,0.55)!important;}
    div[data-testid="stButton"]>button[kind="secondary"]{background:#0f1f38!important;color:#60a5fa!important;border:1px solid #1e3a5f!important;border-radius:12px!important;font-family:'DM Sans',sans-serif!important;}
    div[data-testid="stExpander"]{background:rgba(37,99,235,0.04)!important;border:1px solid #1e3a5f!important;border-radius:12px!important;}
    div[data-testid="stExpander"] summary{color:#60a5fa!important;}
    div[data-testid="stAlert"]{border-radius:10px!important;}
    </style>
    <div class="orb-a"></div><div class="orb-b"></div>
    <div class="watermark">TechX</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;margin-bottom:28px;">
        <div class="brand-icon">🔍</div>
        <div class="brand-name"><span>TechX</span> Digital Solutions</div>
        <div class="brand-tag">Talent Intelligence System</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📋 Plans & Pricing"):
        st.markdown("""
        <div class="plans">
            <div class="plan-row"><span class="plan-n">🆓 Free Trial</span><span class="plan-p">2 days · 4 resumes</span></div>
            <div class="plan-row"><span class="plan-n">💎 6 Months</span><span class="plan-p">₹16,000</span></div>
            <div class="plan-row"><span class="plan-n">🏆 12 Months</span><span class="plan-p">₹25,000</span></div>
            <div class="plan-row"><span class="plan-n">💬 Chatbot</span><span class="plan-p">₹50 / question</span></div>
            <div class="plan-row"><span class="plan-n">📄 PDF Report</span><span class="plan-p">₹75 / report</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── LOGIN METHOD TOGGLE ──────────────────────────────────────────────────
    login_method = st.radio(
        "Login Method",
        ["🔑 OTP Login", "🔒 Username & Password"],
        horizontal=True,
        label_visibility="collapsed",
        key="global_login_method"
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # PATH B — Username & Password
    # ════════════════════════════════════════════════════════════════════════
    if login_method == "🔒 Username & Password":
        username = st.text_input("Username", placeholder="your.username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Login →", type="primary", use_container_width=True):
            if not username.strip() or not password.strip():
                st.error("Please enter both username and password.")
            else:
                with st.spinner("Verifying..."):
                    tenant_row, err = verify_password_login(username, password)
                if err:
                    st.error(err)
                else:
                    token = create_session(tenant_row["tenant_id"])
                    st.session_state.session_token = token
                    st.session_state.tenant = {
                        "id":      tenant_row["tenant_id"],
                        "company": tenant_row["company_name"],
                        "hr_name": tenant_row["hr_name"],
                        "plan":    tenant_row["plan"],
                        "used":    tenant_row["resumes_used"],
                        "limit":   tenant_row["resumes_limit"],
                        "expires": tenant_row["expires_at"][:10],
                    }
                    log_action(tenant_row["tenant_id"], "LOGIN_PASSWORD", username)
                    st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # PATH A — OTP
    # ════════════════════════════════════════════════════════════════════════
    else:
        if "login_step" not in st.session_state:
            st.session_state.login_step = "identifier"

        if st.session_state.login_step == "identifier":
            method = st.radio("Contact Method", ["📱 Phone Number", "📧 Email Address"],
                              horizontal=True, label_visibility="collapsed")
            st.session_state.login_method = "phone" if "Phone" in method else "email"
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.login_method == "phone":
                identifier = st.text_input("Phone Number", placeholder="+91 98765 43210")
            else:
                identifier = st.text_input("Email Address", placeholder="hr@yourcompany.com")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Send OTP →", type="primary", use_container_width=True):
                if not identifier.strip():
                    st.error("Please enter your phone or email.")
                else:
                    tenant = get_tenant_by_identifier(identifier.strip())
                    if not tenant:
                        st.error("Account not found. Contact TechXdigisolutions.")
                    elif not tenant["is_active"]:
                        st.error("Account suspended. Contact support.")
                    else:
                        with st.spinner("Sending OTP..."):
                            if st.session_state.login_method == "phone":
                                send_phone_otp(identifier.strip())
                            else:
                                ok, err = send_email_otp(identifier.strip())
                                if not ok:
                                    st.error(f"Failed to send OTP: {err}")
                                    st.stop()
                        st.session_state.login_identifier = identifier.strip()
                        st.session_state.login_step = "otp"
                        st.rerun()

        elif st.session_state.login_step == "otp":
            identifier = st.session_state.get("login_identifier", "")
            masked = identifier[:3] + "•"*(len(identifier)-6) + identifier[-3:] if len(identifier)>6 else identifier
            st.success(f"✅ OTP sent to **{masked}**")
            st.caption("Check your terminal if email/SMS not configured. Valid 10 minutes.")
            st.markdown("<br>", unsafe_allow_html=True)
            otp_input = st.text_input("6-digit OTP", placeholder="0  0  0  0  0  0", max_chars=6)
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns([3, 2])
            if c1.button("Verify & Login →", type="primary", use_container_width=True):
                if len(otp_input.strip()) != 6:
                    st.error("Enter the 6-digit OTP.")
                else:
                    success, err = verify_otp(identifier, otp_input.strip())
                    if success:
                        tenant = get_tenant_by_identifier(identifier)
                        from datetime import datetime as dt
                        if dt.fromisoformat(tenant["expires_at"]) < dt.utcnow() or not tenant["is_active"]:
                            st.error("Subscription expired. Contact TechXdigisolutions.")
                        else:
                            token = create_session(tenant["id"])
                            st.session_state.session_token = token
                            st.session_state.tenant = {
                                "id": tenant["id"], "company": tenant["company_name"],
                                "hr_name": tenant["hr_name"], "plan": tenant["plan"],
                                "used": tenant["resumes_used"], "limit": tenant["resumes_limit"],
                                "expires": tenant["expires_at"][:10],
                            }
                            log_action(tenant["id"], "LOGIN", identifier)
                            st.session_state.login_step = "identifier"
                            st.rerun()
                    else:
                        st.error(err)
            if c2.button("Resend OTP", use_container_width=True):
                if st.session_state.login_method == "phone":
                    send_phone_otp(identifier)
                else:
                    send_email_otp(identifier)
                st.success("OTP resent!")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("← Use different contact", use_container_width=True):
                st.session_state.login_step = "identifier"
                st.rerun()

    st.markdown("""
    <div style="text-align:center;margin-top:28px;padding-top:20px;border-top:1px solid #0f1f38;">
        <span style="color:#1e3a5f;font-size:0.75rem;">Need access? </span>
        <span style="color:#2563eb;font-size:0.75rem;font-weight:600;">Contact TechXdigisolutions</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# AUTH GATE
# ─────────────────────────────────────────────────────────────────────────────
if "session_token" not in st.session_state:
    show_login_page()

tenant_session = validate_session(st.session_state.get("session_token", ""))
if not tenant_session:
    for k in ["session_token","tenant","results","jd_structured"]:
        st.session_state.pop(k, None)
    show_login_page()

st.session_state.tenant = {
    "id":      tenant_session["tenant_id"],
    "company": tenant_session["company_name"],
    "hr_name": tenant_session["hr_name"],
    "plan":    tenant_session["plan"],
    "used":    tenant_session["resumes_used"],
    "limit":   tenant_session["resumes_limit"],
    "expires": tenant_session["sub_expires"][:10],
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TechX Digital Solutions — Talent AI",
    page_icon="🔍", layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

from app.core.pipeline             import run_pipeline
from app.core.knowledge_graph      import plot_multi_jd_graph
from app.core.heatmap              import build_heatmap
from app.core.skill_gap_forecaster import compute_transferability
from app.core.report_generator     import generate_pdf_report
from app.core.email_sender         import (get_rejection_template,
    get_selection_template, ai_personalize_email, send_email)
from app.core.config import settings

try:
    from app.core.hr_chatbot           import ask_hr_chatbot
    from app.core.candidate_comparator import compare_candidates
    from app.core.interview_generator  import generate_interview_questions
    from app.core.summary_generator    import generate_hiring_summary
    HR_TOOLS_OK = True
except Exception as _e:
    HR_TOOLS_OK = False

for _k,_v in [("extra_jds",[]),("li_texts",[{"name":"","text":""}]),
               ("override_log",[]),("chat_history",[]),
               ("results",[]),("jd_structured",{})]:
    if _k not in st.session_state: st.session_state[_k]=_v

tenant = st.session_state.tenant

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:0 4px 20px;
                border-bottom:1px solid #0f1f38;margin-bottom:20px;">
        <div style="width:34px;height:34px;background:linear-gradient(135deg,#1d4ed8,#2563eb);
                    border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:1rem;">🔍</div>
        <div>
            <div style="font-size:0.82rem;font-weight:700;color:#f1f5f9;">TechX Digital Solutions</div>
            <div style="font-size:0.62rem;color:#334155;font-family:'DM Mono',monospace;letter-spacing:1px;">TALENT AI</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**⚙️ Pipeline**")
    show_bias     = st.toggle("Bias Audit",         value=True)
    show_graph    = st.toggle("Intelligence Graph", value=True)
    show_heatmap  = st.toggle("Competency Heatmap", value=True)
    show_forecast = st.toggle("Skill Gap Forecast", value=True)
    st.divider()

    pc = {"trial":"#f59e0b","six_months":"#3b82f6","twelve_months":"#a78bfa"}.get(tenant.get("plan","trial"),"#64748b")
    used = tenant.get("used",0)
    limit = max(tenant.get("limit",1),1)
    pct = min((used/limit)*100, 100)

    st.markdown(f"""
    <div style="background:#080d18;border:1px solid #0f1f38;border-radius:12px;padding:14px;font-size:0.75rem;">
        <div style="color:#f1f5f9;font-weight:700;font-size:0.88rem;margin-bottom:8px;">🏢 {tenant.get('company','')}</div>
        <div style="color:#64748b;margin-bottom:4px;">👤 {tenant.get('hr_name','')}</div>
        <span style="background:{pc}18;color:{pc};border:1px solid {pc}44;padding:2px 10px;border-radius:20px;font-size:0.7rem;font-weight:700;">
            {tenant.get('plan','trial').replace('_',' ').upper()}
        </span>
        <div style="margin-top:10px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#475569;">Resumes</span>
                <span style="color:#94a3b8;font-family:'DM Mono',monospace;">{used}/{tenant.get('limit',0)}</span>
            </div>
            <div style="background:#0f1f38;border-radius:4px;height:4px;">
                <div style="background:{pc};height:4px;border-radius:4px;width:{pct:.0f}%;"></div>
            </div>
        </div>
        <div style="color:#334155;margin-top:8px;font-size:0.7rem;">⏰ Expires: {tenant.get('expires','')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.divider()
    st.code("LLM : Llama-3.3-70b\nEmbed: MiniLM-L6-v2\nRAG : FAISS+BM25", language="yaml")

# ── TOP BAR ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:28px;
            padding-bottom:20px;border-bottom:1px solid #0f1f38;">
    <div>
        <div style="font-size:1.6rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.5px;">
            Talent Intelligence <span style="color:#2563eb;">System</span>
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#334155;
                    letter-spacing:3px;text-transform:uppercase;margin-top:3px;">
            Multi-Agent · Hybrid RAG · Explainable AI · Bias-Aware
        </div>
    </div>
    <div style="margin-left:auto;text-align:right;">
        <div style="font-size:0.78rem;color:#475569;">👤 {tenant.get('hr_name','')}</div>
        <div style="font-size:0.72rem;color:#334155;">{tenant.get('company','')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── SECTION 01: JD ────────────────────────────────────────────────────────────
st.markdown('<div class="section-lbl">01 — Job Descriptions</div>', unsafe_allow_html=True)

with st.expander("🔵 Primary Job Description", expanded=True):
    jd_text = st.text_area("Paste JD here", height=160, key="primary_jd",
                            placeholder="e.g. AI Developer Intern — Python, LangChain, RAG, NLP, 1+ years...")

if can_access(tenant.get("plan","trial"), "multi_jd"):
    st.markdown("**➕ Additional Openings**")
    if st.button("+ Add Role", type="secondary"):
        st.session_state.extra_jds.append({"role_name":"","text":""})
    for i, jd in enumerate(st.session_state.extra_jds):
        with st.expander(f"📄 Opening #{i+1}: {jd['role_name'] or 'Unnamed'}", expanded=True):
            c1, c2 = st.columns([1,3])
            st.session_state.extra_jds[i]["role_name"] = c1.text_input("Role Title", value=jd["role_name"], key=f"rn_{i}")
            st.session_state.extra_jds[i]["text"]      = c2.text_area("JD Text", value=jd["text"], height=90, key=f"jdt_{i}")
            if st.button("🗑 Remove", key=f"rm_{i}", type="secondary"):
                st.session_state.extra_jds.pop(i); st.rerun()

st.divider()

# ── SECTION 02: CANDIDATES ────────────────────────────────────────────────────
st.markdown('<div class="section-lbl">02 — Candidates</div>', unsafe_allow_html=True)

tab_pdf, tab_json, tab_text = st.tabs(["📎 Upload PDF/DOCX","🔗 LinkedIn JSON","📋 Paste LinkedIn Text"])

with tab_pdf:
    uploaded_files = st.file_uploader("Upload PDF or DOCX resumes", type=["pdf","docx"], accept_multiple_files=True)
with tab_json:
    st.caption("👉 LinkedIn → Settings → Data Privacy → Download Profile.json")
    li_json_files = st.file_uploader("Upload Profile.json", type=["json"], accept_multiple_files=True, key="li_json")
with tab_text:
    st.caption("👉 Open LinkedIn profile → Ctrl+A → Ctrl+C → paste below")
    for i, entry in enumerate(st.session_state.li_texts):
        c1, c2 = st.columns([1,3])
        st.session_state.li_texts[i]["name"] = c1.text_input("Name", value=entry["name"], key=f"li_name_{i}")
        st.session_state.li_texts[i]["text"] = c2.text_area("LinkedIn text", value=entry["text"], height=80, key=f"li_text_{i}")
    if st.button("+ Add profile", type="secondary", key="add_li"):
        st.session_state.li_texts.append({"name":"","text":""}); st.rerun()

st.divider()

if st.button("🔍  Search for Suitable Candidates", type="primary", use_container_width=True):
    if not jd_text.strip():
        st.error("Please enter a Job Description.")
    else:
        from app.agents.resume_parser_agent import parse_linkedin_to_profile
        from app.utils.linkedin_parser import parse_linkedin_json_export, parse_linkedin_text_paste
        temp_dir = tempfile.mkdtemp()
        file_paths, linkedin_profiles = [], []
        for f in (uploaded_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p,"wb") as out: out.write(f.read())
            file_paths.append(p)
        for f in (li_json_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p,"wb") as out: out.write(f.read())
            try:
                li_data = parse_linkedin_json_export(p)
                linkedin_profiles.append(parse_linkedin_to_profile(li_data))
            except Exception as e: st.warning(f"LinkedIn JSON error: {e}")
        for entry in st.session_state.li_texts:
            if entry["text"].strip():
                try:
                    li_data = parse_linkedin_text_paste(entry["text"], entry.get("name",""))
                    linkedin_profiles.append(parse_linkedin_to_profile(li_data))
                except Exception as e: st.warning(f"LinkedIn error: {e}")
        if not file_paths and not linkedin_profiles:
            st.error("Upload at least one resume or LinkedIn profile.")
        else:
            extra_jds = [{"role_name":j["role_name"] or f"Role {i+1}","text":j["text"]}
                         for i,j in enumerate(st.session_state.extra_jds) if j["text"].strip()]
            with st.spinner("🤖 Running multi-agent pipeline..."):
                results = run_pipeline(jd_text, file_paths, extra_jds=extra_jds, linkedin_profiles=linkedin_profiles)
                st.session_state.results      = results
                st.session_state.jd_structured = results[0]["jd"] if results else {}
            st.success(f"✅ Done! {len(results)} candidates processed.")
            st.rerun()

# ── RESULTS ───────────────────────────────────────────────────────────────────
if st.session_state.results:
    results       = st.session_state.results
    jd_structured = st.session_state.jd_structured
    primary_role  = jd_structured.get("role_title","the role")

    st.divider()
    st.markdown('<div class="section-lbl">03 — Results</div>', unsafe_allow_html=True)

    m1,m2,m3,m4,m5 = st.columns(5)
    hire_count = sum(1 for r in results if r["score"].hire_recommendation in ["HIRE","STRONG HIRE"])
    avg_score  = sum(r["score"].weighted_total for r in results)/len(results)
    avg_conf   = sum(r["score"].confidence for r in results)/len(results)
    n_roles    = len(results[0].get("all_jds",[])) if results else 1
    m1.metric("Screened",       len(results))
    m2.metric("Recommended",    hire_count)
    m3.metric("Avg Score",      f"{avg_score:.1f}/10")
    m4.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
    m5.metric("Open Roles",     n_roles)

    st.markdown("#### 📊 Ranked Shortlist")
    table_rows = []
    for i,r in enumerate(results,1):
        s    = r["score"]
        best = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else "N/A"
        rec  = s.hire_recommendation
        vt   = ("✅ SUITABLE" if rec in ["STRONG HIRE","HIRE"] else "🟡 MAYBE" if rec=="MAYBE" else "❌ NOT SUITABLE")
        table_rows.append({"Rank":i,"Candidate":s.candidate_name,
                            "Hiring Match":f"{getattr(s,'hiring_match_pct',0)}%",
                            "Score":f"{s.weighted_total}/10","Confidence":f"{int(s.confidence*100)}%",
                            "Best-Fit Role":best,"Verdict":vt})
    st.dataframe(table_rows, use_container_width=True, height=min(420,80+len(results)*45))

    if show_graph or show_heatmap:
        gc1,gc2 = st.columns(2)
        if show_graph:
            with gc1:
                st.markdown("#### 🕸️ Intelligence Graph")
                st.plotly_chart(plot_multi_jd_graph(results), use_container_width=True)
        if show_heatmap:
            with gc2:
                st.markdown("#### 🌡️ Competency Heatmap")
                st.plotly_chart(build_heatmap(results), use_container_width=True)

    st.markdown("#### 🔍 Candidate Breakdown")
    for rank,r in enumerate(results,1):
        s          = r["score"]
        profile    = r.get("profile")
        jd_matches = r.get("jd_matches",[])
        best       = jd_matches[0]["role_name"] if jd_matches else "N/A"
        emoji      = REC_ICON.get(s.hire_recommendation,"⚪")
        match_pct  = getattr(s,"hiring_match_pct",0)
        mc = "#10b981" if match_pct>=70 else "#f59e0b" if match_pct>=50 else "#ef4444"

        with st.expander(f"{emoji}  #{rank}  {s.candidate_name}  —  Match: {match_pct}%  —  {s.hire_recommendation}"):
            st.markdown(verdict_badge(s.hire_recommendation)+
                        f'&nbsp;&nbsp;<span style="color:#475569;font-size:0.75rem;">Best fit: {best}</span>',
                        unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:18px;background:#080d18;border:1px solid #0f1f38;
                        border-radius:12px;padding:14px 20px;margin:12px 0;">
                <div style="font-size:2.2rem;font-weight:800;color:{mc};font-family:'DM Mono',monospace;min-width:72px;">{match_pct}%</div>
                <div>
                    <div style="font-size:0.85rem;font-weight:600;color:#f1f5f9;">Hiring Match</div>
                    <div style="font-size:0.72rem;color:#475569;margin-top:2px;">Semantic alignment · skill coverage · overall score</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_a,col_b = st.columns(2)
            with col_a:
                st.markdown("**📐 Dimension Scores**")
                for dim in s.dimensions:
                    st.progress(dim.score/10, text=f"{dim.name}: {dim.score}/10 ({int(dim.weight*100)}%)")
                    st.caption(f"↳ {dim.justification}")
            with col_b:
                st.markdown("**✅ Matched Skills**")
                if s.matched_skills:
                    st.markdown(" ".join(f'<span style="background:#0c1e38;color:#60a5fa;font-size:0.7rem;font-weight:600;padding:3px 8px;border-radius:20px;border:1px solid #1e3a5f;margin:2px;display:inline-block;">{sk}</span>' for sk in s.matched_skills), unsafe_allow_html=True)
                else: st.write("None detected")
                st.markdown("**❌ Missing Skills**")
                if s.missing_skills:
                    st.markdown(" ".join(f'<span style="background:#200a0a;color:#f87171;font-size:0.7rem;font-weight:600;padding:3px 8px;border-radius:20px;border:1px solid #7f1d1d;margin:2px;display:inline-block;">{sk}</span>' for sk in s.missing_skills), unsafe_allow_html=True)
                else: st.write("Full match!")
                st.markdown("**💡 AI Reasoning**")
                st.info(s.shortlist_reasoning)

            if jd_matches:
                st.markdown("**🎯 Fit vs All Roles**")
                for idx,match in enumerate(jd_matches):
                    prefix = "🥇" if idx==0 else "🥈" if idx==1 else "🥉" if idx==2 else "  "
                    st.progress(min(match["similarity"],1.0), text=f"{prefix} {match['role_name']}: {match['similarity']:.4f}")

            if show_forecast and s.missing_skills and profile:
                forecast = compute_transferability(profile.skills, s.missing_skills)
                f1,f2,f3 = st.columns(3)
                f1.metric("Adaptability",      forecast["adaptability"])
                f2.metric("Ramp-Up Time",      forecast["months_estimate"])
                f3.metric("3-Month Readiness", f"{forecast['readiness_score']}%")

            if show_bias and r.get("bias_audit"):
                audit = r["bias_audit"]
                risk  = audit.get("bias_risk_level","UNKNOWN")
                ri    = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🔴"}.get(risk,"⚪")
                st.markdown(f"**🛡️ Bias Audit** — {ri} {risk}")
                if audit.get("bias_detected"):
                    st.warning("⚠️ "+", ".join(audit.get("bias_types",[])))
                else:
                    st.success("No bias detected.")

            st.markdown("**🔧 HR Override**")
            ov1,ov2 = st.columns([1,3])
            new_score = ov1.number_input("New Score",0.0,10.0,s.weighted_total,0.5,key=f"ov_{rank}")
            reason    = ov2.text_input("Reason (required)",key=f"re_{rank}",placeholder="e.g. Strong cultural fit")
            if st.button("✅ Apply Override",key=f"ap_{rank}",type="secondary"):
                if not reason.strip(): st.error("Please enter a reason.")
                else:
                    idx = rank-1
                    st.session_state.results[idx]["score"].weighted_total = new_score
                    if   new_score>=7.5: new_rec="STRONG HIRE"
                    elif new_score>=6.0: new_rec="HIRE"
                    elif new_score>=4.5: new_rec="MAYBE"
                    else:                new_rec="NO HIRE"
                    st.session_state.results[idx]["score"].hire_recommendation = new_rec
                    st.session_state.results.sort(key=lambda x:x["score"].weighted_total,reverse=True)
                    if "override_log" not in st.session_state: st.session_state.override_log=[]
                    st.session_state.override_log.append({"candidate":s.candidate_name,"old_score":s.weighted_total,"new_score":new_score,"new_verdict":new_rec,"reason":reason})
                    st.success(f"✅ {s.candidate_name}: {s.weighted_total} → {new_score}/10")
                    st.rerun()

    if st.session_state.get("override_log"):
        with st.expander(f"📋 Override Audit Log ({len(st.session_state.override_log)} entries)"):
            for entry in st.session_state.override_log:
                st.markdown(f"**{entry['candidate']}** — `{entry['old_score']}` → `{entry['new_score']}/10` — **{entry['new_verdict']}** — _{entry['reason']}_")

    # ── SECTION 04: EMAILS ────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-lbl">04 — Emails</div>', unsafe_allow_html=True)

    if feature_locked("emails"):
        pass
    else:
        with st.expander("⚙️ SMTP Settings",expanded=False):
            ec1,ec2,ec3 = st.columns(3)
            smtp_host_in = ec1.text_input("SMTP Host",    value=settings.smtp_host)
            smtp_port_in = ec1.number_input("SMTP Port",  value=int(settings.smtp_port))
            sender_in    = ec2.text_input("Your Gmail",   value=settings.sender_email)
            password_in  = ec2.text_input("App Password", type="password",value=settings.sender_password)
            hr_name_in   = ec3.text_input("Your Name",    value="HR Team")
            company_in   = ec3.text_input("Company Name", value=settings.company_name)

        shortlisted = [r for r in results if r["score"].hire_recommendation in ["HIRE","STRONG HIRE"]]
        rejected    = [r for r in results if r["score"].hire_recommendation == "NO HIRE"]

        st.markdown("#### 🟢 Selection Emails")
        if not shortlisted:
            st.warning("No candidates scored HIRE or above.")
        else:
            for r in shortlisted:
                s=r["score"]
                best_role=r["jd_matches"][0]["role_name"] if r.get("jd_matches") else primary_role
                with st.expander(f"🟢 {s.candidate_name} — {s.hire_recommendation}"):
                    key_body=f"sel_body_{s.candidate_name}"
                    if key_body not in st.session_state:
                        st.session_state[key_body]=get_selection_template(s.candidate_name,best_role,company_in or settings.company_name,hr_name_in,"3 Months","Remote","[Date]","[Amount]","")
                    if st.button("✨ AI Personalize",key=f"ai_{s.candidate_name}",type="secondary"):
                        with st.spinner("Personalizing..."):
                            st.session_state[key_body]=ai_personalize_email(st.session_state[key_body],s.candidate_name,s.matched_skills,s.shortlist_reasoning)
                    edited=st.text_area("✏️ Edit",value=st.session_state[key_body],height=260,key=f"sel_edit_{s.candidate_name}")
                    st.session_state[key_body]=edited
                    to_addr=st.text_input("Candidate Email",key=f"sel_email_{s.candidate_name}",placeholder="candidate@email.com")
                    if st.button("📤 Send",key=f"send_sel_{s.candidate_name}",type="primary"):
                        if not to_addr: st.error("Enter candidate email.")
                        elif not sender_in or not password_in: st.error("Configure SMTP.")
                        else:
                            ok,msg=send_email(to_addr,f"Congratulations — {best_role}",edited,smtp_host_in,int(smtp_port_in),sender_in,password_in)
                            st.success(msg) if ok else st.error(msg)

        st.markdown("#### 🔴 Rejection Emails")
        if not rejected:
            st.success("No rejected candidates!")
        else:
            for r in rejected:
                s=r["score"]
                with st.expander(f"🔴 {s.candidate_name} — NOT SUITABLE"):
                    key_body=f"rej_body_{s.candidate_name}"
                    if key_body not in st.session_state:
                        st.session_state[key_body]=get_rejection_template(s.candidate_name,primary_role,company_in or settings.company_name,hr_name_in)
                    edited=st.text_area("✏️ Edit",value=st.session_state[key_body],height=240,key=f"rej_edit_{s.candidate_name}")
                    st.session_state[key_body]=edited
                    to_addr=st.text_input("Candidate Email",key=f"rej_email_{s.candidate_name}",placeholder="candidate@email.com")
                    if st.button("📤 Send",key=f"send_rej_{s.candidate_name}",type="primary"):
                        if not to_addr: st.error("Enter candidate email.")
                        elif not sender_in or not password_in: st.error("Configure SMTP.")
                        else:
                            ok,msg=send_email(to_addr,f"Update on your application — {primary_role}",edited,smtp_host_in,int(smtp_port_in),sender_in,password_in)
                            st.success(msg) if ok else st.error(msg)

    # ── SECTION 05: HR TOOLS ──────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-lbl">05 — HR Tools</div>', unsafe_allow_html=True)

    t1,t2,t3,t4 = st.tabs(["💬 HR Chatbot","⚖️ Compare","🎯 Interview Qs","📋 Summary"])

    with t1:
        if feature_locked("hr_chatbot"): pass
        elif not HR_TOOLS_OK: st.error("HR Tools module not loaded.")
        else:
            st.markdown("**💬 Ask anything about your candidates** *(₹50/question)*")
            for msg in st.session_state.chat_history:
                if msg["role"]=="user":
                    st.markdown(f'<div style="background:#0c1e38;border-radius:10px;padding:10px 14px;margin:6px 0;font-size:0.85rem;text-align:right;">👤 {msg["content"]}</div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:#080d18;border:1px solid #0f1f38;border-radius:10px;padding:10px 14px;margin:6px 0;font-size:0.85rem;">🧠 {msg["content"]}</div>',unsafe_allow_html=True)
            user_input=st.text_input("Ask HR Chatbot",value=st.session_state.get("chatbot_input",""),placeholder="e.g. Who is best at Python?",key="chat_input_box",label_visibility="collapsed")
            cs1,cs2=st.columns([1,5])
            if cs1.button("Send",type="primary",key="send_chat"):
                if user_input.strip():
                    with st.spinner("Thinking..."):
                        resp=ask_hr_chatbot(user_input,results,st.session_state.chat_history)
                    st.session_state.chat_history.append({"role":"user","content":user_input})
                    st.session_state.chat_history.append({"role":"assistant","content":resp})
                    st.session_state.chatbot_input=""
                    st.rerun()
            if cs2.button("Clear Chat",type="secondary",key="clear_chat"):
                st.session_state.chat_history=[]; st.rerun()

    with t2:
        if feature_locked("compare_candidates"): pass
        elif not HR_TOOLS_OK: st.error("HR Tools module not loaded.")
        else:
            names=[r["score"].candidate_name for r in results]
            c1,c2=st.columns(2)
            cand_a=c1.selectbox("Candidate A",names,key="cmp_a")
            cand_b=c2.selectbox("Candidate B",names,index=min(1,len(names)-1),key="cmp_b")
            if st.button("⚖️ Compare Now",type="primary",key="do_compare"):
                if cand_a==cand_b: st.error("Select two different candidates.")
                else:
                    ra=next(r for r in results if r["score"].candidate_name==cand_a)
                    rb=next(r for r in results if r["score"].candidate_name==cand_b)
                    ca,cb=st.columns(2)
                    for col,r2 in [(ca,ra),(cb,rb)]:
                        sc=r2["score"]
                        mc2="#10b981" if sc.weighted_total>=7 else "#f59e0b" if sc.weighted_total>=5 else "#ef4444"
                        col.markdown(f'<div style="background:#080d18;border:1px solid #0f1f38;border-radius:12px;padding:16px;text-align:center;"><div style="color:#f1f5f9;font-weight:700;">{sc.candidate_name}</div><div style="font-size:2rem;font-weight:800;color:{mc2};">{sc.weighted_total}/10</div><div style="color:#475569;font-size:0.78rem;">{sc.hire_recommendation}</div></div>',unsafe_allow_html=True)
                    st.markdown("**Dimension Comparison**")
                    for dim in ra["score"].dimensions:
                        db_score=next((d.score for d in rb["score"].dimensions if d.name==dim.name),0)
                        d1,d2,d3=st.columns([2,3,3])
                        d1.markdown(f"<div style='color:#64748b;font-size:0.78rem;padding-top:6px;'>{dim.name}</div>",unsafe_allow_html=True)
                        d2.progress(dim.score/10,text=f"{cand_a.split()[0]}: {dim.score}/10")
                        d3.progress(db_score/10, text=f"{cand_b.split()[0]}: {db_score}/10")
                    with st.spinner("AI analysis..."): st.info(compare_candidates(ra,rb))

    with t3:
        if feature_locked("interview_questions"): pass
        elif not HR_TOOLS_OK: st.error("HR Tools module not loaded.")
        else:
            sel=st.selectbox("Select Candidate",[r["score"].candidate_name for r in results],key="iq_select")
            num_q=st.slider("Number of Questions",5,15,8,key="iq_num")
            if st.button("Generate Questions",type="primary",key="gen_iq"):
                cr=next(r for r in results if r["score"].candidate_name==sel)
                with st.spinner("Generating..."):
                    try:
                        qs=generate_interview_questions(cr,jd_structured,num_q)
                        cats={"technical":("🔧 Technical","#3b82f6"),"gap_probe":("🔍 Gap Probe","#f59e0b"),"behavioural":("💼 Behavioural","#8b5cf6"),"culture_fit":("🤝 Culture Fit","#10b981"),"motivation":("🎯 Motivation","#14b8a6")}
                        for key,(label,color) in cats.items():
                            q_list=qs.get(key,[])
                            if q_list:
                                st.markdown(f"**{label}**")
                                for qi,q in enumerate(q_list,1):
                                    st.markdown(f'<div style="background:#080d18;border-left:3px solid {color};border-radius:6px;padding:10px 14px;margin:5px 0;font-size:0.85rem;color:#e2e8f0;">{qi}. {q}</div>',unsafe_allow_html=True)
                    except Exception as e: st.error(f"Error: {e}")

    with t4:
        if feature_locked("hiring_summary"): pass
        elif not HR_TOOLS_OK: st.error("HR Tools module not loaded.")
        else:
            sum_co=st.text_input("Company Name",value=settings.company_name,key="sum_company")
            if st.button("Generate Summary",type="primary",key="gen_sum"):
                with st.spinner("Generating..."):
                    summary=generate_hiring_summary(results,jd_structured,sum_co)
                    st.session_state["hiring_summary"]=summary
            if "hiring_summary" in st.session_state:
                edited_sum=st.text_area("Edit Summary",value=st.session_state["hiring_summary"],height=280,key="sum_edit")
                st.download_button("⬇️ Download Summary",edited_sum,"hiring_summary.txt",use_container_width=True)

    # ── SECTION 06: PDF ───────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-lbl">06 — Report</div>', unsafe_allow_html=True)
    if feature_locked("pdf_report"): pass
    else:
        if st.button("📄 Generate PDF Report",type="primary",use_container_width=True):
            with st.spinner("Building..."):
                path="/tmp/shortlist_report.pdf"
                generate_pdf_report(results,jd_structured,path)
                with open(path,"rb") as f:
                    st.download_button("⬇️ Download PDF",f,"shortlist_report.pdf","application/pdf",use_container_width=True)
