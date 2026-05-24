import sqlite3
import secrets
import hashlib
import random
from datetime import datetime, timedelta
from manage_tenants import get_db, init_db, log_action, DB_PATH

# ── OTP via Twilio (phone) ─────────────────────────────────────────────────
def send_phone_otp(phone: str) -> bool:
    """Send OTP via Twilio SMS."""
    try:
        from twilio.rest import Client
        import os
        client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
        otp = str(random.randint(100000, 999999))
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        expires  = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        init_db()
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO otp_store (phone_or_email, otp_hash, expires_at, attempts)
            VALUES (?, ?, ?, 0)
        """, (phone, otp_hash, expires))
        conn.commit()
        conn.close()

        client.messages.create(
            body=f"Your Talent Intelligence System OTP is: {otp}\nValid for 10 minutes.",
            from_=os.getenv("TWILIO_PHONE"),
            to=phone
        )
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        # Fallback: print OTP to console (for testing without Twilio)
        _store_otp_console(phone)
        return True

def _store_otp_console(identifier: str) -> str:
    """Fallback — store OTP and print to console for testing."""
    otp = str(random.randint(100000, 999999))
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires  = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    init_db()
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO otp_store (phone_or_email, otp_hash, expires_at, attempts)
        VALUES (?, ?, ?, 0)
    """, (identifier, otp_hash, expires))
    conn.commit()
    conn.close()
    print(f"\n🔑 OTP for {identifier}: {otp}  (valid 10 min)\n")
    return otp

# ── OTP via Email ──────────────────────────────────────────────────────────
def send_email_otp(email: str) -> bool:
    """Send OTP via email using SMTP."""
    import smtplib, os
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    otp = str(random.randint(100000, 999999))
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    expires  = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    init_db()
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO otp_store (phone_or_email, otp_hash, expires_at, attempts)
        VALUES (?, ?, ?, 0)
    """, (email, otp_hash, expires))
    conn.commit()
    conn.close()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your Talent Intelligence System Login OTP"
        msg["From"]    = os.getenv("SENDER_EMAIL", "")
        msg["To"]      = email
        html = f"""
        <html><body style="font-family:Arial,sans-serif;padding:20px;">
            <h2 style="color:#6366f1;">Talent Intelligence System</h2>
            <p>Your login OTP is:</p>
            <div style="font-size:2.5rem;font-weight:bold;color:#6366f1;
                        letter-spacing:8px;padding:20px;background:#f1f5f9;
                        border-radius:8px;text-align:center;">{otp}</div>
            <p style="color:#666;margin-top:20px;">Valid for 10 minutes. Do not share this with anyone.</p>
        </body></html>"""
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL(
            os.getenv("SMTP_HOST", "smtp.gmail.com"),
            int(os.getenv("SMTP_PORT", 465))
        ) as server:
            server.login(os.getenv("SENDER_EMAIL"), os.getenv("SENDER_PASSWORD"))
            server.sendmail(os.getenv("SENDER_EMAIL"), email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email OTP error: {e}")
        print(f"\n🔑 EMAIL OTP for {email}: {otp}  (valid 10 min)\n")
        return True

# ── Verify OTP ─────────────────────────────────────────────────────────────
def verify_otp(identifier: str, entered_otp: str) -> tuple[bool, str]:
    """Returns (success, error_message)."""
    init_db()
    conn = get_db()
    row = conn.execute("""
        SELECT otp_hash, expires_at, attempts
        FROM otp_store WHERE phone_or_email = ?
    """, (identifier,)).fetchone()

    if not row:
        conn.close()
        return False, "No OTP found. Please request a new one."

    if row["attempts"] >= 5:
        conn.close()
        return False, "Too many attempts. Please request a new OTP."

    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.close()
        return False, "OTP expired. Please request a new one."

    entered_hash = hashlib.sha256(entered_otp.encode()).hexdigest()
    if entered_hash != row["otp_hash"]:
        conn.execute("""
            UPDATE otp_store SET attempts = attempts + 1
            WHERE phone_or_email = ?
        """, (identifier,))
        conn.commit()
        conn.close()
        remaining = 4 - row["attempts"]
        return False, f"Wrong OTP. {remaining} attempts remaining."

    # OTP correct — delete it so it can't be reused
    conn.execute("DELETE FROM otp_store WHERE phone_or_email = ?", (identifier,))
    conn.commit()
    conn.close()
    return True, ""

# ── Session management ─────────────────────────────────────────────────────
def create_session(tenant_id: str) -> str:
    """Create a session token after successful login."""
    token   = secrets.token_urlsafe(48)
    expires = (datetime.utcnow() + timedelta(hours=8)).isoformat()

    init_db()
    conn = get_db()
    conn.execute("""
        INSERT INTO sessions (session_token, tenant_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """, (token, tenant_id, datetime.utcnow().isoformat(), expires))
    conn.commit()
    conn.close()
    return token

def validate_session(token: str) -> dict | None:
    """Returns tenant info if session is valid."""
    if not token:
        return None
    init_db()
    conn = get_db()
    row = conn.execute("""
        SELECT s.tenant_id, s.expires_at,
               t.company_name, t.hr_name, t.plan,
               t.is_active, t.is_paid, t.resumes_used,
               t.resumes_limit, t.expires_at as sub_expires
        FROM sessions s
        JOIN tenants t ON s.tenant_id = t.id
        WHERE s.session_token = ?
    """, (token,)).fetchone()
    conn.close()

    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        return None
    if not row["is_active"]:
        return None
    if datetime.fromisoformat(row["sub_expires"]) < datetime.utcnow():
        return None

    return dict(row)

def get_tenant_by_identifier(identifier: str) -> dict | None:
    """Find tenant by phone or email."""
    init_db()
    conn = get_db()
    row = conn.execute("""
        SELECT * FROM tenants
        WHERE phone = ? OR email = ?
    """, (identifier, identifier)).fetchone()
    conn.close()
    return dict(row) if row else None