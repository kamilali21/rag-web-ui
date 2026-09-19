"""Added by ChatGPT: opt-in MySQL migration tests, restricted to a disposable clone.

Set PHASE1_TEST_DATABASE_URI to the researchiq-migration-test container and a
researchiq_migration_* database restored at revision 3580c0dcd005. No live DB access.
"""
import hashlib
import json
import os
from dataclasses import dataclass

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, configure_mappers

BASELINE = "3580c0dcd005"
HEAD = "riq_004"
NEW_TABLES = {
    "roles", "user_roles", "departments", "admin_allowlist", "email_otps",
    "auth_sessions", "auth_rate_limits", "academic_document_metadata", "bookmarks",
}


def snapshot(connection, tables):
    # Added by ChatGPT: compare every original value without logging private rows or hashes.
    result = {}
    for name, columns in tables.items():
        rows = connection.execute(sa.text(
            f"SELECT {', '.join('`' + column + '`' for column in columns)} FROM `{name}`"
        )).all()
        encoded = sorted(json.dumps(list(row), default=str) for row in rows)
        result[name] = (len(rows), hashlib.sha256(json.dumps(encoded).encode()).hexdigest())
    return result


@dataclass
class Database:
    engine: object
    config: Config
    original_tables: dict
    original_data: dict


@pytest.fixture(scope="module")
def migrated():
    uri = os.getenv("PHASE1_TEST_DATABASE_URI")
    if not uri:
        pytest.skip("PHASE1_TEST_DATABASE_URI is required for disposable MySQL tests")
    url = make_url(uri)
    assert url.host == "researchiq-migration-test", "Refusing a non-test database host"
    assert url.database.startswith("researchiq_migration_"), "Refusing a non-test database"
    from app.core.config import settings
    previous = settings.SQLALCHEMY_DATABASE_URI
    settings.SQLALCHEMY_DATABASE_URI = uri
    engine = sa.create_engine(uri)
    config = Config("alembic.ini")
    try:
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == BASELINE
            inspector = sa.inspect(connection)
            tables = {name: [col["name"] for col in inspector.get_columns(name)]
                      for name in inspector.get_table_names() if name != "alembic_version"}
            before = snapshot(connection, tables)
        command.upgrade(config, HEAD)
        yield Database(engine, config, tables, before)
        # Added by ChatGPT: exercise an entire reversal/re-upgrade with original data intact.
        command.downgrade(config, BASELINE)
        with engine.connect() as connection:
            assert snapshot(connection, tables) == before
            assert not NEW_TABLES.intersection(sa.inspect(connection).get_table_names())
            assert not next(c for c in sa.inspect(connection).get_columns("users")
                            if c["name"] == "hashed_password")["nullable"]
        command.upgrade(config, HEAD)
        with engine.connect() as connection:
            assert snapshot(connection, tables) == before
    finally:
        engine.dispose()
        settings.SQLALCHEMY_DATABASE_URI = previous


@pytest.fixture
def connection(migrated):
    with migrated.engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def test_preserves_all_legacy_data_and_ownership(migrated, connection):
    assert snapshot(connection, migrated.original_tables) == migrated.original_data
    assert NEW_TABLES.issubset(sa.inspect(connection).get_table_names())
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM knowledge_bases WHERE scope <> 'private' OR is_system_managed <> 0")) == 0
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM users WHERE is_system <> 0")) == 0
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM user_roles WHERE role_id = 1")) == connection.scalar(sa.text("SELECT COUNT(*) FROM users"))
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM user_roles WHERE role_id = 2")) == 0
    assert connection.execute(sa.text("SELECT id,name FROM roles ORDER BY id")).all() == [(1, "researcher"), (2, "admin")]


def test_existing_orm_and_new_relationships(connection):
    from app.models import User, KnowledgeBase, AcademicDocumentMetadata, Document
    from app.core.security import verify_password
    configure_mappers()
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        user = session.query(User).first()
        assert user and [role.name for role in user.roles] == ["researcher"]
        assert all(kb.scope == "private" for kb in user.knowledge_bases)
        otp_user = User(email="otp-schema@example.com", username="otp_schema", hashed_password=None)
        session.add(otp_user)
        session.flush()
        assert verify_password("not-a-password", otp_user.hashed_password) is False
        kb = KnowledgeBase(name="Schema defaults", user_id=otp_user.id)
        session.add(kb)
        session.flush()
        assert kb.scope == "private" and kb.is_system_managed is False
        doc = session.query(Document).first()
        doc.academic_metadata = AcademicDocumentMetadata(title="Schema test", publication_year=2024)
        session.flush()
        assert doc.academic_metadata.document_id == doc.id
        assert doc.academic_metadata.publication_status == "draft"


@pytest.mark.parametrize("statement", [
    "INSERT INTO roles (name) VALUES ('researcher')",
    "INSERT INTO user_roles SELECT MIN(id),1 FROM users",
    "INSERT INTO user_roles VALUES (-1,1)",
    "UPDATE users SET is_system=1,is_active=1 LIMIT 1",
    "UPDATE users SET is_system=1,is_active=0,is_superuser=1 LIMIT 1",
    "UPDATE users SET is_system=1,is_active=NULL,is_superuser=0 LIMIT 1",
    "UPDATE knowledge_bases SET scope='public' LIMIT 1",
    "UPDATE knowledge_bases SET is_system_managed=1 LIMIT 1",
    "UPDATE knowledge_bases SET scope='invalid' LIMIT 1",
    "INSERT INTO bookmarks (user_id,document_id) VALUES (-1,-1)",
    "INSERT INTO academic_document_metadata (document_id,title,publication_year) SELECT MIN(id),'test',999 FROM documents",
    "INSERT INTO academic_document_metadata (document_id,title,publication_status) SELECT MIN(id),'test','ready' FROM documents",
    "INSERT INTO email_otps (email,otp_hash,expires_at,attempt_count) VALUES ('test@example.com','hash',NOW(),-1)",
    "INSERT INTO email_otps (email,otp_hash,expires_at,delivery_status) VALUES ('test@example.com','hash',NOW(),'invalid')",
    "INSERT INTO auth_rate_limits (key_hash,window_started_at,request_count,expires_at) VALUES ('hash',NOW(),-1,NOW())",
])
def test_database_rejects_invalid_state(connection, statement):
    with pytest.raises(sa.exc.DBAPIError):
        connection.execute(sa.text(statement))


def test_uniqueness_indexes_and_cascades(connection):
    user_id = connection.scalar(sa.text("SELECT MIN(id) FROM users"))
    document_id = connection.scalar(sa.text("SELECT MIN(id) FROM documents"))
    params = {"user": user_id, "doc": document_id}
    connection.execute(sa.text("INSERT INTO departments (name,code) VALUES ('Schema Department','SCHEMA')"))
    department = connection.scalar(sa.text("SELECT id FROM departments WHERE code='SCHEMA'"))
    params["department"] = department
    connection.execute(sa.text("INSERT INTO admin_allowlist (email,department_id,added_by) VALUES ('exact@example.com',:department,:user)"), params)
    connection.execute(sa.text("INSERT INTO academic_document_metadata (document_id,title,authors_text,abstract,department_id) VALUES (:doc,'Synthetic irrigation research','Test author','Evidence about water',:department)"), params)
    connection.execute(sa.text("INSERT INTO bookmarks (user_id,document_id) VALUES (:user,:doc)"), params)
    for statement in [
        "INSERT INTO departments (name,code) VALUES ('Schema Department','OTHER')",
        "INSERT INTO departments (name,code) VALUES ('Other','SCHEMA')",
        "INSERT INTO admin_allowlist (email) VALUES ('exact@example.com')",
        "INSERT INTO academic_document_metadata (document_id,title) VALUES (:doc,'duplicate')",
        "INSERT INTO bookmarks (user_id,document_id) VALUES (:user,:doc)",
    ]:
        with pytest.raises(sa.exc.DBAPIError):
            connection.execute(sa.text(statement), params)
    index_rows = connection.execute(sa.text("SHOW INDEX FROM academic_document_metadata")).mappings().all()
    assert any(row["Key_name"] == "ix_academic_search" and row["Index_type"] == "FULLTEXT" for row in index_rows)
    assert {"ix_academic_catalog", "ix_academic_type_year", "ix_academic_date"}.issubset({row["Key_name"] for row in index_rows})
    for table, index in [("bookmarks", "ix_bookmarks_user_created"), ("auth_sessions", "ix_auth_sessions_user_expires"),
                         ("email_otps", "ix_email_otps_email_purpose_created"), ("knowledge_bases", "ix_knowledge_bases_scope_owner")]:
        assert index in {i["name"] for i in sa.inspect(connection).get_indexes(table)}
    connection.execute(sa.text("DELETE FROM departments WHERE id=:department"), params)
    assert connection.scalar(sa.text("SELECT department_id FROM academic_document_metadata WHERE document_id=:doc"), params) is None
    assert connection.scalar(sa.text("SELECT department_id FROM admin_allowlist WHERE email='exact@example.com'")) is None
    # Added by ChatGPT: test document cascade using a new document, not legacy dependent rows.
    result = connection.execute(sa.text("INSERT INTO documents (file_path,file_name,content_type,knowledge_base_id,created_at,updated_at) SELECT 'test','cascade.pdf','application/pdf',MIN(id),NOW(),NOW() FROM knowledge_bases"))
    doc = result.lastrowid
    connection.execute(sa.text("INSERT INTO academic_document_metadata (document_id,title) VALUES (:id,'Cascade')"), {"id": doc})
    connection.execute(sa.text("INSERT INTO bookmarks (user_id,document_id) VALUES (:user,:doc)"), {"user": user_id, "doc": doc})
    connection.execute(sa.text("DELETE FROM documents WHERE id=:id"), {"id": doc})
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM bookmarks WHERE document_id=:id"), {"id": doc}) == 0
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM academic_document_metadata WHERE document_id=:id"), {"id": doc}) == 0


def test_fulltext_search_after_commit(migrated):
    # Added by ChatGPT: InnoDB FULLTEXT searches committed rows, not the current transaction's inserts.
    with migrated.engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO academic_document_metadata (document_id,title) SELECT MIN(id),'Irrigation synthetic research' FROM documents"))
    try:
        with migrated.engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM academic_document_metadata WHERE MATCH(title,authors_text,abstract) AGAINST ('irrigation')")) == 1
        with pytest.raises(RuntimeError, match="academic_document_metadata"):
            command.downgrade(migrated.config, "riq_002")
        with migrated.engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "riq_003"
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM academic_document_metadata WHERE title='Irrigation synthetic research'"))
        command.upgrade(migrated.config, HEAD)


def test_auth_uniqueness_and_user_cascade(connection):
    result = connection.execute(sa.text("INSERT INTO users (email,username,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES ('cascade@example.com','schema_cascade',NULL,1,0,NOW(),NOW())"))
    params = {"id": result.lastrowid}
    connection.execute(sa.text("INSERT INTO user_roles (user_id,role_id) VALUES (:id,1)"), params)
    connection.execute(sa.text("INSERT INTO auth_sessions (user_id,token_hash,csrf_token_hash,expires_at) VALUES (:id,'token','csrf',NOW())"), params)
    with pytest.raises(sa.exc.DBAPIError):
        connection.execute(sa.text("INSERT INTO auth_sessions (user_id,token_hash,csrf_token_hash,expires_at) VALUES (:id,'token','other',NOW())"), params)
    connection.execute(sa.text("DELETE FROM users WHERE id=:id"), params)
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM user_roles WHERE user_id=:id"), params) == 0
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM auth_sessions WHERE user_id=:id"), params) == 0


def test_exact_email_matching_and_model_constraints(connection):
    from app.models.base import Base
    connection.execute(sa.text("INSERT INTO admin_allowlist (email) VALUES ('exact@example.com')"))
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_allowlist WHERE email='EXACT@example.com'")) == 0
    assert connection.scalar(sa.text("SELECT COUNT(*) FROM admin_allowlist WHERE email=CONCAT(CHAR(195,169 USING utf8mb4),'xact@example.com')")) == 0
    inspector = sa.inspect(connection)
    for table in NEW_TABLES:
        expected = {constraint.name for constraint in Base.metadata.tables[table].constraints
                    if isinstance(constraint, sa.UniqueConstraint)}
        actual = {constraint["name"] for constraint in inspector.get_unique_constraints(table)}
        assert expected.issubset(actual), table


@pytest.mark.parametrize("insert, cleanup, reason", [
    ("INSERT INTO bookmarks (user_id,document_id) SELECT (SELECT MIN(id) FROM users),MIN(id) FROM documents",
     "DELETE FROM bookmarks", "bookmarks"),
    ("UPDATE knowledge_bases SET scope='public',is_system_managed=1 ORDER BY id LIMIT 1",
     "UPDATE knowledge_bases SET scope='private',is_system_managed=0", "Public collections"),
])
def test_library_rollback_guards(migrated, insert, cleanup, reason):
    with migrated.engine.begin() as connection:
        connection.execute(sa.text(insert))
    try:
        with pytest.raises(RuntimeError, match=reason):
            command.downgrade(migrated.config, "riq_002")
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text(cleanup))
        command.upgrade(migrated.config, HEAD)


def test_earlier_migrations_refuse_destructive_rollback(migrated):
    command.downgrade(migrated.config, "riq_002")
    with migrated.engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO email_otps (email,otp_hash,expires_at) VALUES ('rollback@example.com','hash',NOW())"))
    try:
        with pytest.raises(RuntimeError, match="email_otps"):
            command.downgrade(migrated.config, "riq_001")
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM email_otps WHERE email='rollback@example.com'"))
    with migrated.engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO users (email,username,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES ('rollback@example.com','schema_rollback',NULL,1,0,NOW(),NOW())"))
    try:
        with pytest.raises(RuntimeError, match="OTP-only/system"):
            command.downgrade(migrated.config, "riq_001")
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM users WHERE username='schema_rollback'"))
    command.downgrade(migrated.config, "riq_001")
    with migrated.engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO departments (name,code) VALUES ('Rollback guard','ROLLBACK')"))
    try:
        with pytest.raises(RuntimeError, match="department"):
            command.downgrade(migrated.config, BASELINE)
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM departments WHERE code='ROLLBACK'"))
    with migrated.engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO roles (name) VALUES ('custom')"))
    try:
        with pytest.raises(RuntimeError, match="custom roles"):
            command.downgrade(migrated.config, BASELINE)
    finally:
        with migrated.engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM roles WHERE name='custom'"))
        command.upgrade(migrated.config, HEAD)
