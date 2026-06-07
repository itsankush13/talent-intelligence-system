import smtplib, os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv("/Users/ankushsaxena/talent-intelligence-system/.env")

email = os.getenv("SENDER_EMAIL")
password = os.getenv("SENDER_PASSWORD")

# Send test OTP to yourself
test_otp = "123456"
recipient = email  # sending to yourself as a test

msg = MIMEMultipart("alternative")
msg["Subject"] = "Test OTP - TechXdigisolutions"
msg["From"] = email
msg["To"] = recipient
msg.attach(MIMEText(f"Your test OTP is: {test_otp}", "plain"))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(email, password)
        s.sendmail(email, recipient, msg.as_string())
        print(f"✅ Test email sent to {recipient} — check your inbox!")
except Exception as e:
    print(f"❌ Send failed: {e}")
