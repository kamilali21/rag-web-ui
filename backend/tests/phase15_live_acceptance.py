"""Opt-in local synthetic PDF -> index -> comparison -> saved-evidence acceptance.

PHASE15_LIVE_ACCEPTANCE=1 python -m tests.phase15_live_acceptance
Uses configured embeddings/free model; never submits existing research to it.
Creates temporary users, a private collection and one public fixture, then
deletes only those fixtures using the existing document lifecycle.
"""
import io
import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
import httpx
import sqlalchemy as sa
from fastapi import Request
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from app.core.config import settings
from app.core.minio import get_minio_client
from app.db.session import SessionLocal
from app.models import User, Role, AdminAllowlist, AnalysisRun, AnalysisEvidence
from app.models.authentication import AuthSession
from app.services.auth_sessions import create_session, cookie_names


def snapshot(connection, tables):
    result = {}
    for name, columns in tables.items():
        rows = connection.execute(sa.text(f"SELECT {', '.join('`' + col + '`' for col in columns)} FROM `{name}`")).all()
        encoded = sorted(json.dumps(list(row), default=str) for row in rows)
        result[name] = (len(rows), hashlib.sha256(json.dumps(encoded).encode()).hexdigest())
    return result


def pdf(name, public=False, contradiction=False):
    lines = ["Synthetic software acceptance study " + name,
        "Objective: compare drip irrigation and flood irrigation water use.",
        "Method: randomized trial of drip versus flood irrigation.",
        "Study C: 120 greenhouse vegetable plots in Punjab during 2025." if contradiction else "Study B: 60 cotton field plots in Punjab during 2024." if public else "Study A: 120 greenhouse vegetable plots in Punjab during 2025.",
        "Finding: drip irrigation did not reduce water use; measured reduction was 0 percent." if contradiction else "Finding: drip irrigation reduced water use by 18 percent." if public else "Finding: drip irrigation reduced water use by 23 percent.",
        "Limitation: only one season was studied; yield was not measured.",
        "Conclusion: drip did not reduce water use in the studied setting." if contradiction else "Conclusion: drip reduced water use in the studied setting.",
        "Future work: multi-season field validation is required.",
        "These are fabricated test data, not real scientific findings."]
    writer = PdfWriter(); page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 10 Tf 36 740 Td " + " 0 -24 Td ".join(f"({line}) Tj" for line in lines) + " ET").encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    result = io.BytesIO(); writer.write(result); return result.getvalue()


def run(extra_acceptance=None, phase="phase15"):
    if phase not in {"phase15", "phase16", "phase17"} or os.getenv(f"{phase.upper()}_LIVE_ACCEPTANCE") != "1" or settings.AUTH_ORIGIN != "http://127.0.0.1.nip.io":
        raise SystemExit("Explicit opt-in and local Windows origin required")
    db = SessionLocal()
    inspector = sa.inspect(db.bind)
    tables = {name: [col["name"] for col in inspector.get_columns(name)] for name in inspector.get_table_names()
              if name not in {"alembic_version", "auth_sessions", "auth_rate_limits", "email_otps"}}
    before = snapshot(db, tables); db.rollback()
    storage = get_minio_client()
    def objects():
        return sorted((o.object_name, o.etag, o.size) for o in storage.list_objects(settings.MINIO_BUCKET_NAME, recursive=True))
    vectors = chromadb.HttpClient(host=settings.CHROMA_DB_HOST, port=settings.CHROMA_DB_PORT)
    def vector_ids():
        return {collection.name: sorted(collection.get(include=[])["ids"]) for collection in vectors.list_collections()}
    before_objects, before_vectors = objects(), vector_ids()
    name = phase + "_" + uuid.uuid4().hex[:12]
    users, clients = [], []
    kb_id = public_id = public_task = None
    checks = []
    def checked(client, method, path, expected=200, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}")
        return response
    def passed(step):
        checks.append(step); print(json.dumps({"passed": step}), flush=True)
    try:
        for suffix in ("owner", "other"):
            user = User(username=f"{name}_{suffix}", email=f"{name}_{suffix}@example.invalid", is_active=True, email_verified_at=datetime.utcnow())
            user.roles = [db.query(Role).filter_by(name="researcher").one()]
            if suffix == "owner":
                user.roles.append(db.query(Role).filter_by(name="admin").one())
                db.add(AdminAllowlist(email=user.email, is_active=True))
            db.add(user); db.flush(); users.append(user.id)
            token, csrf = create_session(db, user, Request({"type": "http", "method": "GET", "headers": []}))
            session_name, csrf_name = cookie_names()
            clients.append(httpx.Client(base_url="http://nginx", timeout=180,
                headers={"Host": "127.0.0.1.nip.io", "Origin": settings.AUTH_ORIGIN, "X-CSRF-Token": csrf},
                cookies={session_name: token, csrf_name: csrf}))
        db.commit()
        owner, other = clients
        kb_id = checked(owner, "POST", "/api/knowledge-base", json={"name": name}).json()["id"]
        uploaded = checked(owner, "POST", f"/api/knowledge-base/{kb_id}/documents/upload", files={"files": (f"{name}-private.pdf", pdf(name), "application/pdf")}).json()
        tasks = checked(owner, "POST", f"/api/knowledge-base/{kb_id}/documents/process", json=uploaded).json()["tasks"]
        task_id = tasks[0]["task_id"]
        # Windows cold-start embedding imports can exceed four minutes.
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            task = checked(owner, "GET", f"/api/knowledge-base/{kb_id}/documents/tasks", params={"task_ids": str(task_id)}).json()[str(task_id)]
            if task["status"] == "completed": break
            assert task["status"] != "failed", "Synthetic private processing failed"
            time.sleep(2)
        else: raise RuntimeError("Private processing timed out")
        private_id = checked(owner, "GET", f"/api/knowledge-base/{kb_id}").json()["documents"][0]["id"]
        public_task = checked(owner, "POST", "/api/corpus/documents/upload", expected=202,
            files={"file": (f"{name}-public.pdf", pdf(name, True), "application/pdf")}).json()["id"]
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            task = checked(owner, "GET", f"/api/corpus/tasks/{public_task}").json()
            if task["status"] == "completed": public_id = task["document_id"]; break
            assert task["status"] != "failed", "Synthetic public processing failed"
            time.sleep(2)
        else: raise RuntimeError("Public processing timed out")
        checked(owner, "POST", f"/api/corpus/documents/{public_id}/publish")
        passed("Synthetic private/public PDF upload and processing/indexing")
        if extra_acceptance:
            extra_acceptance(owner, other, private_id, public_id, passed)
        request = {"request_id": str(uuid.uuid4()), "scope": "both", "document_ids": [private_id, public_id],
                   "criteria": ["objective", "methodology", "findings", "limitations"], "question": "Compare the two fabricated irrigation studies."}
        checked(other, "POST", "/api/insights/comparisons", expected=404, json=request)
        checked(owner, "POST", "/api/insights/comparisons", expected=404, json={**request, "scope": "public"})
        started = time.monotonic()
        response = checked(owner, "POST", "/api/insights/comparisons", json=request).json()
        elapsed = round(time.monotonic() - started, 2)
        assert response["status"] == "complete"
        result = response["result"]
        assert len(result["criteria"]) == 4 and len(result["documents"]) == 2
        claims = [claim for row in result["criteria"] for cell in row["values"] for claim in cell["claims"]]
        assert len(claims) >= 4
        for row in result["criteria"]:
            for cell in row["values"]:
                for claim in cell["claims"]:
                    assert claim["citations"] and all(ref["document_id"] == cell["document_id"] and ref["page"] == 0 for ref in claim["citations"])
        assert "23" in json.dumps(result) and "18" in json.dumps(result)
        run_id = response["id"]
        assert checked(owner, "GET", f"/api/insights/comparisons/{run_id}").json() == response
        assert checked(owner, "POST", "/api/insights/comparisons", json=request).json() == response
        checked(other, "GET", f"/api/insights/comparisons/{run_id}", expected=404)
        db.rollback()
        assert db.query(AnalysisEvidence).filter_by(analysis_id=run_id).count() >= 2
        assert checked(owner, "GET", f"/api/knowledge-base/{kb_id}/documents/{private_id}/content?inline=true").content.startswith(b"%PDF")
        assert checked(other, "GET", f"/api/corpus/documents/{public_id}/content?inline=true").content.startswith(b"%PDF")
        checked(other, "GET", f"/api/knowledge-base/{kb_id}/documents/{private_id}/content", expected=404)
        passed(f"Real provider comparison, per-paper citations, saved reopening and idempotency ({elapsed}s)")
        checked(owner, "POST", f"/api/corpus/documents/{public_id}/unpublish")
        checked(owner, "GET", f"/api/insights/comparisons/{run_id}", expected=404)
        passed("Revocation hides saved results and private source remains owner-only")
        Path(f".local/tmp/{phase}-live-result.json").write_text(json.dumps({"duration_seconds": elapsed, "synthetic_result": response}, default=str))
    finally:
        if public_id is not None:
            checked(clients[0], "DELETE", f"/api/corpus/documents/{public_id}")
        elif public_task is not None:
            checked(clients[0], "DELETE", f"/api/corpus/tasks/{public_task}")
        if kb_id is not None:
            # Never override the lifecycle's active-processing protection.
            deadline = time.monotonic() + 600
            while True:
                response = clients[0].delete(f"/api/knowledge-base/{kb_id}")
                if response.status_code == 200:
                    break
                if response.status_code != 409 or time.monotonic() >= deadline:
                    raise RuntimeError(f"Synthetic collection cleanup pending: HTTP {response.status_code}; KB {kb_id}")
                time.sleep(3)
        db.rollback()
        db.query(AnalysisRun).filter(AnalysisRun.user_id.in_(users)).delete(synchronize_session=False)
        db.query(AuthSession).filter(AuthSession.user_id.in_(users)).delete(synchronize_session=False)
        db.query(AdminAllowlist).filter(AdminAllowlist.email == f"{name}_owner@example.invalid").delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(users)).delete(synchronize_session=False)
        db.commit()
        assert snapshot(db, tables) == before, "Existing application data changed; inspect concurrent activity"
        assert objects() == before_objects, "Object baseline changed"
        assert vector_ids() == before_vectors, "Vector baseline changed"
        for client in clients: client.close()
        db.close()
        passed("Synthetic cleanup; original SQL rows, MinIO objects and Chroma vector IDs unchanged")
    Path(f".local/tmp/{phase}-live-receipt.json").write_text(json.dumps({"passed": checks}))


if __name__ == "__main__":
    run()
