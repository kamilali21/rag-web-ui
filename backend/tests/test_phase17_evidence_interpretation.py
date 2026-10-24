from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.models import AnalysisRun, AnalysisDocument, AnalysisEvidence
from app.schemas.research_analysis import ProfilesDraft
from app.schemas.evidence_interpretation import InterpretationDraft
from app.services import comparison, research_analysis, evidence_interpretation
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase16_research_analysis import model_draft, payload, post


def body(w, **changes):
    return payload(w, document_ids=[w.alice_doc.id, w.published.id], focus='contradictions', include_related=False, **changes)


def relationship(refs):
    return {'claim': 'The selected study reports reduced water use.', 'supporting': [refs[0]],
        'contradicting': [refs[1]], 'qualifying': [],
        'interpretation': {'text': 'The retrieved findings differ; their cause cannot be established here.', 'evidence_ids': refs[:2]},
        'context_factors': [{'key': 'methodology', 'explanation': {'text': 'The reported settings may affect comparability.', 'evidence_ids': refs[:2]}}]}


def draft(schema, system, data, budget, label):
    if schema is ProfilesDraft:
        return model_draft(schema, system, data, budget, label)
    refs = list({e['document_id']: e['evidence_id'] for e in data['evidence']}.values())
    return InterpretationDraft(relationships=[relationship(refs)])


@pytest.fixture
def generation(monkeypatch):
    fn = MagicMock(side_effect=draft); monkeypatch.setattr(comparison, 'generate_structured', fn)
    return fn


def test_interpretation_saved_citations_permissions_replay_and_revocation(sources, provider, generation):
    w = sources; request = body(w)
    response = post(w, request); assert response.status_code == 200, response.text
    run = response.json(); data = run['result']; item = data['interpretations'][0]
    assert run['status'] == 'complete' and data['focus'] == 'contradictions' and data['sections'] == []
    assert item['label'] == 'Potential disagreement'
    assert {c['document_id'] for c in item['supporting']} == {w.alice_doc.id}
    assert {c['document_id'] for c in item['contradicting']} == {w.published.id}
    assert len(item['interpretation']['citations']) == 2
    assert item['context_factors'][0]['title'] == 'Methodology'
    assert w.db.get(AnalysisRun, run['id']).analysis_type == 'contradictions'
    assert w.db.query(AnalysisDocument).count() == 2 and w.db.query(AnalysisEvidence).count() == 2
    assert post(w, request).json() == run and generation.call_count == 2
    assert post(w, {**request, 'focus': 'overview'}).status_code == 409
    paths = [f'/api/insights/analyses/{run["id"]}', f'/api/insights/analyses/requests/{request["request_id"]}']
    for path in paths:
        assert w.client.get(path, headers=w.headers(w.alice)).json() == run
        assert w.client.get(path).status_code == 401
        for actor in (w.bob, w.professor, w.superuser):
            assert w.client.get(path, headers=w.headers(actor)).status_code == 404
    assert w.client.get(f'/api/insights/comparisons/{run["id"]}', headers=w.headers(w.alice)).status_code == 404
    w.published.academic_metadata.publication_status = 'archived'; w.db.commit()
    for path in paths:
        assert w.client.get(path, headers=w.headers(w.alice)).status_code == 404


@pytest.mark.parametrize('changes,status', [({'focus':'gaps'},422), ({'document_ids':[1]},422), ({'scope':'private'},404)])
def test_request_boundaries(sources, generation, changes, status):
    request = {**body(sources), **changes}
    assert post(sources, request).status_code == status
    generation.assert_not_called()


@pytest.mark.parametrize('target', ['bob_doc', 'draft', 'archived', 'failed'])
def test_private_and_unpublished_papers_never_generate(sources, generation, target):
    w = sources
    assert post(w, {**body(w), 'document_ids': [w.alice_doc.id, getattr(w, target).id]}).status_code == 404
    generation.assert_not_called()


@pytest.mark.parametrize('fault', ['unknown', 'overlapping_roles', 'duplicate', 'one_paper', 'missing_side', 'unknown_factor_evidence', 'duplicate_factor'])
def test_invalid_relationships_never_saved(sources, provider, monkeypatch, fault):
    def invalid(*args):
        value = draft(*args)
        if isinstance(value, InterpretationDraft):
            item = value.relationships[0]
            if fault == 'unknown': item.supporting = ['E999']
            if fault == 'overlapping_roles': item.qualifying = list(item.supporting)
            if fault == 'duplicate': item.supporting *= 2
            if fault == 'one_paper': item.contradicting = []; item.interpretation.evidence_ids = item.supporting
            if fault == 'missing_side': item.interpretation.evidence_ids = item.supporting
            if fault == 'unknown_factor_evidence': item.context_factors[0].explanation.evidence_ids = ['E999']
            if fault == 'duplicate_factor': item.context_factors *= 2
        return value
    monkeypatch.setattr(comparison, 'generate_structured', invalid)
    assert post(sources, body(sources)).status_code == 502
    row = sources.db.query(AnalysisRun).one()
    assert row.status == 'failed' and row.result_json is None
    assert sources.db.query(AnalysisEvidence).count() == 0


def test_three_roles_are_cited_and_factors_cannot_escape_relationship():
    evidence = [{'evidence_id': f'E{i}', 'document_id': i} for i in range(1, 5)]
    item = relationship(['E1','E2']); item['qualifying'] = ['E3']; item['interpretation']['evidence_ids'].append('E3')
    value = InterpretationDraft(relationships=[item])
    result = evidence_interpretation.validate(value, evidence)[0]
    assert result['qualifying'] == [evidence[2]]
    # E4 is retrieved but does not belong to this relationship.
    value.relationships[0].context_factors[0].explanation.evidence_ids = ['E4']
    with pytest.raises(HTTPException): evidence_interpretation.validate(value, evidence)


def test_same_paper_disagreement_is_not_cross_paper_even_with_qualifier():
    evidence = [{'evidence_id':'E1','document_id':1}, {'evidence_id':'E2','document_id':1}, {'evidence_id':'E3','document_id':2}]
    item = relationship(['E1','E2']); item['qualifying'] = ['E3']; item['interpretation']['evidence_ids'].append('E3')
    with pytest.raises(HTTPException): evidence_interpretation.validate(InterpretationDraft(relationships=[item]), evidence)


@pytest.mark.parametrize('role,label', [('supporting','Supporting evidence'), ('qualifying','Qualified support')])
def test_non_contradicting_classification(role, label):
    item = relationship(['E1','E2']); item['contradicting'] = []; item[role].append('E2')
    result = evidence_interpretation.validate(InterpretationDraft(relationships=[item]), [{'evidence_id':'E1','document_id':1}, {'evidence_id':'E2','document_id':2}])
    assert result[0]['label'] == label


@pytest.mark.parametrize('evidence_available', [True, False])
def test_insufficient_evidence_is_not_a_claim_of_agreement(sources, provider, monkeypatch, evidence_available):
    def empty(*args):
        return model_draft(*args) if args[0] is ProfilesDraft else InterpretationDraft(relationships=[])
    model = MagicMock(side_effect=empty); monkeypatch.setattr(comparison, 'generate_structured', model)
    if not evidence_available: monkeypatch.setattr(research_analysis, 'search_documents', lambda *a, **k: [])
    response = post(sources, body(sources)); assert response.status_code == 200, response.text
    assert response.json()['status'] == 'insufficient_evidence'
    assert response.json()['result']['interpretations'] == []
    assert model.call_count == (2 if evidence_available else 0)


def test_revocation_while_interpreting_prevents_persistence(sources, provider, monkeypatch):
    def revoke(*args):
        result = draft(*args)
        if isinstance(result, InterpretationDraft):
            sources.published.academic_metadata.publication_status = 'archived'; sources.db.commit()
        return result
    monkeypatch.setattr(comparison, 'generate_structured', revoke)
    assert post(sources, body(sources)).status_code == 404
    assert sources.db.query(AnalysisRun).one().result_json is None
