"""Fail closed before production services initialize; errors contain names, never values."""
import ipaddress
import re
from urllib.parse import urlsplit


def validate_production_settings(settings):
    if settings.ENVIRONMENT not in {"development", "test", "production"}:
        raise RuntimeError("Invalid ENVIRONMENT setting")
    if settings.ENVIRONMENT != "production":
        return
    errors = []
    if not settings.EMAIL_OTP_ENABLED:
        errors.append("EMAIL_OTP_ENABLED")
    if settings.AUTH_ALLOW_LOCAL_HTTP or settings.AUTH_LOCAL_ORIGIN:
        errors.append("local authentication exceptions")
    try:
        origin = urlsplit(settings.AUTH_ORIGIN)
        host = origin.hostname or ""
        if (origin.scheme != "https" or origin.username or origin.password
                or origin.path or origin.query or origin.fragment or origin.port
                or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", host)
                or host.endswith((".localhost", ".nip.io", ".test", ".invalid"))):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
    except ValueError:
        errors.append("AUTH_ORIGIN")
    secrets = [settings.SECRET_KEY, settings.AUTH_OTP_SECRET,
               settings.MYSQL_PASSWORD, settings.MINIO_SECRET_KEY]
    if (any(len(s) < 32 or "change_me" in s.lower() or s.startswith("your-") for s in secrets)
            or len(set(secrets)) != len(secrets)):
        errors.append("independent JWT/OTP/database/storage secrets")
    if settings.ALGORITHM != "HS256":
        errors.append("ALGORITHM")
    if not settings.MYSQL_USER or settings.MYSQL_USER.lower() == "root" or settings.SQLALCHEMY_DATABASE_URI:
        errors.append("runtime database identity")
    if settings.RUN_STARTUP_MIGRATIONS or settings.CREATE_STORAGE_BUCKET:
        errors.append("bootstrap privileges")
    if not settings.MINIO_ACCESS_KEY or settings.MINIO_ACCESS_KEY == "minioadmin":
        errors.append("MINIO_ACCESS_KEY")
    if settings.SMTP_SECURITY not in {"ssl", "starttls"}:
        errors.append("SMTP_SECURITY")
    for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"):
        value = getattr(settings, name)
        if not value or "change_me" in value.lower():
            errors.append(name)
    try:
        if len(settings.AUTH_TRUSTED_PROXIES) != 1:
            raise ValueError()
        peer = ipaddress.ip_network(settings.AUTH_TRUSTED_PROXIES[0], strict=True)
        if peer.prefixlen != peer.max_prefixlen or not peer.is_private or peer.is_loopback:
            raise ValueError()
    except ValueError:
        errors.append("single private proxy peer")
    if errors:
        raise RuntimeError("Unsafe production configuration: " + ", ".join(errors))
