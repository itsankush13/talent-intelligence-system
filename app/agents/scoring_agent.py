from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.models.candidate import CandidateProfile, CandidateScore, ScoringDimension
import json, re

llm = ChatGroq(model=settings.model_name, api_key=settings.groq_api_key, temperature=0)

SCORE_SYSTEM_PROMPT = """You are an expert technical recruiter. Score a candidate against a job description.

Return ONLY valid JSON with these exact dimension scores (0-10 each) and one-line justifications:
{
  "skills_match": {"score": number, "justification": "string"},
  "experience_relevance": {"score": number, "justification": "string"},
  "education_certs": {"score": number, "justification": "string"},
  "project_portfolio": {"score": number, "justification": "string"},
  "communication_quality": {"score": number, "justification": "string"},
  "matched_skills": ["list of matched skills"],
  "missing_skills": ["list of missing required skills"],
  "shortlist_reasoning": "2-3 sentence overall assessment",
  "llm_confidence": number between 0 and 1
}

Weights: skills_match=30%, experience_relevance=25%, education_certs=15%, project_portfolio=20%, communication_quality=10%
Be strict and objective. Base scores ONLY on evidence in the resume."""

def score_candidate(
    candidate: CandidateProfile,
    jd_structured: dict,
    semantic_similarity: float = 0.0,
    bm25_score: float = 0.0,
) -> CandidateScore:
    
    prompt = f"""
JOB REQUIREMENTS:
{json.dumps(jd_structured, indent=2)}

CANDIDATE PROFILE:
Name: {candidate.name}
Experience: {candidate.experience_years} years
Education: {candidate.education}
Skills: {', '.join(candidate.skills)}
Projects: {'; '.join(candidate.projects[:3])}
Certifications: {', '.join(candidate.certifications)}

Resume Sections:
{candidate.segmented_sections.get('experience', '')[:2000]}
"""
    
    response = llm.invoke([
        SystemMessage(content=SCORE_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    
    text = response.content.strip()
    text = re.sub(r"```json|```", "", text).strip()
    scored = json.loads(text)

    weights = {
        "skills_match": 0.30,
        "experience_relevance": 0.25,
        "education_certs": 0.15,
        "project_portfolio": 0.20,
        "communication_quality": 0.10,
    }
    
    dimensions = []
    weighted_total = 0.0
    for key, weight in weights.items():
        dim_data = scored.get(key, {"score": 0, "justification": "Not evaluated"})
        s = float(dim_data["score"])
        dimensions.append(ScoringDimension(
            name=key.replace("_", " ").title(),
            score=s,
            weight=weight,
            justification=dim_data["justification"]
        ))
        weighted_total += s * weight

    # Ensemble score: combine LLM + semantic + BM25
    # Normalize bm25 to 0-10 range (cap at 50 raw score)
    bm25_normalized = min(bm25_score / 5.0, 10.0)
    semantic_score = semantic_similarity * 10  # 0-1 → 0-10
    
    ensemble_score = (
        0.50 * weighted_total +
        0.30 * semantic_score +
        0.20 * bm25_normalized
    )
    
    # Confidence = average of LLM confidence + extraction completeness
    extraction_completeness = min(len(candidate.skills) / 10.0, 1.0)
    confidence = (scored.get("llm_confidence", 0.7) + extraction_completeness) / 2
    
    # Hire recommendation
    if ensemble_score >= 7.5:
        rec = "STRONG HIRE"
    elif ensemble_score >= 6.0:
        rec = "HIRE"
    elif ensemble_score >= 4.5:
        rec = "MAYBE"
    else:
        rec = "NO HIRE"

    matched_skills = scored.get("matched_skills", [])
    missing_skills = scored.get("missing_skills", [])

    # Hiring match % — calculated BEFORE building the object
    skill_coverage = len(matched_skills) / max(
        len(jd_structured.get("required_skills", [])), 1)
    hiring_match = (
        0.5 * semantic_similarity +
        0.3 * skill_coverage +
        0.2 * (ensemble_score / 10)
    ) * 100

    return CandidateScore(
        candidate_name=candidate.name,
        file_name="",
        dimensions=dimensions,
        weighted_total=round(ensemble_score, 2),
        confidence=round(confidence, 2),
        hire_recommendation=rec,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        semantic_similarity=round(semantic_similarity, 3),
        bm25_score=round(bm25_score, 2),
        bias_masked=True,
        shortlist_reasoning=scored.get("shortlist_reasoning", ""),
        hiring_match_pct=round(min(hiring_match, 100), 1),
    )