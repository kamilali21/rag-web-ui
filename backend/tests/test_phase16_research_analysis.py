from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from app.models import AnalysisRun, AnalysisDocument, AnalysisEvidence, DocumentChunk
from app.schemas.research_analysis import PROFILE_FIELDS, SECTIONS, ProfilesDraft, SynthesisDraft, AnalysisRequest
from app.services import research_analysis as service, comparison
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase13_document_summary import rate_limit


def payload(w, **changes):
    return {"request_id": str(uuid4()), "scope": "both", "document_ids": [w.alice_doc.id],
            "question": "irrigation", "include_related": True, **changes}


def model_draft(schema, system, data, max_tokens, label, **_kwargs):
    evidence = data["evidence"]
    if schema is ProfilesDraft:
        return ProfilesDraft(profiles=[{"document_id": identity, "fields": [{"key": key, "claims": [
            {"text": "Irrigation study evidence.", "evidence_ids": [next(e["evidence_id"] for e in evidence if e["document_id"] == identity)]}]
            if key != "future_work" and any(e["document_id"] == identity for e in evidence) else []} for key in PROFILE_FIELDS]} for identity in data["document_ids"]])
    refs = list({e["document_id"]: e["evidence_id"] for e in evidence}.values())
    return SynthesisDraft(sections=[{"key": key, "claims": [{"text": "A qualified evidence-backed interpretation.", "evidence_ids": refs[:5]}]
        if refs and (len(refs) >= 2 or key not in {"common_findings", "methodological_differences", "trends"}) else []} for key in SECTIONS])


@pytest.fixture
def generation(monkeypatch):
    fn = MagicMock(side_effect=model_draft)
    monkeypatch.setattr(comparison, "generate_structured", fn)
    return fn


def post(w, body=None, actor=None):
    return w.client.post("/api/insights/analyses", headers=w.headers(actor or w.alice), json=body or payload(w))


def related(w):
    w.published.academic_metadata.title = "Irrigation evidence"
    w.draft.academic_metadata.title = "Irrigation draft"
    w.db.commit()


def test_profiles_related_discovery_synthesis_persistence(sources, provider, generation):
    w = sources; related(w); body = payload(w)
    response = post(w, body)
    assert response.status_code == 200, response.text
    run = response.json(); result = run["result"]
    assert run["status"] == "complete" and generation.call_count == 2
    assert [(d["id"], d["role"]) for d in result["documents"]] == [(w.alice_doc.id, "selected"), (w.published.id, "related")]
    assert result["coverage"]["candidate_count"] == 1
    assert len(result["profiles"][0]["fields"]) == 6 and len(result["sections"]) == 7
    assert result["profiles"][0]["fields"][-1]["claims"] == []
    for field in result["profiles"][0]["fields"]:
        for claim in field["claims"]:
            assert {c["document_id"] for c in claim["citations"]} == {w.alice_doc.id}
    assert {c["document_id"] for c in result["sections"][2]["claims"][0]["citations"]} == {w.alice_doc.id, w.published.id}
    assert w.db.query(AnalysisEvidence).count() == 2
    assert {s.role for s in w.db.query(AnalysisDocument)} == {"selected", "related"}
    assert post(w, body).json() == run and generation.call_count == 2
    path = f'/api/insights/analyses/{run["id"]}'
    assert w.client.get(path, headers=w.headers(w.alice)).json() == run
    # Type-specific routes cannot accidentally expose another workflow's payload.
    assert w.client.get(f'/api/insights/comparisons/{run["id"]}', headers=w.headers(w.alice)).status_code == 404
    for actor in (w.bob, w.professor, w.superuser):
        assert w.client.get(path, headers=w.headers(actor)).status_code == 404
    assert w.client.get(path).status_code == 401
    # Snapshots survive index rebuilds, but related paper revocation hides the run.
    w.db.query(DocumentChunk).delete(); w.db.commit()
    assert w.client.get(path, headers=w.headers(w.alice)).status_code == 200
    w.published.academic_metadata.publication_status = "archived"; w.db.commit()
    assert w.client.get(path, headers=w.headers(w.alice)).status_code == 404


def test_recover_request_checks_owner_type_and_current_sources(sources, provider, generation):
    w = sources; body = payload(w, include_related=False)
    result = post(w, body).json()
    path = f'/api/insights/analyses/requests/{body["request_id"]}'
    assert w.client.get(path, headers=w.headers(w.alice)).json() == result
    for actor in (w.bob, w.professor, w.superuser):
        assert w.client.get(path, headers=w.headers(actor)).status_code == 404
    assert w.client.get(path).status_code == 401
    assert w.client.get('/api/insights/analyses/requests/not-a-uuid', headers=w.headers(w.alice)).status_code == 422
    row = w.db.get(AnalysisRun, result['id']); row.status = 'processing'; row.result_json = None; w.db.commit()
    assert w.client.get(path, headers=w.headers(w.alice)).json()['status'] == 'processing'
    row.analysis_type = 'compare'; w.db.commit()
    assert w.client.get(path, headers=w.headers(w.alice)).status_code == 404
    row.analysis_type = 'analyze'; w.db.commit()
    w.alice_kb.user_id = w.bob.id; w.db.commit()
    assert w.client.get(path, headers=w.headers(w.alice)).status_code == 404
    assert generation.call_count == 2  # Recovery never makes model calls.


def test_profile_budget_and_correction_include_actual_schema_bounds(sources, provider, monkeypatch):
    import json
    model = MagicMock(); model.bind.return_value = model
    calls = 0
    def invoke(prompt):
        nonlocal calls
        calls += 1
        data = json.loads(prompt[1].content)
        schema = ProfilesDraft if 'document_ids' in data else SynthesisDraft
        draft = model_draft(schema, '', data, 1, '')
        if calls == 1:
            draft.profiles[0].fields[0].claims[0].text = 'x' * 501
        if calls == 2:
            assert 'maxLength' in prompt[-1].content and '500' in prompt[-1].content
        return SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    model.invoke.side_effect = invoke
    monkeypatch.setattr(comparison.LLMFactory, 'create', lambda **kw: model)
    assert post(sources, payload(sources, include_related=False)).status_code == 200
    assert calls == 3
    budgets = [c.kwargs['max_tokens'] for c in model.bind.call_args_list if 'max_tokens' in c.kwargs]
    assert budgets[0] == 4000


@pytest.mark.parametrize("scope,include", [("private", True), ("both", False)])
def test_private_or_disabled_discovery_never_expands(sources, provider, generation, scope, include):
    w = sources; related(w)
    result = post(w, payload(w, scope=scope, include_related=include)).json()["result"]
    assert [d["id"] for d in result["documents"]] == [w.alice_doc.id]
    assert not result["coverage"]["enabled"]
    assert result["sections"][2]["claims"] == []
    assert set(provider.stores) == {w.alice_kb.id}


@pytest.mark.parametrize("target", ["bob_doc", "draft", "archived", "failed", "fake"])
def test_invalid_selection_never_generates(sources, generation, target):
    w = sources
    assert post(w, payload(w, document_ids=[getattr(w, target).id])).status_code == 404
    generation.assert_not_called()
    assert w.db.query(AnalysisRun).count() == 0


@pytest.mark.parametrize("changes", [{"document_ids": []}, {"document_ids": [1]*6}, {"document_ids": [True]},
    {"document_ids": [1,1]}, {"scope": "all"}, {"include_related": "true"}, {"question": "x"*1001}, {"analysis_types": ["gaps"]}])
def test_strict_requests(sources, changes):
    assert post(sources, payload(sources, **changes)).status_code == 422


@pytest.mark.parametrize("fault", ["foreign_profile", "unknown_citation", "profile_fields", "missing_profile", "sections", "one_paper_crossstudy"])
def test_bad_output_not_saved(sources, provider, monkeypatch, fault):
    w = sources
    def invalid(*args, **_kwargs):
        value = model_draft(*args)
        if isinstance(value, ProfilesDraft):
            if fault == "foreign_profile": value.profiles[0].document_id = w.bob_doc.id
            if fault == "unknown_citation": value.profiles[0].fields[0].claims[0].evidence_ids = ["E999"]
            if fault == "profile_fields": value.profiles[0].fields[-1].key = "objective"
            if fault == "missing_profile": value.profiles = []
        else:
            if fault == "sections": value.sections[-1].key = "summary"
            if fault == "one_paper_crossstudy": value.sections[2].claims = value.sections[0].claims
        return value
    monkeypatch.setattr(comparison, "generate_structured", invalid)
    assert post(w, payload(w, include_related=False)).status_code == 502
    assert w.db.query(AnalysisRun).one().status == "failed"
    assert w.db.query(AnalysisRun).one().result_json is None
    assert w.db.query(AnalysisEvidence).count() == 0


@pytest.mark.parametrize("stage", ["profiles", "synthesis"])
def test_revocation_during_generation_fails_closed(sources, provider, monkeypatch, stage):
    w = sources
    def revoke(*args, **_kwargs):
        value = model_draft(*args)
        if (stage == "profiles" and isinstance(value, ProfilesDraft)) or (stage == "synthesis" and isinstance(value, SynthesisDraft)):
            w.published.academic_metadata.publication_status = "archived"; w.db.commit()
        return value
    monkeypatch.setattr(comparison, "generate_structured", revoke)
    assert post(w, payload(w, scope="public", document_ids=[w.published.id])).status_code == 404
    assert w.db.query(AnalysisRun).one().result_json is None


def test_no_evidence_abstains_without_model_or_discovery(sources, monkeypatch, generation):
    monkeypatch.setattr(service, "search_documents", lambda *a, **k: [])
    run = post(sources).json()
    assert run["status"] == "insufficient_evidence"
    generation.assert_not_called()
    assert not run["result"]["coverage"]["enabled"]


def test_changed_chunk_rejected_before_model(sources, monkeypatch, generation):
    w = sources
    monkeypatch.setattr(service, "search_documents", lambda *a, **k: [{"content": "forged content", "metadata": {
        "document_id": w.alice_doc.id, "kb_id": w.alice_kb.id, "scope": "private", "chunk_id": f"chunk-{w.alice_doc.id}"}}])
    assert post(w).status_code == 409
    generation.assert_not_called()


def test_request_uuid_cannot_change_options(sources, provider, generation):
    body = payload(sources); assert post(sources, body).status_code == 200
    assert post(sources, {**body, "question": "changed"}).status_code == 409


@pytest.mark.parametrize("failures,wait,status", [(1,"0",200), (2,"0",503), (1,"60",503)])
def test_profile_provider_retry_is_bounded(sources, provider, monkeypatch, failures, wait, status):
    import json
    model = MagicMock(); model.bind.return_value = model
    def invoke(prompt):
        nonlocal failures
        if failures:
            failures -= 1; raise rate_limit(wait)
        data = json.loads(prompt[1].content)
        schema = ProfilesDraft if "document_ids" in data else SynthesisDraft
        return SimpleNamespace(content=model_draft(schema, "", data, 1, "").model_dump_json(), response_metadata={})
    model.invoke.side_effect = invoke
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    sleeper = MagicMock(); monkeypatch.setattr(comparison.time, "sleep", sleeper)
    assert post(sources, payload(sources, include_related=False)).status_code == status
    assert model.invoke.call_count == (3 if status == 200 else 1 if wait == "60" else 2)
    assert sleeper.call_count <= 1


def test_discovery_candidates_and_related_count_bounded(sources, provider, generation):
    from app.models import Document, AcademicDocumentMetadata
    from app.models.knowledge import ProcessingTask
    w = sources
    for n in range(24):
        doc = Document(knowledge_base_id=w.corpus.id, file_name=f"irrigation-{n}.pdf", file_path=f"synthetic/{n}", file_size=1, content_type="application/pdf")
        doc.academic_metadata = AcademicDocumentMetadata(title=f"Irrigation {n}", publication_status="published")
        w.db.add(doc); w.db.flush()
        w.db.add(ProcessingTask(knowledge_base_id=w.corpus.id, document_id=doc.id, status="completed"))
        w.db.add(DocumentChunk(id=f"chunk-{doc.id}", kb_id=w.corpus.id, document_id=doc.id, file_name=doc.file_name, hash=str(n), chunk_metadata={"page_content": "Irrigation test", "page": 0}))
        w.source_documents.append(doc)
    w.db.commit()
    response = post(w); assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["coverage"]["candidate_count"] == 20
    assert result["coverage"]["related_count"] == 3
    assert len(result["documents"]) == 4
    assert generation.call_count == 2


def test_free_router_does_not_disable_mandatory_reasoning(monkeypatch):
    monkeypatch.setattr(comparison.settings, "CHAT_PROVIDER", "openai")
    monkeypatch.setattr(comparison.settings, "OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    model = MagicMock(); model.bind.return_value = model
    draft = ProfilesDraft(profiles=[{"document_id": 1, "fields": [{"key": key, "claims": []} for key in PROFILE_FIELDS]}])
    model.invoke.return_value = SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    comparison.generate_structured(ProfilesDraft, service.PROFILE_PROMPT, {}, 1800, "Profiles")
    config = model.bind.call_args.kwargs
    assert config["extra_body"] == {"reasoning": {"effort": "low", "exclude": True}, "provider": {"require_parameters": True}}
    assert config["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("status,failures,expected_calls", [(404,1,2),(503,1,2),(502,2,2),(401,1,1),(400,1,1)])
def test_transient_router_failure_retries_only_once(monkeypatch, status, failures, expected_calls):
    import httpx
    from openai import APIStatusError
    from fastapi import HTTPException
    response = httpx.Response(status, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    error = APIStatusError("Synthetic failure", response=response, body={"code":status})
    draft = ProfilesDraft(profiles=[{"document_id":1,"fields":[{"key":key,"claims":[]} for key in PROFILE_FIELDS]}])
    model = MagicMock(); model.bind.return_value = model
    model.invoke.side_effect = [error]*failures + [SimpleNamespace(content=draft.model_dump_json(), response_metadata={})]
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    monkeypatch.setattr(comparison.time, "sleep", MagicMock())
    if status in {404,503}:
        assert comparison.generate_structured(ProfilesDraft, "", {}, 1800, "Profiles") == draft
    else:
        with pytest.raises(HTTPException) as failure:
            comparison.generate_structured(ProfilesDraft, "", {}, 1800, "Profiles")
        assert failure.value.status_code == 503
    assert model.invoke.call_count == expected_calls


@pytest.mark.parametrize("failures", [1,2])
def test_sdk_truncation_uses_one_bounded_correction(monkeypatch, failures):
    from openai import LengthFinishReasonError
    from openai.types.chat import ChatCompletion
    from fastapi import HTTPException
    error = LengthFinishReasonError(completion=ChatCompletion(id="test", choices=[], created=0, model="synthetic", object="chat.completion"))
    draft = ProfilesDraft(profiles=[{"document_id":1,"fields":[{"key":key,"claims":[]} for key in PROFILE_FIELDS]}])
    model = MagicMock(); model.bind.return_value = model
    model.invoke.side_effect = [error]*failures + [SimpleNamespace(content=draft.model_dump_json(), response_metadata={})]
    monkeypatch.setattr(comparison.LLMFactory, "create", lambda **kw: model)
    if failures == 1:
        assert comparison.generate_structured(ProfilesDraft, "", {}, 7000, "Profiles") == draft
    else:
        with pytest.raises(HTTPException) as failure:
            comparison.generate_structured(ProfilesDraft, "", {}, 7000, "Profiles")
        assert failure.value.status_code == 502
    assert model.invoke.call_count == 2
    assert model.bind.call_args.kwargs["max_tokens"] == 12000


@pytest.mark.parametrize('failures', [1, 2])
def test_null_provider_choices_uses_shared_retry_limit(monkeypatch, failures):
    from langchain_openai import ChatOpenAI
    from fastapi import HTTPException
    draft = ProfilesDraft(profiles=[{'document_id': 1, 'fields': [{'key': key, 'claims': []} for key in PROFILE_FIELDS]}])
    model = MagicMock(); model.bind.return_value = model
    calls = 0
    def invoke(prompt):
        nonlocal calls
        calls += 1
        if calls <= failures:
            # Actual installed adapter reproduces the HTTP-200/null-choices error.
            return ChatOpenAI._create_chat_result(None, {'choices': None})
        return SimpleNamespace(content=draft.model_dump_json(), response_metadata={})
    model.invoke.side_effect = invoke
    monkeypatch.setattr(comparison.LLMFactory, 'create', lambda **kw: model)
    monkeypatch.setattr(comparison.time, 'sleep', MagicMock())
    if failures == 1:
        assert comparison.generate_structured(ProfilesDraft, '', {}, 4000, 'Profiles') == draft
    else:
        with pytest.raises(HTTPException) as failure:
            comparison.generate_structured(ProfilesDraft, '', {}, 4000, 'Profiles')
        assert failure.value.status_code == 503
    assert calls == 2


def test_application_typeerror_is_not_retried(monkeypatch):
    from fastapi import HTTPException
    model = MagicMock(); model.bind.return_value = model
    model.invoke.side_effect = TypeError('Synthetic application failure')
    monkeypatch.setattr(comparison.LLMFactory, 'create', lambda **kw: model)
    with pytest.raises(HTTPException):
        comparison.generate_structured(ProfilesDraft, '', {}, 4000, 'Profiles')
    assert model.invoke.call_count == 1
