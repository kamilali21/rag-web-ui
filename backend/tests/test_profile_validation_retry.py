"""Malformed evidence retries share the existing provider budget; never bypass checks."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import AnalysisRun, AnalysisEvidence
from app.schemas.research_analysis import ProfilesDraft, SynthesisDraft
from app.services import comparison
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase16_research_analysis import model_draft, payload, post


@pytest.mark.parametrize("fault", ["foreign_document", "unknown_reference", "duplicate_field", "other_paper_reference"])
@pytest.mark.parametrize("persistent", [False, True])
def test_invalid_profile_can_recover_once_without_persisting_invalid_evidence(sources, provider, monkeypatch, fault, persistent):
    w = sources
    model = MagicMock()
    model.bind.return_value = model
    attempts = 0
    def invoke(prompt):
        nonlocal attempts
        data = json.loads(prompt[1].content)
        schema = ProfilesDraft if "document_ids" in data else SynthesisDraft
        draft = model_draft(schema, "", data, 1, "")
        if schema is ProfilesDraft:
            attempts += 1
            if persistent or attempts == 1:
                profile = draft.profiles[0]
                if fault == "foreign_document":
                    profile.document_id = w.bob_doc.id
                elif fault == "unknown_reference":
                    profile.fields[0].claims[0].evidence_ids = ["E999"]
                elif fault == "duplicate_field":
                    profile.fields[-1].key = "objective"
                else:
                    profile.fields[0].claims[0].evidence_ids = [next(
                        e["evidence_id"] for e in data["evidence"] if e["document_id"] != profile.document_id)]
        return SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    model.invoke.side_effect = invoke
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    response = post(w, payload(w, document_ids=[w.alice_doc.id, w.published.id], include_related=False))
    assert response.status_code == (502 if persistent else 200)
    assert attempts == 2 and model.invoke.call_count == (2 if persistent else 3)
    run = w.db.query(AnalysisRun).one()
    if persistent:
        assert run.status == "failed" and run.result_json is None
        assert w.db.query(AnalysisEvidence).count() == 0
    else:
        assert run.status == "complete"
        for profile in response.json()["result"]["profiles"]:
            for field in profile["fields"]:
                for claim in field["claims"]:
                    assert all(c["document_id"] == profile["document_id"] for c in claim["citations"])
        assert "E999" not in response.text


def test_json_and_evidence_failures_do_not_multiply_retry_budget(sources, provider, monkeypatch):
    model = MagicMock()
    model.bind.return_value = model
    def invalid_evidence(prompt):
        draft = model_draft(ProfilesDraft, "", json.loads(prompt[1].content), 1, "")
        draft.profiles[0].fields[0].claims[0].evidence_ids = ["E999"]
        return SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    responses = iter([None, invalid_evidence])
    def invoke(prompt):
        response = next(responses)
        return response(prompt) if response else SimpleNamespace(content="not JSON", response_metadata={})
    model.invoke.side_effect = invoke
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    assert post(sources, payload(sources, include_related=False)).status_code == 502
    assert model.invoke.call_count == 2


@pytest.mark.parametrize("status", [401, 403, 404, 409])
def test_validation_never_retries_permission_or_source_change_errors(monkeypatch, status):
    model = MagicMock()
    model.bind.return_value = model
    data = {"document_ids": [1], "evidence": []}
    draft = model_draft(ProfilesDraft, "", data, 1, "")
    model.invoke.return_value = SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    def revoked(value):
        raise HTTPException(status, "Unavailable")
    with pytest.raises(HTTPException) as error:
        comparison.generate_structured(ProfilesDraft, "", data, 4000, "Profiles", validate_output=revoked)
    assert error.value.status_code == status and model.invoke.call_count == 1
