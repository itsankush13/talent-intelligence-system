import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess, sys
from app.core.auth import (send_phone_otp, send_email_otp,
                            verify_otp, create_session,
                            validate_session, get_tenant_by_identifier)

def show_login_page():
    """Full login page with OTP authentication."""
    st.markdown("""
    <div style="max-width:420px;margin:80px auto;">
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;margin-bottom:32px;">
        <div style="font-size:2.5rem;">🧠</div>
        <div style="font-size:1.6rem;font-weight:800;
                    background:linear-gradient(135deg,#6366f1,#8b5cf6);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Talent Intelligence System
        </div>
        <div style="color:#64748b;font-size:0.85rem;margin-top:6px;">
            Sign in to your organisation account
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "login_step" not in st.session_state:
        st.session_state.login_step = "identifier"
    if "login_identifier" not in st.session_state:
        st.session_state.login_identifier = ""
    if "login_method" not in st.session_state:
        st.session_state.login_method = "phone"

    # ── Step 1: Enter phone or email ──────────────────────────
    if st.session_state.login_step == "identifier":
        method = st.radio("Login with", ["📱 Phone Number", "📧 Email"],
                          horizontal=True, label_visibility="collapsed")
        st.session_state.login_method = "phone" if "Phone" in method else "email"

        if st.session_state.login_method == "phone":
            identifier = st.text_input("Phone Number",
                                        placeholder="+91 98765 43210",
                                        help="Enter with country code e.g. +91")
        else:
            identifier = st.text_input("Email Address",
                                        placeholder="hr@yourcompany.com")

        if st.button("Send OTP", type="primary", use_container_width=True):
            if not identifier.strip():
                st.error("Please enter your phone number or email.")
            else:
                tenant = get_tenant_by_identifier(identifier.strip())
                if not tenant:
                    st.error("Account not found. Contact support to get access.")
                elif not tenant["is_active"]:
                    st.error("Your account is suspended. Please contact support.")
                else:
                    with st.spinner("Sending OTP..."):
                        if st.session_state.login_method == "phone":
                            send_phone_otp(identifier.strip())
                        else:
                            send_email_otp(identifier.strip())
                    st.session_state.login_identifier = identifier.strip()
                    st.session_state.login_step = "otp"
                    st.rerun()

    # ── Step 2: Enter OTP ─────────────────────────────────────
    elif st.session_state.login_step == "otp":
        identifier = st.session_state.login_identifier
        st.success(f"OTP sent to {identifier}")
        st.caption("Check your messages. OTP is valid for 10 minutes.")

        otp_input = st.text_input("Enter 6-digit OTP",
                                   placeholder="_ _ _ _ _ _",
                                   max_chars=6)

        col1, col2 = st.columns(2)
        if col1.button("Verify OTP", type="primary", use_container_width=True):
            if len(otp_input.strip()) != 6:
                st.error("Please enter the 6-digit OTP.")
            else:
                success, error_msg = verify_otp(identifier, otp_input.strip())
                if success:
                    tenant = get_tenant_by_identifier(identifier)

                    # Check subscription status
                    from datetime import datetime
                    sub_expired = (datetime.fromisoformat(tenant["expires_at"])
                                   < datetime.utcnow())

                    if sub_expired or not tenant["is_active"]:
                        st.error("Your subscription has expired or been suspended. "
                                 "Please contact support to renew.")
                    else:
                        token = create_session(tenant["id"])
                        st.session_state.session_token = token
                        st.session_state.tenant = {
                            "company":  tenant["company_name"],
                            "hr_name":  tenant["hr_name"],
                            "plan":     tenant["plan"],
                            "used":     tenant["resumes_used"],
                            "limit":    tenant["resumes_limit"],
                            "expires":  tenant["expires_at"][:10],
                        }
                        from manage_tenants import log_action
                        log_action(tenant["id"], "LOGIN",
                                   f"via {st.session_state.login_method}")
                        st.session_state.login_step = "identifier"
                        st.rerun()
                else:
                    st.error(error_msg)

        if col2.button("Resend OTP", use_container_width=True):
            with st.spinner("Resending..."):
                if st.session_state.login_method == "phone":
                    send_phone_otp(identifier)
                else:
                    send_email_otp(identifier)
            st.success("OTP resent!")

        if st.button("← Back", type="secondary"):
            st.session_state.login_step = "identifier"
            st.rerun()

    st.markdown("""
    <div style="text-align:center;margin-top:32px;color:#475569;font-size:0.78rem;">
        Don't have access? Contact us to get started.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ── Gate: show login if not authenticated ─────────────────────────────────
if "session_token" not in st.session_state:
    show_login_page()

# Validate existing session on every page load
tenant_session = validate_session(st.session_state.get("session_token", ""))
if not tenant_session:
    # Session expired or invalid — force re-login
    for key in ["session_token", "tenant", "results", "jd_struct"]:
        st.session_state.pop(key, None)
    show_login_page()

# Update tenant info
st.session_state.tenant = {
    "company": tenant_session["company_name"],
    "hr_name": tenant_session["hr_name"],
    "plan":    tenant_session["plan"],
    "used":    tenant_session["resumes_used"],
    "limit":   tenant_session["resumes_limit"],
    "expires": tenant_session["sub_expires"][:10],
}

def download_spacy_model():
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except OSError:
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)

download_spacy_model()
import os, streamlit as st

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
import streamlit as st
import tempfile, os

REC_ICON = {"STRONG HIRE":"🟢","HIRE":"🔵","MAYBE":"🟡","NO HIRE":"🔴"}
def verdict_badge(rec: str) -> str:
    if rec in ["STRONG HIRE", "HIRE"]:
        return '<span style="background:#0f2d1f;color:#22c55e;border:1px solid #166534;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;font-family:monospace;">SUITABLE FOR HIRING</span>'
    elif rec == "MAYBE":
        return '<span style="background:#2d250f;color:#f59e0b;border:1px solid #92400e;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;font-family:monospace;">UNDER CONSIDERATION</span>'
    else:
        return '<span style="background:#2d0f0f;color:#ef4444;border:1px solid #991b1b;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;font-family:monospace;">NOT SUITABLE FOR HIRING</span>'
from app.core.pipeline import run_pipeline

# Add core folder to path for HR tool modules
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), 'core'))

from hr_chatbot import ask_hr_chatbot
from candidate_comparator import compare_candidates
from interview_generator import generate_interview_questions
from summary_generator import generate_hiring_summary
try:
    from app.core.hr_chatbot import ask_hr_chatbot
    from app.core.candidate_comparator import compare_candidates
    from app.core.interview_generator import generate_interview_questions
    from app.core.summary_generator import generate_hiring_summary
    HR_TOOLS_AVAILABLE = True
except Exception as e:
    HR_TOOLS_AVAILABLE = False
    print(f"HR Tools not loaded: {e}")

from app.core.knowledge_graph import plot_multi_jd_graph
from app.core.heatmap import build_heatmap
from app.core.knowledge_graph import plot_multi_jd_graph
from app.core.skill_gap_forecaster import compute_transferability
from app.core.report_generator import generate_pdf_report
from app.core.heatmap import build_heatmap
from app.core.email_sender import (
    get_rejection_template, get_selection_template,
    ai_personalize_email, send_email,
)
from app.core.config import settings
import streamlit.components.v1 as components

st.set_page_config(page_title="Talent Intelligence System", page_icon="🔎", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.stApp { background: #07090f; }

.hero-title {
    font-family: 'Syne', sans-serif; font-size: 2.6rem; font-weight: 800;
    background: linear-gradient(135deg, #4ECDC4 0%, #A29BFE 50%, #FF6B6B 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px; margin-bottom: 0;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
    color: #4a5568; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 2rem;
}
.section-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
    color: #4ECDC4; letter-spacing: 4px; text-transform: uppercase;
    margin-bottom: 0.3rem;
}
div[data-testid="stExpander"] {
    background: #0d1117; border: 1px solid #1e2d40; border-radius: 12px;
}
.stButton > button {
    background: linear-gradient(135deg, #4ECDC4, #A29BFE);
    color: #07090f; font-weight: 700; font-family: 'JetBrains Mono', monospace;
    border: none; border-radius: 8px; letter-spacing: 1px;
    transition: all 0.2s ease;
}
.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }

.email-box {
    background: #0d1117; border: 1px solid #1e2d40;
    border-radius: 10px; padding: 1.2rem; margin: 0.5rem 0;
}
.tag-green {
    background: #0f3d2e; color: #00ff88; border-radius: 20px;
    padding: 2px 12px; font-size: 0.72rem; font-family: monospace;
    font-weight: 700; letter-spacing: 1px;
}
.tag-red {
    background: #3d0f0f; color: #FF6B6B; border-radius: 20px;
    padding: 2px 12px; font-size: 0.72rem; font-family: monospace;
    font-weight: 700; letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">TALENT HUNTING INTELLIGENCE SYSTEM</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Multi-Agent · Hybrid RAG · Explainable AI · Bias-Aware · Skill Intelligence</div>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Pipeline Settings")
    show_bias     = st.toggle("Bias Audit",            value=True)
    show_graph    = st.toggle("Intelligence Graph",    value=True)
    show_heatmap  = st.toggle("Competency Heatmap",   value=True)
    show_forecast = st.toggle("Skill Gap Forecast",   value=True)
    show_pdf      = st.toggle("PDF Report",            value=True)
    st.divider()
    st.markdown("**Stack**")
    st.code("LLM  : Llama-3.3-70b (Groq)\nEmbed: MiniLM-L6-v2\nRAG  : FAISS + BM25\nUI   : Streamlit", language="yaml")
# Tenant info + logout
    st.sidebar.divider()
    tenant = st.session_state.get("tenant", {})
    st.sidebar.markdown(f"""
    <div style="padding:8px;background:#0d1220;border-radius:8px;
                border:1px solid #1e2d45;font-size:0.75rem;">
        <div style="color:#f1f5f9;font-weight:600;">{tenant.get('company','')}</div>
        <div style="color:#64748b;">👤 {tenant.get('hr_name','')}</div>
        <div style="color:#64748b;">📋 {tenant.get('plan','').title()} plan</div>
        <div style="color:#64748b;">📄 {tenant.get('used',0)}/{tenant.get('limit',0)} resumes</div>
        <div style="color:#64748b;">⏰ Expires: {tenant.get('expires','')}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
# ══════════════════════════════════════════════════════════════════════════════
# INPUT SECTION
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">01 — Job Descriptions</div>', unsafe_allow_html=True)

with st.expander("🔵 Primary Job Description", expanded=True):
    jd_text = st.text_area("Paste primary JD", height=160, key="primary_jd",
                            placeholder="e.g. AI Developer Intern — Python, LangChain, RAG, NLP, 1+ years...")

st.markdown("**➕ Additional Openings** *(optional)*")
if "extra_jds" not in st.session_state:
    st.session_state.extra_jds = []

if st.button("+ Add Role"):
    st.session_state.extra_jds.append({"role_name": "", "text": ""})

for i, jd in enumerate(st.session_state.extra_jds):
    with st.expander(f"📄 Opening #{i+1}: {jd['role_name'] or 'Unnamed'}", expanded=True):
        c1, c2 = st.columns([1, 3])
        st.session_state.extra_jds[i]["role_name"] = c1.text_input(
            "Role Title", value=jd["role_name"], key=f"rn_{i}",
            placeholder="e.g. Data Engineer")
        st.session_state.extra_jds[i]["text"] = c2.text_area(
            "Job Description", value=jd["text"], height=100, key=f"jdt_{i}",
            placeholder="Paste JD text...")
        if st.button(f"🗑 Remove", key=f"rm_{i}"):
            st.session_state.extra_jds.pop(i)
            st.rerun()

st.divider()

# ── Resumes + LinkedIn ────────────────────────────────────────────────────────
st.markdown('<div class="section-label">02 — Candidates</div>', unsafe_allow_html=True)

tab_resume, tab_li_json, tab_li_text = st.tabs([
    "📎 Upload PDF / DOCX",
    "🔗 LinkedIn JSON Export",
    "📋 Paste LinkedIn Text",
])

with tab_resume:
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX resumes",
        type=["pdf", "docx"], accept_multiple_files=True)

with tab_li_json:
    st.caption("👉 LinkedIn → Settings → Data Privacy → Get a copy of your data → Download Profile.json")
    li_json_files = st.file_uploader(
        "Upload LinkedIn Profile.json exports",
        type=["json"], accept_multiple_files=True, key="li_json")

with tab_li_text:
    st.caption("👉 Open LinkedIn profile → Ctrl+A → Ctrl+C → paste below")
    if "li_texts" not in st.session_state:
        st.session_state.li_texts = [{"name": "", "text": ""}]
    for i, entry in enumerate(st.session_state.li_texts):
        c1, c2 = st.columns([1, 3])
        st.session_state.li_texts[i]["name"] = c1.text_input(
            "Name", value=entry["name"], key=f"li_name_{i}",
            placeholder="e.g. Priya Sharma")
        st.session_state.li_texts[i]["text"] = c2.text_area(
            "LinkedIn text", value=entry["text"], height=90,
            key=f"li_text_{i}", placeholder="Paste LinkedIn profile text...")
    if st.button("+ Add LinkedIn profile", key="add_li"):
        st.session_state.li_texts.append({"name": "", "text": ""})
        st.rerun()

# ── Run button ────────────────────────────────────────────────────────────────
st.divider()
if st.button("Search for Suitable Candidates 🔍", type="primary", use_container_width=True):
    if not jd_text.strip():
        st.error("Please enter the primary Job Description.")
    else:
        from app.agents.resume_parser_agent import parse_linkedin_to_profile
        from app.utils.linkedin_parser import (
            parse_linkedin_json_export, parse_linkedin_text_paste)

        temp_dir = tempfile.mkdtemp()
        file_paths, linkedin_profiles = [], []

        for f in (uploaded_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p, "wb") as out:
                out.write(f.read())
            file_paths.append(p)

        for f in (li_json_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p, "wb") as out:
                out.write(f.read())
            try:
                li_data = parse_linkedin_json_export(p)
                linkedin_profiles.append(parse_linkedin_to_profile(li_data))
                st.toast(f"✅ LinkedIn JSON: {li_data.get('name','?')}")
            except Exception as e:
                st.warning(f"LinkedIn JSON error: {e}")

        for entry in st.session_state.get("li_texts", []):
            if entry["text"].strip():
                try:
                    li_data = parse_linkedin_text_paste(entry["text"], entry.get("name",""))
                    linkedin_profiles.append(parse_linkedin_to_profile(li_data))
                    st.toast(f"✅ LinkedIn text: {li_data.get('name','?')}")
                except Exception as e:
                    st.warning(f"LinkedIn text error: {e}")

        if not file_paths and not linkedin_profiles:
            st.error("Upload at least one resume or LinkedIn profile.")
        else:
            extra_jds = [
                {"role_name": j["role_name"] or f"Role {i+1}", "text": j["text"]}
                for i, j in enumerate(st.session_state.extra_jds)
                if j["text"].strip()
            ]
            with st.spinner("🤖 Running multi-agent pipeline..."):
                results = run_pipeline(jd_text, file_paths,
                                       extra_jds=extra_jds,
                                       linkedin_profiles=linkedin_profiles)
                st.session_state["results"]        = results
                st.session_state["jd_structured"]  = results[0]["jd"] if results else {}

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if "results" in st.session_state:
    results       = st.session_state["results"]
    jd_structured = st.session_state.get("jd_structured", {})
    primary_role  = jd_structured.get("role_title", "the role")

    st.divider()
    st.markdown('<div class="section-label">03 — Results</div>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    hire_count = sum(1 for r in results if r["score"].hire_recommendation in ["HIRE","STRONG HIRE"])
    avg_score = (
    sum(r["score"].weighted_total for r in results) / len(results)
    if results else 0
)
    avg_conf = (
    sum(r["score"].confidence for r in results) / len(results)
    if results else 0
)
    n_roles    = len(results[0].get("all_jds", [])) if results else 1
    m1.metric("Screened",    len(results))
    m2.metric("Recommended", hire_count)
    m3.metric("Avg Score",   f"{avg_score:.1f}/10")
    m4.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
    m5.metric("Open Roles",  n_roles)


    st.markdown("#### 📊 Ranked Shortlist")
    table_rows = []
    for i, r in enumerate(results, 1):
        s    = r["score"]
        best = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else "N/A"
        rec  = s.hire_recommendation
        verdict_text = ("✅ SUITABLE FOR HIRING" if rec in ["STRONG HIRE","HIRE"]
                        else "🟡 UNDER CONSIDERATION" if rec == "MAYBE"
                        else "❌ NOT SUITABLE FOR HIRING")
        table_rows.append({
            "Rank":          i,
            "Candidate":     s.candidate_name,
            "Hiring Match":  f"{s.hiring_match_pct}%",
            "Score":         f"{s.weighted_total}/10",
            "Confidence":    f"{int(s.confidence*100)}%",
            "Best-Fit Role": best,
            "Verdict":       verdict_text,
        })
    st.dataframe(table_rows, use_container_width=True,
                 height=min(400, 80 + len(results)*45))

# ── Knowledge Graph ───────────────────────────────────────
    st.markdown("#### 🕸️ Candidate × Role Intelligence Graph")
    st.caption("Hexagons = roles · Circles = candidates · Bright edge = best-fit role")
    st.plotly_chart(plot_multi_jd_graph(results), use_container_width=True)

    # ── Competency Heatmap ────────────────────────────────────
    st.markdown("#### 🌡️ Competency Heatmap")
    st.caption("Red = strong · Blue = weak · Based on JD scoring dimensions")
    st.plotly_chart(build_heatmap(results), use_container_width=True)
    st.markdown("#### 🔍 Candidate Breakdown")
    for rank, r in enumerate(results, 1):
        s          = r["score"]
        profile    = r.get("profile")
        jd_matches = r.get("jd_matches", [])
        best       = jd_matches[0]["role_name"] if jd_matches else "N/A"
        emoji      = REC_ICON.get(s.hire_recommendation, "⚪")

        with st.expander(
            f"{emoji}  #{rank}  {s.candidate_name}  —  "
            f"Hiring Match: {s.hiring_match_pct}%  —  {s.hire_recommendation}"
        ):
            st.markdown(
                verdict_badge(s.hire_recommendation) +
                f' &nbsp;<span style="color:#475569;font-size:0.75rem;">Best fit: {best}</span>',
                unsafe_allow_html=True
            )

            match_color = ("#22c55e" if s.hiring_match_pct >= 70
                           else "#f59e0b" if s.hiring_match_pct >= 50
                           else "#ef4444")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:16px;margin:14px 0;
                        background:#0b0f1a;border:1px solid #1e2d45;
                        border-radius:10px;padding:14px 18px;">
                <div style="font-size:2.2rem;font-weight:800;color:{match_color};
                            font-family:monospace;">{s.hiring_match_pct}%</div>
                <div>
                    <div style="font-size:0.85rem;font-weight:600;color:#e2e8f0;">
                        Hiring Match
                    </div>
                    <div style="font-size:0.72rem;color:#64748b;">
                        Semantic alignment + skill coverage + overall score
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📐 Dimension Scores**")
                for dim in s.dimensions:
                    st.progress(dim.score / 10,
                                text=f"{dim.name}: {dim.score}/10 ({int(dim.weight*100)}%)")
                    st.caption(f"↳ {dim.justification}")
            with col_b:
                st.markdown("**✅ Matched Skills**")
                st.write(", ".join(s.matched_skills) if s.matched_skills else "None detected")
                st.markdown("**❌ Missing Skills**")
                st.write(", ".join(s.missing_skills) if s.missing_skills else "Full match!")
                st.markdown("**💡 AI Reasoning**")
                st.info(s.shortlist_reasoning)

            if jd_matches:
                st.markdown("**🎯 Fit vs All Roles**")
                for idx, match in enumerate(jd_matches):
                    prefix = "🥇" if idx==0 else "🥈" if idx==1 else "🥉" if idx==2 else "  "
                    st.progress(min(match["similarity"], 1.0),
                                text=f"{prefix} {match['role_name']}: {match['similarity']:.4f}")

            if s.missing_skills and profile:
                forecast = compute_transferability(profile.skills, s.missing_skills)
                f1, f2, f3 = st.columns(3)
                f1.metric("Adaptability",      forecast["adaptability"])
                f2.metric("Ramp-Up Time",      forecast["months_estimate"])
                f3.metric("3-Month Readiness", f"{forecast['readiness_score']}%")

            if r.get("bias_audit"):
                audit     = r["bias_audit"]
                risk      = audit.get("bias_risk_level", "UNKNOWN")
                risk_icon = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"��"}.get(risk,"⚪")
                st.markdown(f"**🛡️ Bias Audit** — {risk_icon} {risk}")
                if audit.get("bias_detected"):
                    st.warning("⚠️ Bias types: " + ", ".join(audit.get("bias_types", [])))
                    for rec_item in audit.get("recommendations", []):
                        st.write(f"• {rec_item}")
                else:
                    st.success("No bias detected.")

            st.markdown("**🔧 HR Override**")
            ov1, ov2 = st.columns([1, 3])
            new_score = ov1.number_input("New Score", 0.0, 10.0,
                                          s.weighted_total, 0.5, key=f"ov_{rank}")
            reason = ov2.text_input("Reason (required)", key=f"re_{rank}",
                                     placeholder="e.g. Strong cultural fit from interview")
            if st.button("✅ Apply Override", key=f"ap_{rank}", type="secondary"):
                if not reason.strip():
                    st.error("Please enter a reason.")
                else:
                    idx = rank - 1
                    st.session_state.results[idx]["score"].weighted_total = new_score
                    if   new_score >= 7.5: new_rec = "STRONG HIRE"
                    elif new_score >= 6.0: new_rec = "HIRE"
                    elif new_score >= 4.5: new_rec = "MAYBE"
                    else:                  new_rec = "NO HIRE"
                    st.session_state.results[idx]["score"].hire_recommendation = new_rec
                    st.session_state.results.sort(
                        key=lambda x: x["score"].weighted_total, reverse=True)
                    if "override_log" not in st.session_state:
                        st.session_state.override_log = []
                    st.session_state.override_log.append({
                        "candidate":  s.candidate_name,
                        "old_score":  s.weighted_total,
                        "new_score":  new_score,
                        "new_verdict":new_rec,
                        "reason":     reason,
                    })
                    st.success(f"✅ {s.candidate_name}: {s.weighted_total} → {new_score}/10 | {new_rec}")
                    st.rerun()

                    if "override_log" not in st.session_state:
                        st.session_state["override_log"] = []
                    st.session_state["override_log"].append({
                        "candidate": s.candidate_name,
                        "old_score": s.weighted_total,
                        "new_score": new_score,
                        "new_verdict": new_rec,
                        "reason": reason,
                    })

                    st.success(f"✅ Score updated: {s.weighted_total} → {new_score}/10 | Verdict: {new_rec}")
                    st.rerun()

    # ══════════════════════════════════════════════════════════
    # EMAIL SECTION
    # ══════════════════════════════════════════════════════════
    st.divider()
    if st.session_state.get("override_log"):
        with st.expander(f"📋 HR Override Audit Log ({len(st.session_state['override_log'])} entries)"):
            for entry in st.session_state["override_log"]:
                st.markdown(
                    f"**{entry['candidate']}** — "
                    f"`{entry['old_score']}` → `{entry['new_score']}/10` — "
                    f"**{entry['new_verdict']}** — "
                    f"Reason: _{entry['reason']}_"
                )
    st.divider()
    st.markdown('<div class="section-label">04 — Candidate Emails</div>', unsafe_allow_html=True)
    st.markdown("#### 📧 Send Emails to Candidates")
    st.caption("Pre-written templates auto-filled with candidate names. Edit before sending.")

    with st.expander("⚙️ Email / SMTP Settings", expanded=False):
        ec1, ec2, ec3 = st.columns(3)
        smtp_host_in  = ec1.text_input("SMTP Host",    value=settings.smtp_host)
        smtp_port_in  = ec1.number_input("SMTP Port",  value=int(settings.smtp_port), step=1)
        sender_in     = ec2.text_input("Your Gmail",   value=settings.sender_email)
        password_in   = ec2.text_input("App Password", value=settings.sender_password, type="password")
        hr_name_in    = ec3.text_input("Your Name",    value="HR Team",
                                        placeholder="e.g. Priya Sharma")
        company_in    = ec3.text_input("Company Name", value=settings.company_name,
                                        placeholder="e.g. TechCorp AI")

    st.markdown("#### 🟢 Selection Emails")
    st.caption("Sent to HIRE and STRONG HIRE candidates — personalized by HR before sending.")

    with st.expander("📋 Internship Details (fills into all selection emails)"):
        d1, d2, d3, d4 = st.columns(4)
        duration_in     = d1.text_input("Duration",     value="3 Months", placeholder="3/6 Months")
        mode_in         = d2.text_input("Mode",         value="Remote",   placeholder="Remote/Hybrid/On-site")
        joining_in      = d3.text_input("Joining Date", value="[Date]",   placeholder="1st June 2026")
        stipend_in      = d4.text_input("Stipend",      value="[Amount]", placeholder="₹15,000/month")
        contact_in      = st.text_input("Contact Info", value="",         placeholder="hr@company.com | +91-XXXXXXXXXX")

    shortlisted = [r for r in results if r["score"].hire_recommendation in ["HIRE","STRONG HIRE"]]
    if not shortlisted:
        st.warning("No candidates scored HIRE or above yet.")
    else:
        for r in shortlisted:
            s        = r["score"]
            profile  = r.get("profile")
            best_role = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else primary_role

            with st.expander(f"🟢  {s.candidate_name}  —  {s.hire_recommendation}  —  {best_role}"):
                default_body = get_selection_template(
                    candidate_name=s.candidate_name,
                    role=best_role,
                    company=company_in or settings.company_name,
                    hr_name=hr_name_in,
                    duration=duration_in,
                    mode=mode_in,
                    joining_date=joining_in,
                    stipend=stipend_in,
                    contact=contact_in,
                )

                key_body = f"sel_body_{s.candidate_name}"
                if key_body not in st.session_state:
                    st.session_state[key_body] = default_body

                if st.button("✨ AI Personalize", key=f"ai_sel_{s.candidate_name}",
                             help="Adds one sentence referencing candidate's actual skills"):
                    with st.spinner("Personalizing..."):
                        st.session_state[key_body] = ai_personalize_email(
                            st.session_state[key_body],
                            s.candidate_name,
                            s.matched_skills,
                            s.shortlist_reasoning,
                        )

                edited = st.text_area(
                    "✏️ Edit before sending",
                    value=st.session_state[key_body],
                    height=340,
                    key=f"sel_edit_{s.candidate_name}",
                )
                st.session_state[key_body] = edited

                to_addr = st.text_input("Candidate Email Address",
                                         key=f"sel_email_{s.candidate_name}",
                                         placeholder="candidate@email.com")
                subject = f"🎉 Congratulations! Next Steps — {best_role} at {company_in or settings.company_name}"
                if st.button("📤 Send Selection Email", key=f"send_sel_{s.candidate_name}"):
                    if not to_addr:
                        st.error("Enter candidate email.")
                    elif not sender_in or not password_in:
                        st.error("Fill in SMTP settings above.")
                    else:
                        ok, msg = send_email(to_addr, subject, edited,
                                             smtp_host_in, int(smtp_port_in),
                                             sender_in, password_in)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

    st.markdown("#### 🔴 Rejection Emails")
    st.caption("Auto-filled with candidate name. Edit freely before sending.")

    rejected = [r for r in results if r["score"].hire_recommendation == "NO HIRE"]
    if not rejected:
        st.success("No rejected candidates!")
    else:
        for r in rejected:
            s = r["score"]
            with st.expander(f"🔴  {s.candidate_name}  —  NO HIRE"):
                default_body = get_rejection_template(
                    candidate_name=s.candidate_name,
                    role=primary_role,
                    company=company_in or settings.company_name,
                    hr_name=hr_name_in,
                )

                key_body = f"rej_body_{s.candidate_name}"
                if key_body not in st.session_state:
                    st.session_state[key_body] = default_body

                edited = st.text_area(
                    "✏️ Edit before sending",
                    value=st.session_state[key_body],
                    height=280,
                    key=f"rej_edit_{s.candidate_name}",
                )
                st.session_state[key_body] = edited

                to_addr = st.text_input("Candidate Email Address",
                                         key=f"rej_email_{s.candidate_name}",
                                         placeholder="candidate@email.com")
                subject = f"Update on your application — {primary_role}"

                if st.button("📤 Send Rejection Email", key=f"send_rej_{s.candidate_name}"):
                    if not to_addr:
                        st.error("Enter candidate email.")
                    elif not sender_in or not password_in:
                        st.error("Fill in SMTP settings above.")
                    else:
                        ok, msg = send_email(to_addr, subject, edited,
                                             smtp_host_in, int(smtp_port_in),
                                             sender_in, password_in)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)


    # ── HR Tools Section ──────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">05 — HR Tools</div>', unsafe_allow_html=True)
    st.markdown("#### 🛠️ HR Intelligence Tools")

    tool_tab1, tool_tab2, tool_tab3, tool_tab4 = st.tabs([
        "💬 HR Chatbot",
        "⚖️ Compare Candidates",
        "🎯 Interview Questions",
        "📋 Hiring Summary"
    ])

    with tool_tab1:
        st.markdown("### 💬 Ask Anything About Your Candidates")
        st.caption("Ask in plain English — the AI will query your candidate data")
        examples = [
            "Who is best at Python?",
            "Which candidate has the most LLM experience?",
            "Who should I interview first and why?",
            "Which candidate is weakest in experience?",
            "Summarize all candidates in 3 sentences",
        ]
        cols = st.columns(3)
        for i, ex in enumerate(examples):
            if cols[i % 3].button(ex, key=f"ex_{i}", type="secondary"):
                st.session_state.chatbot_input = ex
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'''<div style="background:#1e3a5f;border-radius:10px;padding:10px 14px;margin:8px 0;font-size:0.88rem;">👤 {msg["content"]}</div>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<div style="background:#111827;border:1px solid #1e2d45;border-radius:10px;padding:10px 14px;margin:8px 0;font-size:0.88rem;">🧠 {msg["content"]}</div>''', unsafe_allow_html=True)
        user_input = st.text_input("Ask HR Chatbot", value=st.session_state.get("chatbot_input",""),
                                    placeholder="e.g. Show me candidates best in Python...",
                                    key="chat_input_box", label_visibility="collapsed")
        col_send, col_clear = st.columns([1, 5])
        if col_send.button("Send", type="primary", key="send_chat"):
            if user_input.strip():
                with st.spinner("Thinking..."):
                    response = ask_hr_chatbot(user_input, results, st.session_state.chat_history)
                st.session_state.chat_history.append({"role":"user","content":user_input})
                st.session_state.chat_history.append({"role":"assistant","content":response})
                st.session_state.chatbot_input = ""
                st.rerun()
        if col_clear.button("Clear Chat", type="secondary", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

    with tool_tab2:
        st.markdown("### ⚖️ Head-to-Head Candidate Comparison")
        candidate_names = [r["score"].candidate_name for r in results]
        c1, c2 = st.columns(2)
        cand_a = c1.selectbox("Candidate A", candidate_names, key="cmp_a")
        cand_b = c2.selectbox("Candidate B", candidate_names, index=min(1,len(candidate_names)-1), key="cmp_b")
        if st.button("⚖️ Compare Now", type="primary", key="do_compare"):
            if cand_a == cand_b:
                st.error("Please select two different candidates.")
            else:
                result_a = next(r for r in results if r["score"].candidate_name == cand_a)
                result_b = next(r for r in results if r["score"].candidate_name == cand_b)
                col_a, col_b = st.columns(2)
                with col_a:
                    sa = result_a["score"]
                    color_a = "#22c55e" if sa.weighted_total >= 7 else "#f59e0b" if sa.weighted_total >= 5 else "#ef4444"
                    st.markdown(f'''<div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:16px;text-align:center;"><div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">{cand_a}</div><div style="font-size:2.5rem;font-weight:800;color:{color_a};">{sa.weighted_total}/10</div><div style="font-size:0.8rem;color:#64748b;">{sa.hire_recommendation}</div></div>''', unsafe_allow_html=True)
                with col_b:
                    sb = result_b["score"]
                    color_b = "#22c55e" if sb.weighted_total >= 7 else "#f59e0b" if sb.weighted_total >= 5 else "#ef4444"
                    st.markdown(f'''<div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:16px;text-align:center;"><div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">{cand_b}</div><div style="font-size:2.5rem;font-weight:800;color:{color_b};">{sb.weighted_total}/10</div><div style="font-size:0.8rem;color:#64748b;">{sb.hire_recommendation}</div></div>''', unsafe_allow_html=True)
                st.markdown("**📐 Dimension Comparison**")
                for dim_a in result_a["score"].dimensions:
                    dim_b_score = next((d.score for d in result_b["score"].dimensions if d.name == dim_a.name), 0)
                    dc1, dc2, dc3 = st.columns([2,3,3])
                    dc1.markdown(f"<div style='font-size:0.78rem;color:#94a3b8;padding-top:6px;'>{dim_a.name}</div>", unsafe_allow_html=True)
                    dc2.progress(dim_a.score/10, text=f"{cand_a.split()[0]}: {dim_a.score}/10")
                    dc3.progress(dim_b_score/10, text=f"{cand_b.split()[0]}: {dim_b_score}/10")
                st.markdown("**🧠 AI Analysis**")
                with st.spinner("Generating AI comparison..."):
                    comparison = compare_candidates(result_a, result_b)
                st.info(comparison)

    with tool_tab3:
        st.markdown("### 🎯 Personalized Interview Question Generator")
        selected = st.selectbox("Select Candidate", [r["score"].candidate_name for r in results], key="iq_select")
        num_q = st.slider("Number of Questions", 5, 15, 8, key="iq_num")
        if st.button("🎯 Generate Questions", type="primary", key="gen_iq"):
            candidate_result = next(r for r in results if r["score"].candidate_name == selected)
            with st.spinner("Generating personalized questions..."):
                try:
                    questions = generate_interview_questions(candidate_result, jd_structured, num_q)
                    categories = {
                        "technical":   ("🔧 Technical Depth", "#3b82f6"),
                        "gap_probe":   ("🔍 Gap Probe",       "#f59e0b"),
                        "behavioural": ("💼 Behavioural",     "#8b5cf6"),
                        "culture_fit": ("🤝 Culture Fit",     "#22c55e"),
                        "motivation":  ("🎯 Motivation",      "#14b8a6"),
                    }
                    for key, (label, color) in categories.items():
                        qs = questions.get(key, [])
                        if qs:
                            st.markdown(f"**{label}**")
                            for i, q in enumerate(qs, 1):
                                st.markdown(f'''<div style="background:#111827;border-left:3px solid {color};border-radius:6px;padding:10px 14px;margin:6px 0;font-size:0.88rem;color:#e2e8f0;">{i}. {q}</div>''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error: {e}")

    with tool_tab4:
        st.markdown("### 📋 Executive Hiring Summary")
        company_name = st.text_input("Company Name", value=settings.company_name, key="sum_company")
        if st.button("📋 Generate Summary", type="primary", key="gen_sum"):
            with st.spinner("Generating..."):
                summary = generate_hiring_summary(results, jd_structured, company_name)
                st.session_state["hiring_summary"] = summary
        if "hiring_summary" in st.session_state:
            edited_summary = st.text_area("Edit Summary", value=st.session_state["hiring_summary"], height=300, key="sum_edit")
            st.download_button("⬇️ Download Summary", edited_summary, "hiring_summary.txt", use_container_width=True)


    # ── PDF Report ────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">05 — Export</div>', unsafe_allow_html=True)
    st.markdown("#### 📄 PDF Shortlist Report")
    if st.button("Generate PDF Report", use_container_width=True):
        with st.spinner("Building report..."):
            path = "/tmp/shortlist_report.pdf"
            generate_pdf_report(results, jd_structured, path)
            with open(path, "rb") as f:
                st.download_button("⬇️ Download PDF", f,
                                   "shortlist_report.pdf",
                                   "application/pdf",
                                   use_container_width=True)