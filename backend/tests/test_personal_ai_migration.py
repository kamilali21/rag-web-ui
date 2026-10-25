"""Opt-in, disposable MySQL gate. Refuses the application database."""
import os
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from tests.test_phase1_migrations import snapshot


def test_personal_ai_migration():
    uri = os.getenv("PERSONAL_AI_TEST_DATABASE_URI")
    if not uri:
        pytest.skip("Requires a fresh disposable MySQL database")
    url = make_url(uri)
    assert url.host == "researchiq-byok-mysql" and url.database == "researchiq_byok_test"
    from app.core.config import settings
    old = settings.SQLALCHEMY_DATABASE_URI
    settings.SQLALCHEMY_DATABASE_URI = uri
    engine = sa.create_engine(uri)
    config = Config("alembic.ini")
    try:
        assert not sa.inspect(engine).get_table_names()
        command.upgrade(config, "riq_007")
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO users (id,email,username,is_active,is_system,created_at,updated_at) VALUES (1,'byok@example.invalid','byok',1,0,NOW(),NOW())"))
            inspector = sa.inspect(conn)
            tables = {name:[col['name'] for col in inspector.get_columns(name)] for name in inspector.get_table_names() if name != 'alembic_version'}
            before = snapshot(conn, tables)
        command.upgrade(config, "riq_008")
        with engine.begin() as conn:
            assert snapshot(conn, tables) == before
            conn.execute(sa.text("INSERT INTO user_ai_settings (user_id,provider,model,encrypted_key,key_last4) VALUES (1,'openrouter','openrouter/free','synthetic-ciphertext','test')"))
        with pytest.raises(RuntimeError, match="Remove personal AI settings"):
            command.downgrade(config, "riq_007")
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM users WHERE id=1"))
            assert conn.scalar(sa.text("SELECT COUNT(*) FROM user_ai_settings")) == 0
            conn.execute(sa.text("INSERT INTO users (id,email,username,is_active,is_system,created_at,updated_at) VALUES (1,'byok@example.invalid','byok',1,0,NOW(),NOW())"))
        command.downgrade(config, "riq_007")
        assert 'user_ai_settings' not in sa.inspect(engine).get_table_names()
        command.upgrade(config, "riq_008")
        with engine.connect() as conn:
            assert conn.scalar(sa.text("SELECT COUNT(*) FROM users")) == 1
    finally:
        settings.SQLALCHEMY_DATABASE_URI = old
        engine.dispose()
