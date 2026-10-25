"""Opt-in synthetic Analyze acceptance plus the Phase 15 regression/cleanup gate.

PHASE16_LIVE_ACCEPTANCE=1 python -m tests.phase16_live_acceptance
Only fabricated papers in a temporary department can enter related discovery.
"""
import json
import time
import httpx
from pathlib import Path
from uuid import uuid4
from app.db.session import SessionLocal
from app.models import Department, AnalysisRun, AnalysisDocument, AnalysisEvidence
from tests.phase15_live_acceptance import run, pdf


def check(owner, other, private_id, public_id, passed, focus="overview"):
    department = related_id = task_id = None
    phase = {"contradictions":"phase17", "candidate_gaps":"phase18"}.get(focus,"phase16")
    code = "T" + phase[-2:] + uuid4().hex[:8].upper()
    def request(client, method, path, expected=200, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:240]}")
        return response
    try:
        department = request(owner, "POST", "/api/departments", 201, json={"name": "Synthetic " + phase + " " + code, "code": code}).json()["id"]
        request(owner, "PATCH", f"/api/corpus/documents/{public_id}/metadata", json={"title": "Synthetic irrigation study A", "department_id": department})
        task_id = request(owner, "POST", "/api/corpus/documents/upload", 202,
            files={"file": (f"{code}-related.pdf", pdf(code, True, contradiction=focus == "contradictions"), "application/pdf")}).json()["id"]
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            task = request(owner, "GET", f"/api/corpus/tasks/{task_id}").json()
            if task["status"] == "completed": related_id = task["document_id"]; break
            assert task["status"] != "failed", "Related fixture processing failed"
            time.sleep(2)
        else: raise RuntimeError("Related processing timed out")
        request(owner, "PATCH", f"/api/corpus/documents/{related_id}/metadata", json={"title": "Synthetic irrigation related study", "department_id": department})
        request(owner, "POST", f"/api/corpus/documents/{related_id}/publish")
        body = {"request_id": str(uuid4()), "scope": "both", "document_ids": [private_id, public_id],
                "question": "What do the synthetic irrigation studies show, and what are their limits?", "include_related": True}
        if focus == "contradictions":
            body.update(focus=focus, question="Interpret evidence about whether drip irrigation reduces water use. Compare the 23 percent and 0 percent greenhouse findings; consider the field study's context. Do not infer which study is valid.")
        elif focus == "candidate_gaps":
            body.update(focus=focus, question="Identify a candidate gap within these retrieved studies concerning their stated single-season limitation and requested multi-season validation. Quote the source passages exactly; do not assert global novelty.")
        request(other, "POST", "/api/insights/analyses", 404, json=body)
        started = time.monotonic()
        disconnected = False
        try:
            result = request(owner, "POST", "/api/insights/analyses", json=body, timeout=5 if focus != "overview" else 180).json()
        except httpx.ReadTimeout:
            disconnected = True
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline:
                recovered = owner.get(f'/api/insights/analyses/requests/{body["request_id"]}')
                if recovered.status_code == 200:
                    result = recovered.json()
                    if result['status'] != 'processing': break
                elif recovered.status_code != 404:
                    raise RuntimeError(f'Recovery HTTP {recovered.status_code}')
                time.sleep(3)
            else: raise RuntimeError('Saved analysis did not finish within the acceptance window')
        elapsed = round(time.monotonic() - started, 2)
        assert result["status"] == "complete", (result["status"], result.get("error_message"))
        data = result["result"]
        assert len(data["profiles"]) == 2
        assert len(data["sections"]) == (7 if focus == "overview" else 0)
        assert data["coverage"]["candidate_count"] == 1 and data["coverage"]["related_count"] == 1
        assert {d["id"] for d in data["documents"]} == {private_id, public_id, related_id}
        assert next(d for d in data["documents"] if d["id"] == related_id)["role"] == "related"
        for profile in data["profiles"]:
            assert len(profile["fields"]) == 6
            for field in profile["fields"]:
                for claim in field["claims"]:
                    assert claim["citations"] and all(c["document_id"] == profile["document_id"] for c in claim["citations"])
        if focus == "contradictions":
            relationships = data['interpretations']
            assert relationships and data['focus'] == focus
            assert any({private_id, related_id}.issubset({c['document_id'] for c in item['supporting'] + item['contradicting']}) and item['contradicting'] for item in relationships)
            claims = [item['interpretation'] for item in relationships] + [factor for item in relationships for factor in item['context_factors']]
            assert all(len({c['document_id'] for c in item['interpretation']['citations']}) >= 2 for item in relationships)
        elif focus == "candidate_gaps":
            gaps = data['candidate_gaps']
            assert gaps and data['focus'] == focus
            claims = [item['evidence_pattern'] for item in gaps]
            for item in gaps:
                assert 'within the indexed corpus' in item['qualification']
                for anchor in item['evidence_quotes']:
                    assert ' '.join(anchor['quote'].split()) in ' '.join(anchor['citation']['excerpt'].split())
        else:
            claims = [c for section in data["sections"] for c in section["claims"]]
            assert len(claims) >= 3
        for claim in claims:
            assert claim["citations"] and all(c["document_id"] in {private_id, public_id, related_id} and c["page"] == 0 for c in claim["citations"])
        assert "23" in json.dumps(data) and "18" in json.dumps(data)
        identity = result["id"]
        assert request(owner, "GET", f"/api/insights/analyses/{identity}").json() == result
        recovery_path = f'/api/insights/analyses/requests/{body["request_id"]}'
        assert request(owner, "GET", recovery_path).json() == result
        request(other, "GET", recovery_path, 404)
        assert request(owner, "POST", "/api/insights/analyses", json=body).json() == result
        request(other, "GET", f"/api/insights/analyses/{identity}", 404)
        with SessionLocal() as db:
            assert db.get(AnalysisRun, identity).analysis_type == ("analyze" if focus == "overview" else focus)
            assert db.query(AnalysisDocument).filter_by(analysis_id=identity, role="related").count() == 1
            assert db.query(AnalysisEvidence).filter_by(analysis_id=identity).count() >= 3
        request(owner, "POST", f"/api/corpus/documents/{related_id}/unpublish")
        request(owner, "GET", f"/api/insights/analyses/{identity}", 404)
        request(owner, "GET", recovery_path, 404)
        passed(f"{phase}: profiles, bounded related discovery, {focus}, citations, saved recovery (disconnected={disconnected}) and related-source revocation ({elapsed}s)")
        Path(f".local/tmp/{phase}-analysis-result.json").write_text(json.dumps({"duration_seconds": elapsed, "synthetic_result": result}, default=str))
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
