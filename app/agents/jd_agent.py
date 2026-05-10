from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.security import sanitize_input
import json, re

llm = ChatGroq(model=settings.model_name, api_key=settings.groq_api_key, temperature=0)

JD_SYSTEM_PROMPT = """You are an expert HR analyst. Extract structured hiring requirements from a Job Description.
Return ONLY valid JSON. No markdown, no explanation.

JSON structure:
{
  "role_title": "string",
  "required_skills": ["list of skills"],
  "preferred_skills": ["list of skills"],
  "min_experience_years": number,
  "education_requirement": "string",
  "key_responsibilities": ["list"],
  "seniority_level": "Junior|Mid|Senior|Lead|Principal"
}"""

def parse_jd(jd_text: str) -> dict:
    clean_text, warnings = sanitize_input(jd_text)
    if warnings:
        print(f"[Security] JD warnings: {warnings}")

    response = llm.invoke([
        SystemMessage(content=JD_SYSTEM_PROMPT),
        HumanMessage(content=f"Job Description:\n{clean_text}")
    ])
    
    text = response.content.strip()
    # Strip markdown fences if present
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)