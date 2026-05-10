from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import json, re

llm = ChatGroq(model=settings.model_name, api_key=settings.groq_api_key, temperature=0)

BIAS_SYSTEM_PROMPT = """You are a fairness auditor for AI hiring systems.
Review the scoring rationale and detect any potential bias.
Return ONLY valid JSON:
{
  "bias_detected": boolean,
  "bias_types": ["list of bias types if any, e.g. gender, age, name, institution"],
  "bias_risk_level": "LOW|MEDIUM|HIGH",
  "recommendations": ["list of recommendations"],
  "fair_scoring_confidence": number 0-1
}"""

def audit_for_bias(scoring_rationale: str, candidate_name: str) -> dict:
    response = llm.invoke([
        SystemMessage(content=BIAS_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Candidate Name: {candidate_name}
Scoring Rationale: {scoring_rationale}
Check for any demographic bias in this scoring.
""")
    ])
    text = response.content.strip()
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)