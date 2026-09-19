"""Added by ChatGPT: opaque, revocable browser sessions with bound CSRF tokens."""
import hashlib
import hmac
import ipaddress
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.authentication import AuthSession
from app.services.authorization import require_active_user
from app.models.user import User

SESSION_COOKIE = "__Host-researchiq_session"
CSRF_COOKIE = "__Host-researchiq_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def check_configuration():
    try:
        origin = urlsplit(settings.AUTH_ORIGIN)
        # Added by ChatGPT: never allow the local exception on a public hostname.
        local = origin.hostname in {"localhost", "127.0.0.1", "127.0.0.1.nip.io", "::1"}
        valid = (origin.scheme == "https" or
                 (settings.AUTH_ALLOW_LOCAL_HTTP and local and origin.scheme == "http"))
        valid = valid and origin.hostname and not (origin.username or origin.password or
                    origin.path or origin.query or origin.fragment)
        origin.port  # Validate malformed ports before processing a request.
    except ValueError:
        valid = False
    if not settings.EMAIL_OTP_ENABLED or len(settings.AUTH_OTP_SECRET) < 32 or not valid:
        raise HTTPException(503, "Email sign-in is not configured")


def cookie_names():
    # Added by ChatGPT: __Host- cookies require Secure; HTTP development uses distinct names.
    if settings.AUTH_ALLOW_LOCAL_HTTP and settings.AUTH_ORIGIN.startswith("http://"):
        return "researchiq_local_session", "researchiq_local_csrf"
    return SESSION_COOKIE, CSRF_COOKIE


def require_origin(request: Request):
    check_configuration()
    if request.headers.get("origin") != settings.AUTH_ORIGIN:
        raise HTTPException(403, "Request origin is not allowed")


def client_address(request: Request) -> str:
    # Forwarded addresses are accepted only from explicitly configured proxy peers.
    peer = request.client.host if request.client else "unknown"
    try:
        trusted = any(ipaddress.ip_address(peer) in ipaddress.ip_network(network)
                      for network in settings.AUTH_TRUSTED_PROXIES)
        if trusted and request.headers.get("x-real-ip"):
            return str(ipaddress.ip_address(request.headers["x-real-ip"]))
    except ValueError:
        pass
    return peer


def find_session(db: Session, request: Request):
    token = request.cookies.get(cookie_names()[0], "")
    if not 32 <= len(token) <= 128:
        return None
    return db.query(AuthSession).filter(
        AuthSession.token_hash == digest(token), AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > datetime.utcnow()
    ).first()


def require_csrf(request: Request, session: AuthSession):
    # Added by ChatGPT: logout uses the same protection even after an account is disabled.
    if request.method not in SAFE_METHODS:
        require_origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not 32 <= len(csrf) <= 128 or not hmac.compare_digest(digest(csrf), session.csrf_token_hash):
            raise HTTPException(403, "Invalid CSRF token")


def authenticate_session(db: Session, request: Request) -> User:
    check_configuration()
    session = find_session(db, request)
    if session is None:
        raise HTTPException(401, "Session expired or unavailable")
    require_csrf(request, session)
    user = require_active_user(db.get(User, session.user_id))
    return user


def create_session(db: Session, user: User, request: Request):
    require_active_user(user)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    # Rotation revokes only the session presented by this browser, not other devices.
    old = find_session(db, request)
    if old is not None:
        old.revoked_at = datetime.utcnow()
    db.add(AuthSession(user_id=user.id, token_hash=digest(token), csrf_token_hash=digest(csrf),
                       expires_at=datetime.utcnow() + timedelta(seconds=settings.SESSION_TTL_SECONDS)))
    return token, csrf


def set_session_cookies(response: Response, token: str, csrf: str):
    session_name, csrf_name = cookie_names()
    secure = session_name == SESSION_COOKIE
    for name, value, http_only in [(session_name, token, True), (csrf_name, csrf, False)]:
        response.set_cookie(name, value, max_age=settings.SESSION_TTL_SECONDS,
                            httponly=http_only, secure=secure, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookies(response: Response):
    # Added by ChatGPT: also clear stale local-mode cookies during a deliberate rollout rollback.
    for name, http_only, secure in [(SESSION_COOKIE, True, True), (CSRF_COOKIE, False, True),
                                   ("researchiq_local_session", True, False), ("researchiq_local_csrf", False, False)]:
        response.delete_cookie(name, path="/", secure=secure, httponly=http_only, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
