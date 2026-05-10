import streamlit as st
import tempfile, os
from app.core.pipeline import run_pipeline
from app.core.knowledge_graph import plot_multi_jd_graph
from app.core.skill_gap_forecaster import compute_transferability
from app.core.report_generator import generate_pdf_report
from app.core.heatmap import build_heatmap
from app.core.email_sender import (
    get_rejection_template, get_selection_template,
    ai_personalize_email, send_email,
)
from app.core.config import settings

st.set_page_config(page_title="Talent Intelligence System", page_icon="🧠", layout="wide")

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
st.markdown('<div class="hero-title">Talent Intelligence System</div>', unsafe_allow_html=True)
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
if st.button("🚀  Run Intelligence Pipeline", type="primary", use_container_width=True):
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
    avg_score  = sum(r["score"].weighted_total for r in results) / len(results)
    avg_conf   = sum(r["score"].confidence for r in results) / len(results)
    n_roles    = len(results[0].get("all_jds", [])) if results else 1
    m1.metric("Screened",    len(results))
    m2.metric("Recommended", hire_count)
    m3.metric("Avg Score",   f"{avg_score:.1f}/10")
    m4.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
    m5.metric("Open Roles",  n_roles)

    # Ranked table
    st.markdown("#### 📊 Ranked Shortlist")
    rec_icon = {"STRONG HIRE":"🟢","HIRE":"🔵","MAYBE":"🟡","NO HIRE":"🔴"}
    table_data = []
    for i, r in enumerate(results, 1):
        s    = r["score"]
        best = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else "N/A"
        best_sim = r["jd_matches"][0]["similarity"] if r.get("jd_matches") else 0
        table_data.append({
            "Rank": i, "Candidate": s.candidate_name,
            "Score": f"{s.weighted_total}/10",
            "Confidence": f"{int(s.confidence*100)}%",
            "Sem Sim": f"{s.semantic_similarity:.3f}",
            "Best-Fit Role": best,
            "Role Sim": f"{best_sim:.3f}",
            "Verdict": rec_icon.get(s.hire_recommendation,"⚪") + " " + s.hire_recommendation,
        })
    st.dataframe(table_data, use_container_width=True)

    # ── Knowledge Graph ───────────────────────────────────────
    if show_graph:
        st.markdown("#### 🕸️ Candidate × Role Intelligence Graph")
        st.caption("Hexagons = roles · Circles = candidates (size = score, color = verdict) · Bright edge = best-fit role")
        st.plotly_chart(plot_multi_jd_graph(results), use_container_width=True)

    # ── Competency Heatmap ────────────────────────────────────
    if show_heatmap:
        st.markdown("#### 🌡️ Competency Heatmap")
        st.caption("Red = strong in that dimension · Blue = weak · Based on JD requirements")
        st.plotly_chart(build_heatmap(results), use_container_width=True)

    # ── Role match + explainability ───────────────────────────
    st.markdown("#### 🎯 Candidate → Role Assignment")
    for rank, r in enumerate(results, 1):
        s          = r["score"]
        jd_matches = r.get("jd_matches", [])
        profile    = r.get("profile")
        emoji      = rec_icon.get(s.hire_recommendation, "⚪")
        best       = jd_matches[0]["role_name"] if jd_matches else "N/A"

        with st.expander(f"{emoji}  #{rank}  {s.candidate_name}  —  {s.weighted_total}/10  —  Best fit: {best}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📐 Dimension Scores**")
                for dim in s.dimensions:
                    st.progress(dim.score/10, text=f"{dim.name}: {dim.score}/10 ({int(dim.weight*100)}%)")
                    st.caption(f"↳ {dim.justification}")
            with col_b:
                st.markdown("**✅ Matched Skills**")
                st.write(", ".join(s.matched_skills) if s.matched_skills else "None detected")
                st.markdown("**❌ Missing Skills**")
                st.write(", ".join(s.missing_skills) if s.missing_skills else "Full match!")
                st.markdown("**💡 AI Reasoning**")
                st.info(s.shortlist_reasoning)

            # Role fit bars
            st.markdown("**🎯 Fit vs All Roles**")
            for idx, match in enumerate(jd_matches):
                prefix = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "  "
                st.progress(min(match["similarity"], 1.0),
                            text=f"{prefix} {match['role_name']}: {match['similarity']:.4f}")

            # Skill gap forecast
            if show_forecast and s.missing_skills and profile:
                forecast = compute_transferability(profile.skills, s.missing_skills)
                f1, f2, f3 = st.columns(3)
                f1.metric("Adaptability",    forecast["adaptability"])
                f2.metric("Ramp-Up Time",    forecast["months_estimate"])
                f3.metric("3-Month Readiness", f"{forecast['readiness_score']}%")

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
                                     placeholder="e.g. Strong cultural fit from interview")
            if st.button("✅ Apply Override", key=f"ap_{rank}"):
                if not reason.strip():
                    st.error("Please enter a reason for the override.")
                else:
                    # Write new score back into session state so it persists
                    idx = rank - 1
                    st.session_state["results"][idx]["score"].weighted_total = new_score

                    # Recalculate hire recommendation based on new score
                    if new_score >= 7.5:
                        new_rec = "STRONG HIRE"
                    elif new_score >= 6.0:
                        new_rec = "HIRE"
                    elif new_score >= 4.5:
                        new_rec = "MAYBE"
                    else:
                        new_rec = "NO HIRE"
                    st.session_state["results"][idx]["score"].hire_recommendation = new_rec

                    # Re-sort results by new scores
                    st.session_state["results"].sort(
                        key=lambda x: x["score"].weighted_total, reverse=True)

                    # Log override to session state audit trail
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
    # ── Override audit log ────────────────────────────────────
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

    # SMTP settings
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

    # ── Selection email customisation fields ──────────────────
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
                # Pre-fill template immediately
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

                # AI personalize button
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
                # Save edits back
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

    # ── Rejection emails ──────────────────────────────────────
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