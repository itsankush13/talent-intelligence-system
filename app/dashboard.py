from app.core.email_sender import generate_rejection_email, generate_selection_email, send_email
from app.core.config import settings
import streamlit as st
import tempfile, os
from app.core.pipeline import run_pipeline
from app.core.knowledge_graph import plot_multi_jd_graph
from app.core.skill_gap_forecaster import compute_transferability
from app.core.report_generator import generate_pdf_report

st.set_page_config(page_title="Talent Intelligence System", page_icon="🧠", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

.stApp { background: #07090f; }

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #4ECDC4 0%, #A29BFE 50%, #FF6B6B 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
    margin-bottom: 0;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #555e7a;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 2rem;
}
.metric-box {
    background: linear-gradient(135deg, #0d1117 0%, #161b27 100%);
    border: 1px solid #1e2d40;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: center;
}
.jd-card {
    background: #0d1117;
    border: 1px solid #1e2d40;
    border-left: 3px solid #4ECDC4;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #8892a4;
}
.best-fit-badge {
    display: inline-block;
    background: linear-gradient(90deg, #4ECDC4, #A29BFE);
    color: #07090f;
    font-weight: 700;
    font-size: 0.7rem;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.role-match-row {
    background: #0d1117;
    border: 1px solid #1a2236;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.35rem 0;
    display: flex;
    align-items: center;
    gap: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}
div[data-testid="stExpander"] {
    background: #0d1117;
    border: 1px solid #1e2d40;
    border-radius: 12px;
}
.stButton > button {
    background: linear-gradient(135deg, #4ECDC4, #A29BFE);
    color: #07090f;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    border: none;
    border-radius: 8px;
    letter-spacing: 1px;
}
.stButton > button:hover {
    opacity: 0.85;
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">Talent Intelligence System</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Multi-Agent · Hybrid RAG · Explainable AI · Bias-Aware</div>', unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Pipeline Config")
    show_bias    = st.toggle("Bias Audit",           value=True)
    show_graph   = st.toggle("Intelligence Graph",   value=True)
    show_forecast= st.toggle("Skill Gap Forecast",   value=True)
    show_pdf     = st.toggle("PDF Report",           value=True)
    st.divider()
    st.markdown("**Stack**")
    st.code("LLM: Llama-3.3-70b (Groq)\nEmbed: MiniLM-L6-v2\nRetrieval: FAISS + BM25\nAgents: LangGraph-style", language="yaml")

# ── INPUT SECTION ─────────────────────────────────────────────────────────────
st.markdown("### 📋 Job Descriptions")

# Primary JD
with st.expander("🔵 Primary Job Description", expanded=True):
    jd_text = st.text_area("Paste primary JD", height=180, key="primary_jd",
                            placeholder="e.g. Senior ML Engineer — Python, LangChain, FastAPI, 4+ years...")

# Multiple extra JDs
st.markdown("**➕ Additional Openings** *(optional — add as many as you have)*")

if "extra_jds" not in st.session_state:
    st.session_state.extra_jds = []

col_add, col_clear = st.columns([1, 5])
with col_add:
    if st.button("+ Add Role"):
        st.session_state.extra_jds.append({"role_name": "", "text": ""})

for i, jd in enumerate(st.session_state.extra_jds):
    with st.expander(f"📄 Opening #{i+1}: {jd['role_name'] or 'Unnamed Role'}", expanded=True):
        c1, c2 = st.columns([1, 3])
        st.session_state.extra_jds[i]["role_name"] = c1.text_input(
            "Role Title", value=jd["role_name"], key=f"rn_{i}",
            placeholder="e.g. Data Engineer")
        st.session_state.extra_jds[i]["text"] = c2.text_area(
            "Job Description", value=jd["text"], height=120, key=f"jdt_{i}",
            placeholder="Paste JD text here...")
        if st.button(f"🗑 Remove", key=f"rm_{i}"):
            st.session_state.extra_jds.pop(i)
            st.rerun()

st.divider()

# Resumes
st.markdown("### 📄 Candidate Resumes & LinkedIn Profiles")

tab_resume, tab_li_json, tab_li_text = st.tabs([
    "📎 Upload PDF/DOCX",
    "🔗 LinkedIn JSON Export",
    "📋 Paste LinkedIn Text",
])

with tab_resume:
    uploaded_files = st.file_uploader(
        "Upload PDF or DOCX resumes",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )

with tab_li_json:
    st.caption("👉 LinkedIn → Settings → Data Privacy → Get a copy of your data → Download 'Profile.json'")
    li_json_files = st.file_uploader(
        "Upload LinkedIn Profile JSON exports",
        type=["json"],
        accept_multiple_files=True,
        key="li_json",
    )

with tab_li_text:
    st.caption("👉 Open LinkedIn profile in browser → Ctrl+A → Ctrl+C → paste below")
    if "li_texts" not in st.session_state:
        st.session_state.li_texts = [{"name": "", "text": ""}]

    for i, entry in enumerate(st.session_state.li_texts):
        c1, c2 = st.columns([1, 3])
        st.session_state.li_texts[i]["name"] = c1.text_input(
            "Candidate name", value=entry["name"], key=f"li_name_{i}",
            placeholder="e.g. Priya Sharma")
        st.session_state.li_texts[i]["text"] = c2.text_area(
            "Paste LinkedIn text", value=entry["text"],
            height=100, key=f"li_text_{i}",
            placeholder="Paste full LinkedIn profile text here...")

    if st.button("+ Add another LinkedIn profile", key="add_li_text"):
        st.session_state.li_texts.append({"name": "", "text": ""})
        st.rerun()


# ── RUN ───────────────────────────────────────────────────────────────────────
if st.button("SEARCH SUITABLE CANDIDATES 🔎", type="primary", use_container_width=True):
    if not jd_text.strip():
        st.error("Please enter the primary Job Description.")
    else:
        from app.agents.resume_parser_agent import parse_linkedin_to_profile
        from app.utils.linkedin_parser import (
            parse_linkedin_json_export,
            parse_linkedin_text_paste,
        )

        temp_dir = tempfile.mkdtemp()
        file_paths = []
        linkedin_profiles = []  # Will hold CandidateProfile objects

        # ── PDF/DOCX resumes ──────────────────────────────────
        for f in (uploaded_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p, "wb") as out:
                out.write(f.read())
            file_paths.append(p)

        # ── LinkedIn JSON exports ─────────────────────────────
        for f in (li_json_files or []):
            p = os.path.join(temp_dir, f.name)
            with open(p, "wb") as out:
                out.write(f.read())
            try:
                li_data = parse_linkedin_json_export(p)
                linkedin_profiles.append(parse_linkedin_to_profile(li_data))
                st.toast(f"✅ LinkedIn JSON parsed: {li_data.get('name','?')}")
            except Exception as e:
                st.warning(f"Could not parse LinkedIn JSON {f.name}: {e}")

        # ── LinkedIn text pastes ──────────────────────────────
        for entry in st.session_state.get("li_texts", []):
            if entry["text"].strip():
                try:
                    li_data = parse_linkedin_text_paste(entry["text"])
                    if entry["name"].strip():
                        li_data["name"] = entry["name"].strip()
                    linkedin_profiles.append(parse_linkedin_to_profile(li_data))
                    st.toast(f"✅ LinkedIn text parsed: {li_data.get('name','?')}")
                except Exception as e:
                    st.warning(f"LinkedIn text parse error: {e}")

        # ── LinkedIn URLs (RapidAPI) ──────────────────────────
     
        if not file_paths and not linkedin_profiles:
            st.error("Please upload at least one resume or add a LinkedIn profile.")
        else:
            extra_jds = [
                {"role_name": j["role_name"] or f"Role {i+1}", "text": j["text"]}
                for i, j in enumerate(st.session_state.extra_jds)
                if j["text"].strip()
            ]
            with st.spinner("🤖 Multi-agent pipeline running..."):
                results = run_pipeline(
                    jd_text, file_paths,
                    extra_jds=extra_jds,
                    linkedin_profiles=linkedin_profiles,   # ← pass LinkedIn profiles
                )
                st.session_state["results"] = results
                st.session_state["jd_structured"] = results[0]["jd"] if results else {}

# ── RESULTS ───────────────────────────────────────────────────────────────────
if "results" in st.session_state:
    results        = st.session_state["results"]
    jd_structured  = st.session_state.get("jd_structured", {})

    st.divider()

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    hire_count = sum(1 for r in results if r["score"].hire_recommendation in ["HIRE","STRONG HIRE"])
    avg_score  = sum(r["score"].weighted_total for r in results) / len(results)
    avg_conf   = sum(r["score"].confidence for r in results) / len(results)
    n_roles    = len(results[0].get("all_jds", [])) if results else 0

    m1.metric("Screened",    len(results))
    m2.metric("Recommended", hire_count)
    m3.metric("Avg Score",   f"{avg_score:.1f}/10")
    m4.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
    m5.metric("Open Roles",  n_roles)

    # ── Ranked Table ──────────────────────────────────────────
    st.markdown("### 📊 Ranked Shortlist")
    rec_icon = {"STRONG HIRE":"🟢","HIRE":"🔵","MAYBE":"🟡","NO HIRE":"🔴"}
    table_data = []
    for i, r in enumerate(results, 1):
        s = r["score"]
        best = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else "N/A"
        best_sim = r["jd_matches"][0]["similarity"] if r.get("jd_matches") else 0
        table_data.append({
            "Rank":           i,
            "Candidate":      s.candidate_name,
            "Score":          f"{s.weighted_total}/10",
            "Confidence":     f"{int(s.confidence*100)}%",
            "Sem Similarity": f"{s.semantic_similarity:.3f}",
            "Best-Fit Role":  best,
            "Role Similarity":f"{best_sim:.3f}",
            "Verdict":        rec_icon.get(s.hire_recommendation,"⚪") + " " + s.hire_recommendation,
        })
    st.dataframe(table_data, use_container_width=True)

    # ── Intelligence Graph ────────────────────────────────────
    if show_graph:
        st.markdown("### 🕸️ Candidate × Role Fit Intelligence Graph")
        st.caption("Hexagons = open roles · Circles = candidates (sized by score, colored by verdict) · Bright edges = best-fit match")
        fig = plot_multi_jd_graph(results)
        st.plotly_chart(fig, use_container_width=True)

    # ── Multi-JD Role Match Section ───────────────────────────
    st.markdown("### 🎯 Candidate → Role Assignment Intelligence")
    st.caption("Every candidate ranked against every open role by semantic similarity")

    for rank, r in enumerate(results, 1):
        s = r["score"]
        jd_matches = r.get("jd_matches", [])
        emoji = rec_icon.get(s.hire_recommendation, "⚪")

        with st.expander(f"{emoji}  {s.candidate_name}  —  Best Fit: **{jd_matches[0]['role_name'] if jd_matches else 'N/A'}**"):
            st.markdown(f"**Overall Score:** `{s.weighted_total}/10` &nbsp;&nbsp; **Verdict:** {s.hire_recommendation}")
            st.markdown("**Role-by-Role Fit Scores:**")
            
            for idx, match in enumerate(jd_matches):
                sim = match["similarity"]
                role = match["role_name"]
                bar_val = min(sim, 1.0)

                # Color based on rank
                if idx == 0:
                    label = f"🥇 **{role}** ← Best Fit"
                elif idx == 1:
                    label = f"🥈 {role}"
                else:
                    label = f"🥉 {role}" if idx == 2 else f"&nbsp;&nbsp;&nbsp; {role}"

                st.markdown(label, unsafe_allow_html=True)
                st.progress(bar_val, text=f"Similarity: {sim:.4f}")

            st.divider()

            # Skills + reasoning in compact view
            ca, cb = st.columns(2)
            with ca:
                st.markdown("**✅ Matched Skills**")
                st.write(", ".join(s.matched_skills) if s.matched_skills else "—")
                st.markdown("**❌ Missing Skills**")
                st.write(", ".join(s.missing_skills) if s.missing_skills else "Full match!")
            with cb:
                st.markdown("**💡 AI Reasoning**")
                st.info(s.shortlist_reasoning)

            # Skill gap forecast
            if show_forecast and s.missing_skills and r.get("profile"):
                forecast = compute_transferability(r["profile"].skills, s.missing_skills)
                f1, f2, f3 = st.columns(3)
                f1.metric("Adaptability",   forecast["adaptability"])
                f2.metric("Ramp-Up Time",   forecast["months_estimate"])
                f3.metric("Readiness in 3M",f"{forecast['readiness_score']}%")

            # Bias audit
            if show_bias and r.get("bias_audit"):
                audit = r["bias_audit"]
                risk  = audit.get("bias_risk_level","UNKNOWN")
                risk_icon = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🔴"}.get(risk,"⚪")
                st.markdown(f"**🛡️ Bias Audit** — {risk_icon} {risk}")
                if audit.get("bias_detected"):
                    st.warning(", ".join(audit.get("bias_types",[])))
                else:
                    st.success("No bias detected.")

            # HR override
            ov1, ov2 = st.columns([1, 3])
            new_score = ov1.number_input("Override Score", 0.0, 10.0,
                                          s.weighted_total, 0.5, key=f"ov_{rank}")
            reason = ov2.text_input("Reason", key=f"re_{rank}",
                                     placeholder="e.g. Strong culture fit")
            if st.button("✅ Apply", key=f"ap_{rank}"):
                st.success(f"Score → {new_score}/10 logged.")

    # ── PDF Download ──────────────────────────────────────────
# ── PDF Report ────────────────────────────────────────────
    if show_pdf:
        st.divider()
        st.markdown("### 📄 Generate Report")
        if st.button("Generate PDF Shortlist Report", use_container_width=True):
            with st.spinner("Building PDF..."):
                path = "/tmp/shortlist_report.pdf"
                generate_pdf_report(results, jd_structured, path)
                with open(path, "rb") as f:
                    st.download_button("⬇️ Download PDF", f,
                                       "shortlist_report.pdf",
                                       "application/pdf",
                                       use_container_width=True)

    # ── Email Section ─────────────────────────────────────────
    st.divider()
    st.markdown("### 📧 Send Candidate Emails")
    st.caption("Auto-generate and send emails to candidates. Rejections are automated; selection emails are personalised by HR.")

    # SMTP config expander
    with st.expander("⚙️ Email Settings (SMTP)", expanded=False):
        st.caption("Pre-filled from .env — override here for this session only.")
        ec1, ec2 = st.columns(2)
        smtp_host_in  = ec1.text_input("SMTP Host",   value=settings.smtp_host)
        smtp_port_in  = ec1.number_input("SMTP Port", value=settings.smtp_port, step=1)
        sender_in     = ec2.text_input("Sender Email", value=settings.sender_email)
        password_in   = ec2.text_input("App Password", value=settings.sender_password, type="password")
        company_in    = ec2.text_input("Company Name", value=settings.company_name)

    primary_role = jd_structured.get("role_title", "the role")

    # ── Rejection emails (auto, for NO HIRE candidates) ───────
    st.markdown("#### 🔴 Rejection Emails")
    rejected = [r for r in results if r["score"].hire_recommendation == "NO HIRE"]

    if not rejected:
        st.success("No rejected candidates — everyone scored above the threshold!")
    else:
        st.info(f"{len(rejected)} candidate(s) marked NO HIRE — rejection emails will be auto-generated.")
        for r in rejected:
            s = r["score"]
            with st.expander(f"🔴 {s.candidate_name}"):
                # Generate email on demand
                if st.button(f"Generate Rejection Email", key=f"gen_rej_{s.candidate_name}"):
                    with st.spinner("Generating..."):
                        body = generate_rejection_email(s.candidate_name, primary_role, company_in)
                        st.session_state[f"rej_body_{s.candidate_name}"] = body

                body = st.session_state.get(f"rej_body_{s.candidate_name}", "")
                edited_body = st.text_area("Email Body (editable)", value=body,
                                            height=180, key=f"rej_edit_{s.candidate_name}")
                to_addr = st.text_input("Candidate Email Address", key=f"rej_email_{s.candidate_name}",
                                         placeholder="candidate@email.com")
                subject = f"Update on your application — {primary_role}"

                if st.button("📤 Send Rejection Email", key=f"send_rej_{s.candidate_name}"):
                    if not to_addr:
                        st.error("Enter the candidate's email address.")
                    elif not sender_in or not password_in:
                        st.error("Configure SMTP settings above.")
                    elif not edited_body:
                        st.error("Generate the email body first.")
                    else:
                        ok, msg = send_email(to_addr, subject, edited_body,
                                             smtp_host_in, int(smtp_port_in),
                                             sender_in, password_in)
                        st.success(msg) if ok else st.error(msg)

    # ── Selection / personalised emails ───────────────────────
    st.markdown("#### 🟢 Selection & Interview Emails")
    shortlisted = [r for r in results
                   if r["score"].hire_recommendation in ["HIRE", "STRONG HIRE"]]

    if not shortlisted:
        st.warning("No candidates scored HIRE or above yet.")
    else:
        for r in shortlisted:
            s = r["score"]
            best_role = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else primary_role
            with st.expander(f"🟢 {s.candidate_name}  —  {s.hire_recommendation}"):
                st.markdown(f"**Recommended for:** {best_role}")

                hr_notes = st.text_area(
                    "Your personal notes to include in email",
                    key=f"sel_notes_{s.candidate_name}",
                    placeholder="e.g. Loved your RAG project, want to discuss your LangGraph experience...",
                    height=80,
                )

                if st.button("Generate Selection Email", key=f"gen_sel_{s.candidate_name}"):
                    with st.spinner("Generating personalised email..."):
                        body = generate_selection_email(
                            s.candidate_name, best_role, hr_notes, company_in)
                        st.session_state[f"sel_body_{s.candidate_name}"] = body

                body = st.session_state.get(f"sel_body_{s.candidate_name}", "")
                edited = st.text_area("Email Body (editable)", value=body,
                                       height=200, key=f"sel_edit_{s.candidate_name}")
                to_addr = st.text_input("Candidate Email Address",
                                         key=f"sel_email_{s.candidate_name}",
                                         placeholder="candidate@email.com")
                subject = f"Great news! Next steps — {best_role} at {company_in}"

                if st.button("📤 Send Selection Email", key=f"send_sel_{s.candidate_name}"):
                    if not to_addr:
                        st.error("Enter candidate email.")
                    elif not sender_in or not password_in:
                        st.error("Configure SMTP settings above.")
                    elif not edited:
                        st.error("Generate the email first.")
                    else:
                        ok, msg = send_email(to_addr, subject, edited,
                                             smtp_host_in, int(smtp_port_in),
                                             sender_in, password_in)
                        st.success(msg) if ok else st.error(msg)