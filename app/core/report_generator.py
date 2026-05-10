from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER
from datetime import datetime


# ── Color palette ──────────────────────────────────────────────────────────────
DARK       = colors.HexColor("#07090f")
NAVY       = colors.HexColor("#1a1a2e")
TEAL       = colors.HexColor("#4ECDC4")
PURPLE     = colors.HexColor("#A29BFE")
RED        = colors.HexColor("#FF6B6B")
YELLOW     = colors.HexColor("#FFE66D")
GREEN      = colors.HexColor("#00ff88")
LIGHT_GREY = colors.HexColor("#f7f9fc")
MID_GREY   = colors.HexColor("#cccccc")

REC_COLOR = {
    "STRONG HIRE": GREEN,
    "HIRE":        TEAL,
    "MAYBE":       YELLOW,
    "NO HIRE":     RED,
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"],
                                 fontSize=22, textColor=NAVY,
                                 spaceAfter=4, fontName="Helvetica-Bold"),
        "h2":    ParagraphStyle("H2", parent=base["Heading2"],
                                 fontSize=13, textColor=NAVY,
                                 spaceBefore=14, spaceAfter=4,
                                 fontName="Helvetica-Bold"),
        "h3":    ParagraphStyle("H3", parent=base["Heading3"],
                                 fontSize=10, textColor=NAVY,
                                 spaceBefore=8, spaceAfter=2,
                                 fontName="Helvetica-Bold"),
        "body":  ParagraphStyle("Body", parent=base["Normal"],
                                 fontSize=8.5, leading=13),
        "small": ParagraphStyle("Small", parent=base["Normal"],
                                 fontSize=7.5, leading=11,
                                 textColor=colors.HexColor("#555555")),
        "center":ParagraphStyle("Center", parent=base["Normal"],
                                 fontSize=8.5, alignment=TA_CENTER),
    }


def generate_pdf_report(results: list, jd_structured: dict, output_path: str) -> str:
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    S = _styles()
    elements = []

    # ── Cover header ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Talent Intelligence System", S["title"]))
    elements.append(Paragraph(
        f"AI-Powered Shortlist Report &nbsp;·&nbsp; {datetime.now().strftime('%d %b %Y, %H:%M')}",
        S["body"]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=2.5, color=TEAL))
    elements.append(Spacer(1, 0.4*cm))

    # ── JD summary ────────────────────────────────────────────────────────────
    elements.append(Paragraph("Primary Job Description", S["h2"]))
    jd_rows = [
        ["Role",          jd_structured.get("role_title", "N/A")],
        ["Seniority",     jd_structured.get("seniority_level", "N/A")],
        ["Min Exp.",      f"{jd_structured.get('min_experience_years', '?')} yrs"],
        ["Required Skills",
         ", ".join(jd_structured.get("required_skills", [])[:10])],
    ]
    jd_table = Table(jd_rows, colWidths=[3.8*cm, 13.2*cm])
    jd_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), colors.HexColor("#eef2ff")),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8.5),
        ("GRID",        (0,0), (-1,-1), 0.4, MID_GREY),
        ("PADDING",     (0,0), (-1,-1), 6),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
    ]))
    elements.append(jd_table)
    elements.append(Spacer(1, 0.6*cm))

    # ── Summary statistics ────────────────────────────────────────────────────
    elements.append(Paragraph("Screening Summary", S["h2"]))
    total      = len(results)
    strong     = sum(1 for r in results if r["score"].hire_recommendation == "STRONG HIRE")
    hire       = sum(1 for r in results if r["score"].hire_recommendation == "HIRE")
    maybe      = sum(1 for r in results if r["score"].hire_recommendation == "MAYBE")
    no_hire    = sum(1 for r in results if r["score"].hire_recommendation == "NO HIRE")
    avg_score  = sum(r["score"].weighted_total for r in results) / max(total, 1)

    stat_rows = [
        ["Total Screened", "Strong Hire", "Hire", "Maybe", "No Hire", "Avg Score"],
        [str(total), str(strong), str(hire), str(maybe), str(no_hire),
         f"{avg_score:.1f}/10"],
    ]
    stat_table = Table(stat_rows, colWidths=[3*cm]*6)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("GRID",        (0,0), (-1,-1), 0.4, MID_GREY),
        ("PADDING",     (0,0), (-1,-1), 8),
        ("BACKGROUND",  (0,1), (0,1), colors.HexColor("#eef2ff")),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 0.6*cm))

    # ── Master ranking table ──────────────────────────────────────────────────
    elements.append(Paragraph("Candidate Rankings — Primary Role", S["h2"]))

    rank_header = ["#", "Candidate", "Score", "Conf.", "Semantic", "Verdict", "Best-Fit Role"]
    rank_rows   = [rank_header]

    for i, r in enumerate(results, 1):
        s    = r["score"]
        best = r["jd_matches"][0]["role_name"] if r.get("jd_matches") else "—"
        # Mark if best fit is NOT the primary role
        primary_role = jd_structured.get("role_title", "")
        alt_flag = ""
        if r.get("jd_matches") and len(r["jd_matches"]) > 1:
            if r["jd_matches"][0]["role_name"] != primary_role:
                alt_flag = " ★"   # star = better fit elsewhere
        rank_rows.append([
            str(i),
            s.candidate_name,
            f"{s.weighted_total}/10",
            f"{int(s.confidence*100)}%",
            f"{s.semantic_similarity:.3f}",
            s.hire_recommendation,
            best + alt_flag,
        ])

    rank_table = Table(rank_rows,
                       colWidths=[1*cm, 4.5*cm, 2*cm, 1.8*cm, 2.2*cm, 2.8*cm, 3.7*cm])
    ts = TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("GRID",        (0,0), (-1,-1), 0.3, MID_GREY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT_GREY]),
        ("PADDING",     (0,0), (-1,-1), 6),
        ("ALIGN",       (2,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
    ])
    # Color verdict column per recommendation
    for i, r in enumerate(results, 1):
        c = REC_COLOR.get(r["score"].hire_recommendation, colors.grey)
        ts.add("TEXTCOLOR",  (5, i), (5, i), c)
        ts.add("FONTNAME",   (5, i), (5, i), "Helvetica-Bold")
    rank_table.setStyle(ts)
    elements.append(rank_table)
    elements.append(Paragraph(
        "★ = candidate's highest semantic similarity is to an alternate role, not the primary JD.",
        S["small"]))
    elements.append(Spacer(1, 0.8*cm))

    # ── Per-candidate detailed pages ──────────────────────────────────────────
    elements.append(Paragraph("Detailed Candidate Analysis", S["h2"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=MID_GREY))

    primary_role = jd_structured.get("role_title", "Primary Role")

    for rank, r in enumerate(results, 1):
        s          = r["score"]
        jd_matches = r.get("jd_matches", [])
        audit      = r.get("bias_audit", {})
        rec_color  = REC_COLOR.get(s.hire_recommendation, colors.grey)

        elements.append(Spacer(1, 0.4*cm))

        # Candidate header
        elements.append(Paragraph(
            f"#{rank}  {s.candidate_name}",
            ParagraphStyle("CH", parent=S["h2"], fontSize=13,
                           textColor=rec_color, spaceBefore=6)))
        elements.append(Paragraph(
            f"Verdict: {s.hire_recommendation}  |  Score: {s.weighted_total}/10  |  "
            f"Confidence: {int(s.confidence*100)}%  |  Source: {s.file_name}",
            S["small"]))
        elements.append(Spacer(1, 0.25*cm))

        # ── Dimension scores table ────────────────────────────
        elements.append(Paragraph("Scoring Breakdown", S["h3"]))
        dim_rows = [["Dimension", "Score", "Weight", "Justification"]]
        for dim in s.dimensions:
            dim_rows.append([
                dim.name,
                f"{dim.score}/10",
                f"{int(dim.weight*100)}%",
                dim.justification,
            ])
        dim_table = Table(dim_rows, colWidths=[3.8*cm, 1.8*cm, 1.8*cm, 9.6*cm])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("GRID",        (0,0), (-1,-1), 0.3, MID_GREY),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT_GREY]),
            ("PADDING",     (0,0), (-1,-1), 5),
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ]))
        elements.append(dim_table)
        elements.append(Spacer(1, 0.2*cm))

        # ── Skills ────────────────────────────────────────────
        elements.append(Paragraph(
            f"<b>Matched Skills:</b> {', '.join(s.matched_skills) or 'None detected'}",
            S["body"]))
        elements.append(Paragraph(
            f"<b>Missing Skills:</b> {', '.join(s.missing_skills) or 'None — strong match!'}",
            S["body"]))
        elements.append(Paragraph(
            f"<b>AI Reasoning:</b> {s.shortlist_reasoning}", S["body"]))
        elements.append(Spacer(1, 0.25*cm))

        # ── Multi-JD fit section ──────────────────────────────
        elements.append(Paragraph("Role Fit Analysis — All Open Positions", S["h3"]))

        if jd_matches:
            best_role = jd_matches[0]["role_name"]
            not_primary = (best_role != primary_role)

            if not_primary:
                elements.append(Paragraph(
                    f"⚠  {s.candidate_name} shows LOW fit for the primary role "
                    f"({primary_role}) but is a STRONG match for: {best_role}",
                    ParagraphStyle("Warn", parent=S["body"],
                                   textColor=colors.HexColor("#e67e22"),
                                   fontName="Helvetica-Bold")))
            else:
                elements.append(Paragraph(
                    f"✓  {s.candidate_name} is best suited for the primary role: {primary_role}",
                    ParagraphStyle("Good", parent=S["body"],
                                   textColor=GREEN, fontName="Helvetica-Bold")))

            elements.append(Spacer(1, 0.15*cm))

            # Role match table
            jd_rows_data = [["Rank", "Role", "Similarity Score", "Fit Level"]]
            for idx, match in enumerate(jd_matches):
                sim = match["similarity"]
                fit = "Excellent" if sim > 0.75 else "Good" if sim > 0.55 else "Partial" if sim > 0.35 else "Poor"
                jd_rows_data.append([
                    f"#{idx+1}",
                    match["role_name"],
                    f"{sim:.4f}",
                    fit,
                ])
            jd_match_table = Table(jd_rows_data,
                                   colWidths=[1.5*cm, 6*cm, 4*cm, 5.5*cm])
            jmts = TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), NAVY),
                ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 8),
                ("GRID",        (0,0), (-1,-1), 0.3, MID_GREY),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, LIGHT_GREY]),
                ("PADDING",     (0,0), (-1,-1), 5),
                ("ALIGN",       (2,0), (-1,-1), "CENTER"),
            ])
            # Highlight best-fit row
            jmts.add("BACKGROUND", (0,1), (-1,1), colors.HexColor("#e8f8f5"))
            jmts.add("FONTNAME",   (0,1), (-1,1), "Helvetica-Bold")
            jd_match_table.setStyle(jmts)
            elements.append(jd_match_table)

            # HR recommendation sentence
            elements.append(Spacer(1, 0.15*cm))
            if not_primary:
                elements.append(Paragraph(
                    f"💡 HR Recommendation: Consider {s.candidate_name} for "
                    f"<b>{best_role}</b> instead of {primary_role}. "
                    f"Similarity score {jd_matches[0]['similarity']:.3f} vs primary role.",
                    S["body"]))
        else:
            elements.append(Paragraph("No multi-JD data available.", S["small"]))

        # ── Bias audit ────────────────────────────────────────
        elements.append(Spacer(1, 0.2*cm))
        bias_risk  = audit.get("bias_risk_level", "N/A")
        bias_found = audit.get("bias_detected", False)
        elements.append(Paragraph(
            f"<b>Bias Audit:</b> Risk Level: {bias_risk} | "
            f"Detected: {'Yes — ' + ', '.join(audit.get('bias_types',[])) if bias_found else 'No'}",
            S["body"]))

        elements.append(Spacer(1, 0.3*cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))

    doc.build(elements)
    return output_path