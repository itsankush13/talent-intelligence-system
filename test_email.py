import smtplib, os
from dotenv import load_dotenv

load_dotenv("/Users/ankushsaxena/talent-intelligence-system/.env")

email = os.getenv("SENDER_EMAIL", "")
password = os.getenv("SENDER_PASSWORD", "")

print(f"EMAIL: {email}")
print(f"PASSWORD SET: {'yes' if password else 'NO - check .env'}")

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(email, password)
        print("✅ Gmail login works!")
except Exception as e:
    print(f"❌ Failed: {e}")
