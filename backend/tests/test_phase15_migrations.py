"""Explicitly opt-in disposable MySQL migration gate; never connects to the live DB."""
import os
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from tests.test_phase1_migrations import snapshot


def test_analysis_migration_preserves_rows_and_roundtrips():
    uri = os.getenv("PHASE15_TEST_DATABASE_URI")
    if not uri:
        pytest.skip("Set PHASE15_TEST_DATABASE_URI for disposable MySQL")
    url = make_url(uri)
    assert url.host == "researchiq-phase15-mysql" and url.database == "researchiq_phase15_test"
    from app.core.config import settings
    old = settings.SQLALCHEMY_DATABASE_URI
    settings.SQLALCHEMY_DATABASE_URI = uri
    engine = sa.create_engine(uri)
    config = Config("alembic.ini")
    try:
        assert not sa.inspect(engine).get_table_names(), "Use a fresh disposable schema"
        command.upgrade(config, "riq_006")
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO users (id,email,username,is_active,is_system,created_at,updated_at) VALUES (1,'synthetic@example.invalid','synthetic',1,0,NOW(),NOW())"))
            conn.execute(sa.text("INSERT INTO knowledge_bases (id,name,user_id,scope,is_system_managed,created_at,updated_at) VALUES (1,'Synthetic',1,'private',0,NOW(),NOW())"))
            conn.execute(sa.text("INSERT INTO documents (id,knowledge_base_id,file_path,file_name,file_size,content_type,created_at,updated_at) VALUES (1,1,'synthetic','synthetic.pdf',10,'application/pdf',NOW(),NOW())"))
            inspector = sa.inspect(conn)
            tables = {name: [col["name"] for col in inspector.get_columns(name)] for name in inspector.get_table_names() if name != "alembic_version"}
            before = snapshot(conn, tables)
        command.upgrade(config, "riq_007")
        with engine.connect() as conn:
            assert snapshot(conn, tables) == before
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO analysis_runs (id,user_id,request_id,analysis_type,status,scope,request_json) VALUES (1,1,'synthetic','compare','complete','private','{}')"))
            conn.execute(sa.text("INSERT INTO analysis_documents VALUES (1,1,1,NULL,'selected')"))
            conn.execute(sa.text("INSERT INTO analysis_evidence (analysis_id,evidence_id,document_id,source_document_id,chunk_id,excerpt,retrieval_rank,evidence_hash) VALUES (1,'E1',1,1,'chunk1','Synthetic evidence',1,:hash)"), {"hash": "a" * 64})
        with pytest.raises(RuntimeError, match="Preserve/export"):
            command.downgrade(config, "riq_006")
        with engine.connect() as conn:
            tx = conn.begin()
            conn.execute(sa.text("DELETE FROM documents WHERE id=1"))
            assert conn.scalar(sa.text("SELECT document_id FROM analysis_evidence")) is None
            assert conn.scalar(sa.text("SELECT source_document_id FROM analysis_evidence")) == 1
            assert conn.scalar(sa.text("SELECT document_id FROM analysis_documents")) is None
            tx.rollback()
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM analysis_runs WHERE id=1"))
            assert conn.scalar(sa.text("SELECT COUNT(*) FROM analysis_evidence")) == 0
            assert conn.scalar(sa.text("SELECT COUNT(*) FROM analysis_documents")) == 0
        command.downgrade(config, "riq_006")
        with engine.connect() as conn:
            assert snapshot(conn, tables) == before
            assert "analysis_runs" not in sa.inspect(conn).get_table_names()
        command.upgrade(config, "riq_007")
        with engine.connect() as conn:
            assert snapshot(conn, tables) == before
    finally:
        settings.SQLALCHEMY_DATABASE_URI = old
        engine.dispose()
