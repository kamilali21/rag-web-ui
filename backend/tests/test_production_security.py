"""Offline checks; no runtime credentials, service connections, or migrations."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.production_security import validate_production_settings


def production(**overrides):
    values = dict(ENVIRONMENT="production", EMAIL_OTP_ENABLED=True,
                  AUTH_ALLOW_LOCAL_HTTP=False, AUTH_LOCAL_ORIGIN="",
                  AUTH_ORIGIN="https://research.university.edu", SECRET_KEY="a" * 32,
                  AUTH_OTP_SECRET="b" * 32, MYSQL_PASSWORD="c" * 32, MINIO_SECRET_KEY="d" * 32,
                  MYSQL_USER="runtime", SQLALCHEMY_DATABASE_URI=None, ALGORITHM="HS256",
                  RUN_STARTUP_MIGRATIONS=False, CREATE_STORAGE_BUCKET=False,
                  MINIO_ACCESS_KEY="bucket-user", SMTP_SECURITY="starttls", SMTP_HOST="smtp.example.org",
                  SMTP_USERNAME="mailer", SMTP_PASSWORD="synthetic", SMTP_FROM_EMAIL="a@example.org",
                  AUTH_TRUSTED_PROXIES=["172.30.240.10/32"])
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("mode", ["ssl", "starttls"])
def test_secure_production_accepted(mode):
    validate_production_settings(production(SMTP_SECURITY=mode))


@pytest.mark.parametrize("change", [
    {"EMAIL_OTP_ENABLED": False}, {"AUTH_ALLOW_LOCAL_HTTP": True},
    {"AUTH_LOCAL_ORIGIN": "http://127.0.0.1.nip.io"},
    {"AUTH_ORIGIN": "http://research.university.edu"}, {"AUTH_ORIGIN": "https://127.0.0.1.nip.io"},
    {"AUTH_ORIGIN": "https://research.university.edu/path"},
    {"AUTH_ORIGIN": "https://someone@research.university.edu"},
    {"AUTH_ORIGIN": "https://192.168.1.1"},
    {"AUTH_ORIGIN": "https://bad host.example.org"},
    {"SECRET_KEY": "your-secret-key-here"}, {"AUTH_OTP_SECRET": ""},
    {"MYSQL_PASSWORD": "a" * 32}, {"MINIO_SECRET_KEY": "CHANGE_ME" + "x" * 40},
    {"MYSQL_USER": "root"}, {"SQLALCHEMY_DATABASE_URI": "mysql://private"},
    {"RUN_STARTUP_MIGRATIONS": True}, {"CREATE_STORAGE_BUCKET": True},
    {"MINIO_ACCESS_KEY": "minioadmin"}, {"SMTP_SECURITY": "none"}, {"SMTP_PASSWORD": ""},
    {"SMTP_SECURITY": "tls"},
    {"AUTH_TRUSTED_PROXIES": []}, {"AUTH_TRUSTED_PROXIES": ["0.0.0.0/0"]},
    {"AUTH_TRUSTED_PROXIES": ["172.30.240.0/24"]}, {"ALGORITHM": "none"},
    {"ENVIRONMENT": "prod-typo"},
])
def test_unsafe_configuration_fails_without_echoing_values(change):
    with pytest.raises(RuntimeError) as error:
        validate_production_settings(production(**change))
    for value in change.values():
        if isinstance(value, str) and len(value) > 12:
            assert value not in str(error.value)


def test_local_development_preserves_existing_mode():
    validate_production_settings(production(ENVIRONMENT="development", EMAIL_OTP_ENABLED=False,
                                           AUTH_ALLOW_LOCAL_HTTP=True, AUTH_LOCAL_ORIGIN="http://127.0.0.1.nip.io"))


def test_read_only_schema_gate_never_runs_migrations(monkeypatch):
    from app.startup.migarate import DatabaseMigrator
    migrator = object.__new__(DatabaseMigrator)
    migrator.check_migration_needed = Mock(return_value=(False, "current", "current"))
    migrator.run_migrations = Mock(side_effect=AssertionError("Must not run DDL"))
    migrator.require_current_schema()
    migrator.check_migration_needed.return_value = (True, "old", "current")
    with pytest.raises(RuntimeError, match="operator-managed"):
        migrator.require_current_schema()
    migrator.run_migrations.assert_not_called()


def test_production_bucket_gate_never_creates_storage(monkeypatch):
    from app.core import minio
    client = Mock()
    client.bucket_exists.return_value = False
    monkeypatch.setattr(minio, "get_minio_client", lambda: client)
    monkeypatch.setattr(minio.settings, "CREATE_STORAGE_BUCKET", False)
    with pytest.raises(RuntimeError, match="provisioned"):
        minio.init_minio()
    client.make_bucket.assert_not_called()
    client.bucket_exists.return_value = True
    minio.init_minio()
    client.make_bucket.assert_not_called()
