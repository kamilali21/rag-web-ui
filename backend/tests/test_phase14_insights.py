"""Insights discovery/selection must retain the shared RAG authorization boundary."""
import pytest
from app.models import AcademicDocumentMetadata, Department
from app.models.knowledge import ProcessingTask
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources


def catalog(w, scope="public", actor=None, **params):
    return w.client.get("/api/insights/documents", headers=w.headers(actor or w.alice), params={"scope": scope, **params})


def selection(w, ids, scope="both", mode="compare", actor=None):
    return w.client.post("/api/insights/selection", headers=w.headers(actor or w.alice),
        json={"scope": scope, "mode": mode, "document_ids": ids})


def test_scope_union_and_safe_projection(sources):
    w = sources
    for scope, expected in [("public", {w.published.id}), ("private", {w.alice_doc.id}), ("both", {w.published.id, w.alice_doc.id})]:
        result = catalog(w, scope)
        assert result.status_code == 200
        assert {item["id"] for item in result.json()["items"]} == expected
        assert "file_path" not in result.text and "hashed_password" not in result.text
    assert catalog(w, "private", w.professor).json()["items"] == []
    assert {r["id"] for r in catalog(w, "both", w.bob).json()["items"]} == {w.bob_doc.id, w.published.id}


def test_filters_and_bounded_cursor(sources):
    w = sources
    department = Department(name="Synthetic Agronomy", code="SYNAGR", is_active=True)
    w.db.add(department); w.db.flush()
    metadata = w.published.academic_metadata
    metadata.title = "Water 100% efficient"
    metadata.authors_text = "Ayesha Researcher"
    metadata.abstract = "Scheduled irrigation in greenhouse plots"
    metadata.department_id = department.id
    metadata.document_type = "paper"
    metadata.publication_year = 2025
    w.db.commit()
    query = dict(search="greenhouse", author="Ayesha", department_id=department.id,
                 document_type="paper", year_from=2024, year_to=2026)
    assert catalog(w, **query).json()["items"][0]["id"] == w.published.id
    assert catalog(w, **{**query, "year_to": 2024}).json()["items"] == []
    assert catalog(w, search="%").json()["items"][0]["id"] == w.published.id
    assert catalog(w, search="_").json()["items"] == []
    first = catalog(w, "both", limit=1).json()
    assert first["has_more"] and len(first["items"]) == 1
    second = catalog(w, "both", limit=1, before_id=first["items"][0]["id"]).json()
    assert not second["has_more"]
    assert second["items"][0]["id"] != first["items"][0]["id"]


@pytest.mark.parametrize("query", [{"limit": 51}, {"before_id": -1}, {"year_from": 2026, "year_to": 2024}, {"scope": "all"}, {"search": "a" * 201}])
def test_invalid_catalog_parameters(sources, query):
    assert catalog(sources, **query).status_code == 422


def test_selection_preserves_real_ids_order_and_scope(sources):
    w = sources
    result = selection(w, [w.alice_doc.id, w.published.id])
    assert result.status_code == 200
    assert [(r["id"], r["scope"]) for r in result.json()["documents"]] == [(w.alice_doc.id, "private"), (w.published.id, "public")]


@pytest.mark.parametrize("target", ["bob_doc", "draft", "archived", "failed", "fake"])
def test_foreign_unready_and_unpublished_ids_rejected_as_whole(sources, target):
    w = sources
    result = selection(w, [w.alice_doc.id, getattr(w, target).id])
    assert result.status_code == 404 and "documents" not in result.json()
    detail = w.client.get(f"/api/insights/documents/{getattr(w, target).id}?scope=both", headers=w.headers(w.alice))
    assert detail.status_code == 404


def test_selection_rechecks_archival_and_latest_processing_state(sources):
    w = sources
    assert selection(w, [w.published.id], "public", "analyse").status_code == 200
    w.published.academic_metadata.publication_status = "archived"
    w.db.commit()
    assert selection(w, [w.published.id], "public", "analyse").status_code == 404
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_id=w.alice_doc.id, status="processing")); w.db.commit()
    assert selection(w, [w.alice_doc.id], "private", "analyse").status_code == 404
    assert catalog(w, "both").json()["items"] == []


@pytest.mark.parametrize("ids,mode", [([], "analyse"), ([1], "compare"), ([1, 1], "compare"), ([True], "analyse"), (["1"], "analyse"), ([-1], "analyse"), ([1,2,3,4,5,6], "compare")])
def test_invalid_selection_shape(sources, ids, mode):
    assert selection(sources, ids, mode=mode).status_code == 422


def test_admin_has_no_private_bypass_and_scope_cannot_be_forged(sources):
    w = sources
    assert selection(w, [w.alice_doc.id], "both", "analyse", w.professor).status_code == 404
    assert selection(w, [w.alice_doc.id], "public", "analyse").status_code == 404
    assert selection(w, [w.published.id], "private", "analyse").status_code == 404


def test_authentication_and_extra_fields(sources):
    w = sources
    assert w.client.get("/api/insights/documents").status_code == 401
    assert w.client.post("/api/insights/selection", json={"document_ids": [1], "scope": "public", "mode": "analyse"}).status_code == 401
    assert w.client.post("/api/insights/selection", headers=w.headers(w.alice), json={
        "document_ids": [w.published.id], "scope": "public", "mode": "analyse", "include_unpublished": True}).status_code == 422
