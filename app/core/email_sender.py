import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
import re

llm = ChatGroq(model=settings.model_name, api_key=settings.groq_api_key, temperature=0.7)


def generate_rejection_email(candidate_name: str, role: str, company: str = "Our Company") -> str:
    response = llm.invoke([
        SystemMessage(content="""You write professional, warm, and respectful rejection emails 
        for job candidates. Be empathetic, brief (3 short paragraphs), and encouraging. 
        Do NOT use placeholders — write the full email body only, no subject line."""),
        HumanMessage(content=f"""
Write a rejection email for:
- Candidate: {candidate_name}
- Role applied for: {role}  
- Company: {company}
The tone should be warm but clear. Thank them, inform them of the decision, 
wish them well. Keep it under 120 words.""")
    ])
    return response.content.strip()


def generate_selection_email(candidate_name: str, role: str,
                              hr_notes: str = "", company: str = "Our Company") -> str:
    response = llm.invoke([
        SystemMessage(content="""You write professional, enthusiastic selection/interview 
        invitation emails for job candidates. Be warm, clear, and exciting.
        Write the full email body only, no subject line. Under 150 words."""),
        HumanMessage(content=f"""
Write a selection/next-steps email for:
- Candidate: {candidate_name}
- Role: {role}
- Company: {company}
- HR's personal notes to include: {hr_notes or 'None — keep it general'}
Congratulate them, mention next steps (interview scheduling), 
express genuine excitement about their profile.""")
    ])
    return response.content.strip()


def send_email(to_address: str, subject: str, body: str,
               smtp_host: str, smtp_port: int,
               sender_email: str, sender_password: str) -> tuple[bool, str]:
    """Send email via SMTP. Returns (success, message)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = sender_email
        msg["To"]      = to_address

        # Plain text + basic HTML version
        html_body = body.replace("\n", "<br>")
        html = f"""
        <html><body style="font-family: Arial, sans-serif; line-height: 1.6; 
                           color: #333; max-width: 600px; margin: auto; padding: 20px;">
            <p>{html_body}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                This email was sent via Talent Intelligence System.
            </p>
        </body></html>"""

        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html,  "html"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_address, msg.as_string())

        return True, f"Email sent to {to_address}"
    except Exception as e:
        return False, str(e)