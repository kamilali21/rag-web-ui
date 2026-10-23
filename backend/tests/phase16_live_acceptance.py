"""Opt-in synthetic Analyze acceptance plus the Phase 15 regression/cleanup gate.

PHASE16_LIVE_ACCEPTANCE=1 python -m tests.phase16_live_acceptance
Only fabricated papers in a temporary department can enter related discovery.
"""
import json
import time
from pathlib import Path
from uuid import uuid4
from app.db.session import SessionLocal
from app.models import Department, AnalysisRun, AnalysisDocument, AnalysisEvidence
from tests.phase15_live_acceptance import run, pdf


def check(owner, other, private_id, public_id, passed):
    department = related_id = task_id = None
    code = "T16" + uuid4().hex[:8].upper()
    def request(client, method, path, expected=200, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:240]}")
        return response
    try:
        department = request(owner, "POST", "/api/departments", 201, json={"name": "Synthetic Phase16 " + code, "code": code}).json()["id"]
        request(owner, "PATCH", f"/api/corpus/documents/{public_id}/metadata", json={"title": "Synthetic irrigation study A", "department_id": department})
        task_id = request(owner, "POST", "/api/corpus/documents/upload", 202,
            files={"file": (f"{code}-related.pdf", pdf(code, True), "application/pdf")}).json()["id"]
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            task = request(owner, "GET", f"/api/corpus/tasks/{task_id}").json()
            if task["status"] == "completed": related_id = task["document_id"]; break
            assert task["status"] != "failed", "Related fixture processing failed"
            time.sleep(2)
        else: raise RuntimeError("Related processing timed out")
        request(owner, "PATCH", f"/api/corpus/documents/{related_id}/metadata", json={"title": "Synthetic irrigation field study B", "department_id": department})
        request(owner, "POST", f"/api/corpus/documents/{related_id}/publish")
        body = {"request_id": str(uuid4()), "scope": "both", "document_ids": [private_id, public_id],
                "question": "What do the synthetic irrigation studies show, and what are their limits?", "include_related": True}
        request(other, "POST", "/api/insights/analyses", 404, json=body)
        started = time.monotonic()
        result = request(owner, "POST", "/api/insights/analyses", json=body).json()
        elapsed = round(time.monotonic() - started, 2)
        assert result["status"] == "complete", result["status"]
        data = result["result"]
        assert len(data["profiles"]) == 2 and len(data["sections"]) == 7
        assert data["coverage"]["candidate_count"] == 1 and data["coverage"]["related_count"] == 1
        assert {d["id"] for d in data["documents"]} == {private_id, public_id, related_id}
        assert next(d for d in data["documents"] if d["id"] == related_id)["role"] == "related"
        for profile in data["profiles"]:
            assert len(profile["fields"]) == 6
            for field in profile["fields"]:
                for claim in field["claims"]:
                    assert claim["citations"] and all(c["document_id"] == profile["document_id"] for c in claim["citations"])
        claims = [c for section in data["sections"] for c in section["claims"]]
        assert len(claims) >= 3
        for claim in claims:
            assert claim["citations"] and all(c["document_id"] in {private_id, public_id, related_id} and c["page"] == 0 for c in claim["citations"])
        assert "23" in json.dumps(data) and "18" in json.dumps(data)
        identity = result["id"]
        assert request(owner, "GET", f"/api/insights/analyses/{identity}").json() == result
        assert request(owner, "POST", "/api/insights/analyses", json=body).json() == result
        request(other, "GET", f"/api/insights/analyses/{identity}", 404)
        with SessionLocal() as db:
            assert db.get(AnalysisRun, identity).analysis_type == "analyze"
            assert db.query(AnalysisDocument).filter_by(analysis_id=identity, role="related").count() == 1
            assert db.query(AnalysisEvidence).filter_by(analysis_id=identity).count() >= 3
        request(owner, "POST", f"/api/corpus/documents/{related_id}/unpublish")
        request(owner, "GET", f"/api/insights/analyses/{identity}", 404)
        passed(f"Analyze profiles, bounded related discovery, synthesis, citations, saved reopening and related-source revocation ({elapsed}s)")
        Path(".local/tmp/phase16-analysis-result.json").write_text(json.dumps({"duration_seconds": elapsed, "synthetic_result": result}, default=str))
    finally:
        if related_id is not None:
            request(owner, "DELETE", f"/api/corpus/documents/{related_id}")
        elif task_id is not None:
            request(owner, "DELETE", f"/api/corpus/tasks/{task_id}")
        if department is not None:
            request(owner, "PATCH", f"/api/corpus/documents/{public_id}/metadata", json={"department_id": None})
            # There is no department DELETE API; remove only this exact synthetic reference row.
            with SessionLocal() as db:
                db.query(Department).filter_by(id=department, code=code).delete(synchronize_session=False)
                db.commit()


if __name__ == "__main__":
    run(extra_acceptance=check, phase="phase16")
