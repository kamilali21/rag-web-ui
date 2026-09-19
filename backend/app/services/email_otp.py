"""Added by ChatGPT: bounded OTP issuance/verification using the existing MySQL tables."""
import hashlib
import hmac
import logging
import math
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage

from fastapi import HTTPException, Request
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.authentication import AuthRateLimit, AuthSession, EmailOTP
from app.models.user import User
from app.services.authorization import normalize_email
from app.services.auth_sessions import check_configuration, client_address

logger = logging.getLogger(__name__)
INVALID_CODE = "Invalid or expired code"


def keyed_hash(value: str) -> str:
    return hmac.new(settings.AUTH_OTP_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def send_code(email: str, code: str):
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL or settings.SMTP_SECURITY not in {"starttls", "ssl"}:
        raise HTTPException(503, "Email delivery is not configured")
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message["Subject"] = "Your ResearchIQ verification code"
    message.set_content(f"Your ResearchIQ verification code is {code}.\n\n"
                        f"It expires in {settings.OTP_TTL_SECONDS // 60} minutes. "
                        "If you did not request this code, you can ignore this email.")
    context = ssl.create_default_context()
    smtp_class = smtplib.SMTP_SSL if settings.SMTP_SECURITY == "ssl" else smtplib.SMTP
    kwargs = {"timeout": settings.SMTP_TIMEOUT_SECONDS}
    if settings.SMTP_SECURITY == "ssl":
        kwargs["context"] = context
    with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, **kwargs) as smtp:
        if settings.SMTP_SECURITY == "starttls":
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        if smtp.send_message(message):
            raise smtplib.SMTPException("Recipient rejected")


def lock_limits(db: Session, email: str, address: str, action: str):
    """Lock keys in one order across workers; the email mutex also serializes resends/verifications."""
    now = datetime.utcnow()
    ip_key = keyed_hash(f"{action}:ip:{address}")
    keys = {keyed_hash(f"state:{email}"): None,
            keyed_hash(f"{action}:email:{email}"): 5 if action == "send" else 20,
            ip_key: 30 if action == "send" else 60}
    rows = {}
    # Added by ChatGPT: reject blocked IPs before allocating rows for arbitrary new emails.
    # Every request locks one IP first, then email keys in the same sorted order.
    for key in [ip_key, *sorted(k for k in keys if k != ip_key)]:
        values = dict(key_hash=key, window_started_at=now, request_count=0,
                      expires_at=now + timedelta(days=1))
        # Added by ChatGPT: exclusive upsert locks avoid duplicate-insert lock upgrades on MySQL.
        if db.bind.dialect.name == "mysql":
            statement = mysql_insert(AuthRateLimit).values(**values).on_duplicate_key_update(key_hash=key)
        else:
            statement = sqlite_insert(AuthRateLimit).values(**values).on_conflict_do_nothing(index_elements=["key_hash"])
        db.execute(statement)
        row = db.query(AuthRateLimit).filter_by(key_hash=key).populate_existing().with_for_update().one()
        rows[key] = row
        row.expires_at = now + timedelta(days=1)
        maximum = keys[key]
        if maximum is None:
            continue
        if row.window_started_at + timedelta(minutes=15) <= now:
            row.window_started_at, row.request_count = now, 0
        row.request_count += 1
        if row.request_count > maximum:
            db.commit()
            raise HTTPException(429, "Too many attempts. Please try again later.", headers={"Retry-After": "900"})
    return rows[keyed_hash(f"state:{email}")]


def request_code(db: Session, email: str, request: Request, purpose: str = "verify_email"):
    check_configuration()
    email = normalize_email(email)
    state = lock_limits(db, email, client_address(request), "send")
    now = datetime.utcnow()
    if state.blocked_until and state.blocked_until > now:
        wait = max(1, math.ceil((state.blocked_until - now).total_seconds()))
        db.commit()
        raise HTTPException(429, "Please wait before requesting another code", headers={"Retry-After": str(wait)})
    # Added by ChatGPT: match MySQL DATETIME precision instead of rounding into an extra second.
    state.blocked_until = now.replace(microsecond=0) + timedelta(seconds=settings.OTP_RESEND_SECONDS)
    result = {"message": "If this registered account is eligible, a code has been sent.",
              "retry_after": settings.OTP_RESEND_SECONDS}
    # Added by ChatGPT: no implicit registration, including accent-equivalent MySQL identities.
    user = db.query(User).filter(User.email == email).first()
    if (not user or normalize_email(user.email) != email or not user.is_active or user.is_system
            or (purpose == "verify_email" and (user.email_verified_at is not None or not user.hashed_password))):
        db.commit()
        return result
    db.query(EmailOTP).filter(EmailOTP.email == email, EmailOTP.purpose == purpose, EmailOTP.used_at.is_(None)).update(
        {EmailOTP.used_at: now}, synchronize_session=False)
    code = f"{secrets.randbelow(1000000):06d}"
    otp = EmailOTP(email=email, otp_hash="", expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
                   delivery_status="pending", purpose=purpose, attempt_count=0)
    db.add(otp)
    db.flush()
    otp.otp_hash = keyed_hash(f"otp:{otp.id}:{email}:{code}")
    otp_id = otp.id
    db.commit()
    # SMTP never holds the shared rate-limit locks; pending challenges cannot authenticate.
    try:
        send_code(email, code)
    except Exception as error:
        db.query(EmailOTP).filter_by(id=otp_id).update({EmailOTP.delivery_status: "failed"})
        db.commit()
        logger.warning("OTP mail delivery failed (%s)", type(error).__name__)
        raise HTTPException(503, "Email delivery is temporarily unavailable. Please try again later.") from None
    db.query(EmailOTP).filter_by(id=otp_id).update({EmailOTP.delivery_status: "sent"})
    db.commit()
    return result


def verify_code(db: Session, email: str, code: str, request: Request, password: str,
                purpose: str = "verify_email"):
    # Added by ChatGPT: import locally to avoid the existing security/session dependency cycle.
    from app.core.security import get_password_hash, validate_new_password, verify_password
    check_configuration()
    if purpose == "reset_password":
        validate_new_password(password)
    email = normalize_email(email)
    lock_limits(db, email, client_address(request), "verify")
    now = datetime.utcnow()
    otp = db.query(EmailOTP).filter(EmailOTP.email == email, EmailOTP.purpose == purpose,
        EmailOTP.used_at.is_(None), EmailOTP.delivery_status == "sent").order_by(EmailOTP.id.desc()).with_for_update().first()
    if otp is None or otp.expires_at <= now or otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
        db.commit()
        raise HTTPException(400, INVALID_CODE)
    otp.attempt_count += 1
    if not hmac.compare_digest(otp.otp_hash, keyed_hash(f"otp:{otp.id}:{email}:{code}")):
        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            otp.used_at = now
        db.commit()
        raise HTTPException(400, INVALID_CODE)
    user = db.query(User).filter(User.email == email).first()
    if (not user or normalize_email(user.email) != email or not user.is_active or user.is_system
            or (purpose == "verify_email" and not verify_password(password, user.hashed_password))):
        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            otp.used_at = now
        db.commit()
        raise HTTPException(400, INVALID_CODE)
    otp.used_at = now
    user.email_verified_at = user.email_verified_at or now
    if purpose == "reset_password":
        user.hashed_password = get_password_hash(password)
        db.query(AuthSession).filter_by(user_id=user.id).update({AuthSession.revoked_at: now})
        # A reset also invalidates outstanding verification codes for the old password.
        db.query(EmailOTP).filter(EmailOTP.email == email, EmailOTP.used_at.is_(None)).update(
            {EmailOTP.used_at: now}, synchronize_session=False)
    db.commit()
    return {"message": "Password saved. Sign in with your password." if purpose == "reset_password"
            else "Email verified. Sign in with your password."}
