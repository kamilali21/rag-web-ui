"""Added by ChatGPT: OTP/session HTTP tests; isolated SQLite or the Phase 2 disposable MySQL fixture."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.authentication import AuthRateLimit, AuthSession, EmailOTP
from app.models import AdminAllowlist, User
from app.services import auth_sessions, email_otp
from tests.test_phase2_authorization import world
from tests import test_phase2_authorization as phase2


@pytest.fixture
def otp(world, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_OTP_ENABLED", True)
    monkeypatch.setattr(settings, "AUTH_ORIGIN", "https://testserver")
    monkeypatch.setattr(settings, "AUTH_LOCAL_ORIGIN", "")
    monkeypatch.setattr(settings, "AUTH_ALLOW_LOCAL_HTTP", False)
    monkeypatch.setattr(settings, "AUTH_OTP_SECRET", "phase3-test-secret-not-for-deployment" * 2)
    monkeypatch.setattr(settings, "AUTH_TRUSTED_PROXIES", [])
    world.client.base_url = "https://testserver"
    world.client.headers["Origin"] = settings.AUTH_ORIGIN
    mail = []
    monkeypatch.setattr(email_otp, "send_code", lambda email, code: mail.append((email, code)))
    world.mail = mail
    return world


def send(w, email=None):
    email = email or w.alice.email
    result = w.client.post("/api/auth/request-otp", json={"email": email})
    assert result.status_code == 200, result.text
    return w.mail[-1][1]


def verify(w, code, email=None):
    return w.client.post("/api/auth/verify-otp", json={"email": email or w.alice.email, "code": code,
                                                     "password": "phase2-test-password"})


def login(w, email=None):
    email = email or w.alice.email
    w.db.rollback()
    w.db.expire_all()
    user = w.db.query(User).filter_by(email=email).one()
    if user.email_verified_at is None:
        assert verify(w, send(w, email), email).status_code == 200
    result = w.client.post("/api/auth/token", data={"username": email, "password": "phase2-test-password"})
    assert result.status_code == 200, result.text
    # Added by ChatGPT: end the inspector's snapshot after independent HTTP commits.
    w.db.rollback()
    return result


def csrf(w):
    return {"X-CSRF-Token": w.client.cookies.get(auth_sessions.cookie_names()[1])}


def release_cooldown(w, email=None):
    state = w.db.get(AuthRateLimit, email_otp.keyed_hash(f"state:{email or w.alice.email}"))
    state.blocked_until = datetime.utcnow() - timedelta(seconds=1)
    w.db.commit()


def test_hashed_codes_secure_cookies_me_and_single_use(otp):
    w = otp
    code = send(w, "  ALICE@uaf.edu.pk  ")
    row = w.db.query(EmailOTP).one()
    assert row.otp_hash == email_otp.keyed_hash(f"otp:{row.id}:{w.alice.email}:{code}")
    result = verify(w, code)
    assert result.status_code == 200
    assert not result.headers.get_list("set-cookie")
    assert w.client.get("/api/auth/me").status_code == 401
    result = login(w)
    cookies = result.headers.get_list("set-cookie")
    assert all("Secure" in c and "SameSite=lax" in c and "Path=/" in c for c in cookies)
    assert "HttpOnly" in cookies[0] and "HttpOnly" not in cookies[1]
    assert all("Domain=" not in c for c in cookies)
    assert "token" not in result.json() and "hashed_password" not in result.json()
    # End the inspector's repeatable-read snapshot after the separate HTTP transaction.
    w.db.rollback()
    session = w.db.query(AuthSession).one()
    assert session.token_hash == auth_sessions.digest(w.client.cookies.get(auth_sessions.SESSION_COOKIE))
    assert session.csrf_token_hash == auth_sessions.digest(w.client.cookies.get(auth_sessions.CSRF_COOKIE))
    assert w.client.get("/api/auth/me").json()["roles"] == ["researcher"]
    assert verify(w, code).status_code == 400
    assert w.db.query(AuthSession).count() == 1


def test_new_university_or_allowlisted_email_is_only_researcher(otp):
    w = otp
    email = "new-professor@uaf.edu.pk"
    w.db.add(AdminAllowlist(email=email, is_active=True)); w.db.commit()
    result = w.client.post("/api/auth/register", json={"username": "new-professor", "email": email,
                            "password": "NewPassword123", "is_superuser": True})
    assert result.status_code == 200
    code = send(w, email)
    assert w.client.post("/api/auth/verify-otp", json={"email": email, "code": code,
                                                     "password": "NewPassword123"}).status_code == 200
    assert w.client.post("/api/auth/token", data={"username": email, "password": "NewPassword123"}).status_code == 200
    user = w.db.query(User).filter_by(email=email).one()
    assert user.hashed_password is not None and not user.is_superuser
    assert [r.name for r in user.roles] == ["researcher"]
    assert w.client.get("/test/admin").status_code == 403


def test_existing_admin_preserved_but_private_documents_stay_private(otp):
    w = otp
    login(w, w.professor.email)
    assert w.client.get("/test/admin").status_code == 200
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}").status_code == 404
    assert w.client.get(f"/api/knowledge-base/{w.bob_kb.id}/documents/{w.bob_doc.id}").status_code == 404
    entry = w.db.query(AdminAllowlist).filter_by(email=w.professor.email).one()
    entry.is_active = False; w.db.commit()
    assert w.client.get("/test/admin").status_code == 403


@pytest.mark.parametrize("actor", ["inactive", "system"])
def test_inactive_and_system_cannot_sign_in(otp, actor):
    w = otp
    email = getattr(w, actor).email
    assert w.client.post("/api/auth/request-otp", json={"email": email}).status_code == 200
    assert not w.mail
    assert verify(w, "123456", email).status_code == 400
    assert w.db.query(AuthSession).count() == 0


def test_csrf_origin_logout_and_revocation(otp):
    w = otp
    login(w)
    token = w.client.cookies.get(auth_sessions.SESSION_COOKIE)
    # Valid Bearer does not bypass cookie CSRF requirements after cutover.
    assert w.client.post("/api/auth/logout", headers=w.headers(w.alice)).status_code == 403
    assert w.client.post("/api/auth/logout", headers={**csrf(w), "Origin": "https://evil.example"}).status_code == 403
    assert w.client.post("/api/auth/logout", headers={"X-CSRF-Token": "x" * 43}).status_code == 403
    assert w.client.post("/api/auth/logout", headers=csrf(w)).status_code == 200
    assert not w.client.cookies
    w.client.cookies.set(auth_sessions.SESSION_COOKIE, token)
    assert w.client.get("/api/auth/me").status_code == 401
    w.db.rollback()
    w.db.expire_all()
    assert w.db.query(AuthSession).one().revoked_at is not None


def test_disabled_account_can_still_revoke_its_session(otp):
    w = otp
    login(w)
    w.alice.is_active = False
    w.db.commit()
    assert w.client.get("/api/auth/me").status_code == 401
    assert w.client.post("/api/auth/logout").status_code == 403
    assert w.client.post("/api/auth/logout", headers=csrf(w)).status_code == 200
    assert not w.client.cookies
    assert w.db.query(AuthSession).one().revoked_at is not None


@pytest.mark.parametrize("change", ["expired", "inactive", "revoked"])
def test_session_current_state_checked_each_request(otp, change):
    w = otp
    login(w)
    row = w.db.query(AuthSession).one()
    if change == "expired": row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    elif change == "inactive": w.alice.is_active = False
    else: row.revoked_at = datetime.utcnow()
    w.db.commit()
    assert w.client.get("/api/auth/me").status_code == 401


def test_rotation_and_old_csrf_rejected(otp):
    w = otp
    login(w)
    old_token, old_csrf = w.client.cookies.get(auth_sessions.SESSION_COOKIE), csrf(w)
    release_cooldown(w)
    login(w)
    assert w.client.cookies.get(auth_sessions.SESSION_COOKIE) != old_token
    assert w.client.post("/api/auth/logout", headers=old_csrf).status_code == 403
    assert w.db.query(AuthSession).filter(AuthSession.revoked_at.isnot(None)).count() == 1


def test_wrong_attempts_exhaust_code_and_expired_code_fails(otp):
    w = otp
    code = send(w)
    wrong = "000001" if code == "000000" else "000000"
    for _ in range(settings.OTP_MAX_ATTEMPTS): assert verify(w, wrong).status_code == 400
    assert verify(w, code).status_code == 400
    w.db.expire_all()
    assert w.db.query(EmailOTP).one().attempt_count == settings.OTP_MAX_ATTEMPTS
    release_cooldown(w)
    code = send(w)
    row = w.db.query(EmailOTP).order_by(EmailOTP.id.desc()).first()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1); w.db.commit()
    assert verify(w, code).status_code == 400


def test_resend_cooldown_and_replacement(otp):
    w = otp
    old = send(w)
    response = w.client.post("/api/auth/request-otp", json={"email": w.alice.email})
    assert response.status_code == 429 and 0 < int(response.headers["Retry-After"]) <= 60
    assert len(w.mail) == 1
    release_cooldown(w)
    new = send(w)
    w.db.expire_all()
    assert w.db.query(EmailOTP).order_by(EmailOTP.id).first().used_at is not None
    if new != old: assert verify(w, old).status_code == 400
    assert verify(w, new).status_code == 200


def test_resend_retry_after_at_exact_second_boundary(otp, monkeypatch):
    instant = datetime.utcnow().replace(microsecond=0)
    class FrozenTime(datetime):
        @classmethod
        def utcnow(cls):
            return instant
    monkeypatch.setattr(email_otp, "datetime", FrozenTime)
    send(otp)
    response = otp.client.post("/api/auth/request-otp", json={"email": otp.alice.email})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == str(settings.OTP_RESEND_SECONDS)


def test_email_and_ip_send_limits_and_window_reset(otp):
    w = otp
    send(w)
    for _ in range(4):
        release_cooldown(w); send(w)
    release_cooldown(w)
    assert w.client.post("/api/auth/request-otp", json={"email": w.alice.email}).status_code == 429
    for n in range(24):
        assert w.client.post("/api/auth/request-otp", json={"email": f"different{n}@example.com"}).status_code == 200
    count = w.db.query(AuthRateLimit).count()
    w.db.rollback()
    assert w.client.post("/api/auth/request-otp", json={"email": "over-ip@example.com"}).status_code == 429
    assert w.db.query(AuthRateLimit).count() == count
    for row in w.db.query(AuthRateLimit).all():
        row.window_started_at = datetime.utcnow() - timedelta(minutes=16)
        row.blocked_until = None
    w.db.commit()
    send(w)


def test_verification_rate_limits_survive_missing_codes(otp):
    w = otp
    for _ in range(20): assert verify(w, "000000").status_code == 400
    assert verify(w, "000000").status_code == 429
    for n in range(39): assert verify(w, "000000", f"n{n}@example.com").status_code == 400
    assert verify(w, "000000", "limit@example.com").status_code == 429


def test_smtp_failure_no_secret_logging_no_usable_challenge(otp, monkeypatch, caplog):
    w = otp
    def fail(email, code):
        w.mail.append((email, code))
        raise RuntimeError(f"secret {code} smtp-password")
    monkeypatch.setattr(email_otp, "send_code", fail)
    result = w.client.post("/api/auth/request-otp", json={"email": w.alice.email})
    assert result.status_code == 503
    code = w.mail[-1][1]
    assert code not in caplog.text and "smtp-password" not in caplog.text
    assert w.db.query(EmailOTP).one().delivery_status == "failed"
    assert verify(w, code).status_code == 400


def test_pending_delivery_cannot_verify(otp):
    w = otp
    code = send(w)
    row = w.db.query(EmailOTP).one(); row.delivery_status = "pending"; w.db.commit()
    assert verify(w, code).status_code == 400


def test_cutover_requires_verification_and_rejects_jwts(otp):
    w = otp
    assert w.client.get("/api/auth/methods").json() == {"email_otp": True}
    assert w.client.get("/api/auth/me", headers=w.headers(w.alice)).status_code == 401
    result = w.client.post("/api/auth/token", data={"username": "alice", "password": "phase2-test-password"})
    assert result.json() == {"verification_required": True, "email": w.alice.email}
    assert not w.client.cookies and w.db.query(AuthSession).count() == 0
    assert w.client.post("/api/auth/register", json={"username": "new", "email": "new@example.com", "password": "password"}).status_code == 400


def test_disabled_otp_preserves_legacy_login_and_me(world, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_OTP_ENABLED", False)
    w = world
    assert w.client.get("/api/auth/methods").json() == {"email_otp": False}
    result = w.client.post("/api/auth/token", data={"username": "alice", "password": "phase2-test-password"})
    assert result.status_code == 200
    headers = {"Authorization": "Bearer " + result.json()["access_token"]}
    assert w.client.get("/api/auth/me", headers=headers).json()["id"] == w.alice.id
    assert w.client.post("/api/auth/request-otp", json={"email": w.alice.email}).status_code == 503


def test_explicit_legacy_rollback_clears_stale_otp_cookies(otp, monkeypatch):
    w = otp
    login(w)
    assert w.client.cookies
    monkeypatch.setattr(settings, "EMAIL_OTP_ENABLED", False)
    result = w.client.post("/api/auth/token", data={"username": "alice", "password": "phase2-test-password"})
    assert result.status_code == 200
    assert not w.client.cookies
    assert w.client.get("/api/auth/me", headers=w.headers(w.alice)).status_code == 200


def test_anonymous_login_origin_and_input_validation(otp):
    w = otp
    for path, payload in [("request-otp", {"email": w.alice.email}),
                          ("verify-otp", {"email": w.alice.email, "code": "123456", "password": "password"})]:
        assert w.client.post(f"/api/auth/{path}", json=payload, headers={"Origin": "null"}).status_code == 403
    assert w.client.post("/api/auth/request-otp", json={"email": "bad\naddress"}).status_code == 422
    assert verify(w, "1" * 10000).status_code == 422
    assert len(w.mail) == 0


def test_local_http_explicit_loopback_only(otp, monkeypatch):
    w = otp
    monkeypatch.setattr(settings, "AUTH_ORIGIN", "http://127.0.0.1.nip.io")
    w.client.base_url = settings.AUTH_ORIGIN
    w.client.headers["Origin"] = settings.AUTH_ORIGIN
    assert w.client.post("/api/auth/request-otp", json={"email": w.alice.email}).status_code == 503
    monkeypatch.setattr(settings, "AUTH_ALLOW_LOCAL_HTTP", True)
    result = login(w)
    assert all("Secure" not in c and "__Host-" not in c for c in result.headers.get_list("set-cookie"))
    assert "HttpOnly" in result.headers.get_list("set-cookie")[0]
    assert w.client.get("/api/auth/me").status_code == 200
    monkeypatch.setattr(settings, "AUTH_ORIGIN", "http://public.example.com")
    with pytest.raises(HTTPException): auth_sessions.check_configuration()


def test_forwarded_ip_requires_explicit_trusted_peer(otp, monkeypatch):
    request = Request({"type": "http", "client": ("10.0.0.2", 1), "headers": [(b"x-real-ip", b"198.51.100.1")]})
    assert auth_sessions.client_address(request) == "10.0.0.2"
    monkeypatch.setattr(settings, "AUTH_TRUSTED_PROXIES", ["10.0.0.2/32"])
    assert auth_sessions.client_address(request) == "198.51.100.1"


def test_https_and_explicit_local_login_coexist_with_separate_cookies(otp, monkeypatch):
    w = otp
    monkeypatch.setattr(settings, "AUTH_ALLOW_LOCAL_HTTP", True)
    monkeypatch.setattr(settings, "AUTH_LOCAL_ORIGIN", "http://127.0.0.1.nip.io")
    https_result = login(w)
    assert all("Secure" in c and "__Host-" in c for c in https_result.headers.get_list("set-cookie"))
    w.client.base_url = settings.AUTH_LOCAL_ORIGIN
    w.client.headers["Origin"] = settings.AUTH_LOCAL_ORIGIN
    local_result = login(w)
    assert all("Secure" not in c and "__Host-" not in c for c in local_result.headers.get_list("set-cookie"))
    assert w.client.get("/api/auth/me").status_code == 200
    assert w.client.post("/api/auth/logout").status_code == 403
    local_csrf = w.client.cookies.get("researchiq_local_csrf")
    assert w.client.post("/api/auth/logout", headers={"X-CSRF-Token": local_csrf}).status_code == 200
    assert w.client.get("/api/auth/me").status_code == 401
    w.client.base_url = settings.AUTH_ORIGIN
    w.client.headers["Origin"] = settings.AUTH_ORIGIN
    assert w.client.get("/api/auth/me").status_code == 200
    assert w.client.post("/api/auth/logout", headers={"Origin": "https://evil.invalid"}).status_code == 403
    assert w.client.post("/api/auth/logout", headers=csrf(w)).status_code == 200


@pytest.mark.parametrize("origin", ["http://public.example.com", "https://localhost", "http://127.0.0.1.nip.io/path", "http://localhost:bad"])
def test_additional_origin_is_local_http_only(otp, monkeypatch, origin):
    monkeypatch.setattr(settings, "AUTH_ALLOW_LOCAL_HTTP", True)
    monkeypatch.setattr(settings, "AUTH_LOCAL_ORIGIN", origin)
    with pytest.raises(HTTPException):
        auth_sessions.check_configuration()


def test_tunnel_cookies_cannot_be_downgraded_by_origin_or_forwarded_host(otp, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ALLOW_LOCAL_HTTP", True)
    monkeypatch.setattr(settings, "AUTH_LOCAL_ORIGIN", "http://127.0.0.1.nip.io")
    request = Request({"type": "http", "scheme": "http", "path": "/api/auth/token",
                       "headers": [(b"host", b"localhost"),
                                   (b"origin", b"http://127.0.0.1.nip.io"),
                                   (b"x-forwarded-host", b"127.0.0.1.nip.io")]})
    assert auth_sessions.cookie_names(request) == (auth_sessions.SESSION_COOKIE, auth_sessions.CSRF_COOKIE)


@pytest.mark.parametrize("mode", ["starttls", "ssl"])
def test_smtp_uses_verified_tls_and_configured_sender(otp, monkeypatch, mode):
    # Call the real SMTP adapter; no network or credentials are used by this test.
    for name, value in {"SMTP_HOST": "smtp-relay.brevo.com", "SMTP_FROM_EMAIL": "sender@example.com",
                        "SMTP_USERNAME": "smtp-login", "SMTP_PASSWORD": "smtp-test-only", "SMTP_SECURITY": mode}.items():
        monkeypatch.setattr(settings, name, value)
    transport = MagicMock()
    smtp = transport.return_value.__enter__.return_value
    smtp.send_message.return_value = {}
    monkeypatch.setattr(email_otp.smtplib, "SMTP_SSL" if mode == "ssl" else "SMTP", transport)
    REAL_SEND("recipient@example.com", "123456")
    smtp.login.assert_called_once_with("smtp-login", "smtp-test-only")
    if mode == "starttls":
        context = smtp.starttls.call_args.kwargs["context"]
        assert [call[0] for call in smtp.method_calls] == ["ehlo", "starttls", "ehlo", "login", "send_message"]
    else: context = transport.call_args.kwargs["context"]
    assert context.check_hostname
    message = smtp.send_message.call_args.args[0]
    assert message["From"] == "sender@example.com" and "123456" in message.get_content()


REAL_SEND = email_otp.send_code


def test_cookie_authenticated_two_collection_rag_regression(otp):
    w = otp
    login(w)
    w.headers = lambda actor: csrf(w)
    phase2.test_authorized_http_chat_streams_and_persists_citations_from_both_collections(w)


def test_cookie_writes_require_csrf_and_remain_owner_scoped(otp):
    w = otp
    login(w)
    body = {"name": "New private collection", "scope": "public", "user_id": w.bob.id}
    assert w.client.post("/api/knowledge-base", json=body).status_code == 403
    result = w.client.post("/api/knowledge-base", json=body, headers=csrf(w))
    assert result.status_code == 200 and result.json()["user_id"] == w.alice.id
    assert w.client.get(f"/api/knowledge-base/{w.bob_kb.id}").status_code == 404
    phase2.test_owner_browser_access_works_but_legacy_api_key_is_retired(w)


def test_configuration_failure_does_not_downgrade_authentication(otp, monkeypatch):
    w = otp
    monkeypatch.setattr(settings, "AUTH_OTP_SECRET", "short")
    assert w.client.get("/api/auth/me", headers=w.headers(w.alice)).status_code == 503
    assert w.client.post("/api/auth/request-otp", json={"email": w.alice.email}).status_code == 503
    assert not w.mail


def test_mysql_accent_collation_does_not_link_another_identity(otp):
    w = otp
    if w.engine.dialect.name != "mysql": pytest.skip("Legacy MySQL accent-insensitive collation")
    w.alice.email = "al\u00efce@uaf.edu.pk"; w.db.commit()
    assert w.client.post("/api/auth/request-otp", json={"email": "alice@uaf.edu.pk"}).status_code == 200
    assert not w.mail
    assert verify(w, "123456", "alice@uaf.edu.pk").status_code == 400
    assert w.client.post("/api/auth/token", data={"username": "alice@uaf.edu.pk", "password": "phase2-test-password"}).status_code == 401
    assert w.db.query(AuthSession).count() == 0


def test_smtp_no_plaintext_fallback_on_tls_failure(otp, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_SECURITY", "starttls")
    transport = MagicMock()
    smtp = transport.return_value.__enter__.return_value
    smtp.starttls.side_effect = email_otp.smtplib.SMTPNotSupportedError("TLS unavailable")
    monkeypatch.setattr(email_otp.smtplib, "SMTP", transport)
    with pytest.raises(email_otp.smtplib.SMTPException): REAL_SEND("recipient@example.com", "123456")
    smtp.login.assert_not_called()
    smtp.send_message.assert_not_called()


def test_cleanup_is_bounded_and_preserves_live_auth_and_research_data(otp):
    from app.services.auth_cleanup import purge_expired
    w = otp
    login(w)
    for n in range(3):
        w.db.add(EmailOTP(email=f"expired{n}@example.com", otp_hash="a" * 64,
                          expires_at=datetime.utcnow() - timedelta(days=2), delivery_status="failed"))
    w.db.commit()
    counts = purge_expired(w.db, batch_size=2)
    assert counts == {"email_otps": 2, "auth_sessions": 0, "auth_rate_limits": 0}
    assert w.db.query(EmailOTP).count() == 2
    assert w.client.get("/api/auth/me").status_code == 200
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}").status_code == 200


@pytest.mark.parametrize("action", ["verify", "send"])
def test_mysql_concurrent_requests_allow_one_winner(otp, action):
    w = otp
    if w.engine.dialect.name != "mysql": pytest.skip("Row-lock concurrency requires disposable MySQL")
    code = send(w) if action == "verify" else None
    barrier = Barrier(2)
    def attempt():
        with TestClient(w.app, base_url="https://testserver") as client:
            barrier.wait(timeout=10)
            path = "verify-otp" if action == "verify" else "request-otp"
            payload = {"email": w.alice.email, **({"code": code, "password": "phase2-test-password"} if code else {})}
            return client.post(f"/api/auth/{path}", json=payload, headers={"Origin": settings.AUTH_ORIGIN}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ([200, 400] if action == "verify" else [200, 429])
    if action == "verify": assert w.db.query(AuthSession).count() == 0
    else: assert len(w.mail) == 1


def test_mysql_concurrent_new_users_do_not_gap_lock_each_other(otp, monkeypatch):
    from app.api.api_v1 import auth
    w = otp
    if w.engine.dialect.name != "mysql": pytest.skip("Concurrent signup locking requires disposable MySQL")
    addresses = ["new-a@example.com", "new-b@example.com"]
    barrier = Barrier(2)
    assign = auth.assign_researcher
    def concurrent_assign(db, user):
        barrier.wait(timeout=15)
        assign(db, user)
    monkeypatch.setattr(auth, "assign_researcher", concurrent_assign)
    monkeypatch.setattr(auth_sessions, "client_address", lambda request: request.headers["x-test-ip"])
    def attempt(item):
        index, email = item
        with TestClient(w.app, base_url="https://testserver") as client:
            return client.post("/api/auth/register", json={"email": email, "username": f"new-user-{index}", "password": "Password123"},
                               headers={"Origin": settings.AUTH_ORIGIN, "x-test-ip": f"198.51.100.{index + 1}"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(attempt, enumerate(addresses))) == [200, 200]
    assert w.db.query(User).filter(User.email.in_(addresses)).count() == 2


# Added by ChatGPT: revised registration/password contract, including OTP-era account recovery.
def test_unregistered_email_never_sends_creates_or_authenticates(otp):
    w = otp
    count = w.db.query(User).count()
    assert w.client.post("/api/auth/request-otp", json={"email": "unregistered@gmail.com"}).status_code == 200
    assert not w.mail and w.db.query(EmailOTP).count() == 0
    assert verify(w, "123456", "unregistered@gmail.com").status_code == 400
    assert w.db.query(User).count() == count and not w.client.cookies
    assert w.client.post("/api/auth/token", data={"username": "unregistered@gmail.com", "password": "Password123"}).status_code == 401


def test_registration_verification_then_repeated_password_login(otp):
    w = otp
    payload = {"username": "registered", "email": "registered@example.com", "password": "Password123"}
    assert w.client.post("/api/auth/register", json=payload).status_code == 200
    assert not w.client.cookies
    result = w.client.post("/api/auth/token", data=payload)
    assert result.json()["verification_required"] is True
    code = send(w, payload["email"])
    verify_payload = {"email": payload["email"], "password": payload["password"], "code": code}
    assert w.client.post("/api/auth/verify-otp", json={**verify_payload, "password": "WrongPassword123"}).status_code == 400
    assert w.client.post("/api/auth/verify-otp", json=verify_payload).status_code == 200
    assert not w.client.cookies
    for identifier in [payload["username"], payload["email"], payload["username"]]:
        result = w.client.post("/api/auth/token", data={"username": identifier, "password": payload["password"]})
        assert result.json() == {"authenticated": True}
        assert w.client.get("/api/auth/me").status_code == 200
        assert w.client.post("/api/auth/logout", headers=csrf(w)).status_code == 200
    assert len(w.mail) == 1
    assert w.client.post("/api/auth/register", json=payload).status_code == 400


@pytest.mark.parametrize("existing_password", [True, False])
def test_password_recovery_preserves_identity_and_revokes_sessions(otp, existing_password):
    w = otp
    login(w)
    old_session = w.client.cookies.get(auth_sessions.SESSION_COOKIE)
    if not existing_password:
        w.alice.hashed_password = None
        w.db.commit()
    release_cooldown(w)
    payload = {"email": w.alice.email, "purpose": "reset_password"}
    assert w.client.post("/api/auth/request-otp", json=payload).status_code == 200
    code = w.mail[-1][1]
    # Recovery codes cannot be exchanged as email-verification codes.
    assert verify(w, code).status_code == 400
    body = {**payload, "code": code, "password": "Replacement123"}
    assert w.client.post("/api/auth/verify-otp", json=body).status_code == 200
    assert w.client.post("/api/auth/verify-otp", json=body).status_code == 400
    assert w.client.get("/api/auth/me").status_code == 401
    w.client.cookies.clear()
    assert w.client.post("/api/auth/token", data={"username": "alice", "password": "phase2-test-password"}).status_code == 401
    assert w.client.post("/api/auth/token", data={"username": "alice", "password": "Replacement123"}).status_code == 200
    assert w.client.get("/api/auth/me").json()["id"] == w.alice.id
    assert w.client.get(f"/api/knowledge-base/{w.alice_kb.id}").status_code == 200
    assert w.client.cookies.get(auth_sessions.SESSION_COOKIE) != old_session


def test_password_login_rate_limit_and_origin(otp):
    w = otp
    payload = {"username": "alice", "password": "bad"}
    assert w.client.post("/api/auth/token", data=payload, headers={"Origin": "https://evil.example"}).status_code == 403
    for _ in range(20):
        assert w.client.post("/api/auth/token", data=payload).status_code == 401
    result = w.client.post("/api/auth/token", data=payload)
    assert result.status_code == 429 and result.headers["Retry-After"] == "900"


@pytest.mark.parametrize("password", ["short", "lowercase123", "UPPERCASE123", "NoNumbers", "A1" + "\u00e9" * 36])
def test_new_password_policy_is_enforced_server_side(otp, password):
    assert otp.client.post("/api/auth/register", json={"username": "new-user", "email": "new@example.com", "password": password}).status_code == 400


def test_unverified_api_key_and_session_cannot_bypass_verification(otp):
    w = otp
    assert w.client.get(f"/openapi/knowledge/{w.alice_kb.id}/query", params={"query": "secret"}, headers={"X-API-Key": "phase2-alice"}).status_code == 410
    login(w)
    w.db.expire_all()
    w.alice.email_verified_at = None
    w.db.commit()
    assert w.client.get("/api/auth/me").status_code == 401


def test_mysql_verification_migration_roundtrip_preserves_existing_data(world, monkeypatch):
    import os
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from tests.test_phase1_migrations import snapshot
    w = world
    if w.engine.dialect.name != "mysql": pytest.skip("Migration roundtrip requires disposable MySQL")
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI", os.environ["PHASE2_TEST_DATABASE_URI"])
    w.db.add(AuthSession(user_id=w.alice.id, token_hash="a" * 64, csrf_token_hash="b" * 64,
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
    # An exhausted/invalidated challenge is not evidence of verified ownership.
    w.db.add(EmailOTP(email=w.bob.email, otp_hash="c" * 64, attempt_count=5, used_at=datetime.utcnow(),
                     expires_at=datetime.utcnow(), delivery_status="sent"))
    w.db.commit()
    w.db.close()
    with w.engine.connect() as connection:
        inspector = sa.inspect(connection)
        tables = {name: [c["name"] for c in inspector.get_columns(name) if c["name"] not in {"email_verified_at", "source_scope"}]
                  for name in inspector.get_table_names() if name != "alembic_version"}
        before = snapshot(connection, tables)
    config = Config("alembic.ini")
    for _ in range(2):
        command.downgrade(config, "riq_003")
        with w.engine.connect() as connection:
            assert snapshot(connection, tables) == before
            assert "email_verified_at" not in {c["name"] for c in sa.inspect(connection).get_columns("users")}
        command.upgrade(config, "head")
        with w.engine.connect() as connection:
            assert snapshot(connection, tables) == before
            verified = dict(connection.execute(sa.text("SELECT username,email_verified_at FROM users")).all())
            assert verified["alice"] is not None
            assert verified["bob"] is None and verified["institutional_system"] is None
