"""History never generates, broadens permissions, or trusts client-owned IDs."""
from uuid import uuid4
import pytest
from app.models import AnalysisRun, AnalysisDocument, AnalysisEvidence, DocumentChunk
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase13_document_summary import model_for, request


def saved(w, kind="compare", owner=None, status="complete", document=None, **changes):
    doc = document or w.alice_doc
    run = AnalysisRun(user_id=(owner or w.alice).id, request_id=str(uuid4()), analysis_type=kind,
        scope="public" if doc.id == w.published.id else "private", status=status,
        request_json={"document_ids": [doc.id], "question": "Private question"}, result_json={"secret": "Private output"}, **changes)
    w.db.add(run); w.db.flush()
    w.db.add(AnalysisDocument(analysis_id=run.id, source_document_id=doc.id, document_id=doc.id, document_hash=doc.file_hash))
    w.db.add(AnalysisEvidence(analysis_id=run.id, evidence_id="E1", document_id=doc.id, source_document_id=doc.id,
        chunk_id=f"chunk-{doc.id}", excerpt="Private snapshot", retrieval_rank=1, evidence_hash="a" * 64))
    w.db.commit()
    return run.id


def get(w, path="", actor=None):
    return w.client.get('/api/insights/history' + path, headers=w.headers(actor or w.alice))


def test_owner_only_metadata_and_snapshots_even_for_admins(sources):
    w = sources
    identity = saved(w, document=w.published)
    for actor in (w.bob, w.professor, w.superuser):
        assert get(w, actor=actor).json()['items'] == []
        assert get(w, f'/{identity}', actor).status_code == 404
    assert w.client.get('/api/insights/history').status_code == 401
    assert w.client.get(f'/api/insights/history/{identity}').status_code == 401
    result = get(w).json()['items'][0]
    assert result['available'] and 'result' not in result and 'evidence' not in result
    response = get(w, f'/{identity}')
    assert response.json()['evidence'][0]['excerpt'] == 'Private snapshot'
    assert response.headers['cache-control'] == 'no-store'
    assert get(w).headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('kind', ['summary','compare','analyze','contradictions','candidate_gaps'])
def test_all_types_reopen_without_provider_calls(sources, monkeypatch, kind):
    from app.services.llm.llm_factory import LLMFactory
    monkeypatch.setattr(LLMFactory, 'create', lambda **kwargs: pytest.fail('History must not call a provider'))
    identity = saved(sources, kind)
    assert get(sources, f'/{identity}').json()['analysis_type'] == kind
    assert len(get(sources, '?analysis_type='+kind).json()['items']) == 1


def test_pagination_filters_and_new_insert_do_not_duplicate(sources):
    w=sources
    identities = [saved(w, kind='analyze', status='failed') for _ in range(4)]
    saved(w, kind='compare')
    first=get(w,'?limit=2&analysis_type=analyze&status=failed&scope=private').json()
    assert [r['id'] for r in first['items']] == identities[-1:-3:-1]
    saved(w, kind='analyze', status='failed')
    second=get(w,f'?limit=2&analysis_type=analyze&status=failed&scope=private&before_id={first["next_before_id"]}').json()
    assert [r['id'] for r in second['items']] == identities[1::-1]
    assert second['next_before_id'] is None and not second['has_more']
    assert get(w,'?scope=public').json()['items']==[]


@pytest.mark.parametrize('query',['?limit=0','?limit=51','?before_id=-1','?analysis_type=anything','?scope=all','?status=unknown'])
def test_bounded_validated_queries(sources, query):
    assert get(sources,query).status_code == 422


@pytest.mark.parametrize('change', ['archive', 'hash', 'missing', 'related'])
def test_source_changes_redact_history_and_reject_snapshots(sources, change):
    w=sources
    identity=saved(w, document=w.published)
    if change=='archive': w.published.academic_metadata.publication_status='archived'
    elif change=='hash': w.published.file_hash='new-hash'
    elif change=='missing': w.db.query(AnalysisDocument).filter_by(analysis_id=identity).one().document_id=None
    else:
        w.db.add(AnalysisDocument(analysis_id=identity, source_document_id=w.bob_doc.id, document_id=w.bob_doc.id, role='related'))
    w.db.commit()
    item=get(w).json()['items'][0]
    assert not item['available'] and item['documents']==[] and item['question'] is None
    assert 'Private' not in get(w).text and 'published.txt' not in get(w).text
    assert get(w,f'/{identity}').status_code==404


def test_summary_persists_exact_evidence_and_idempotent_replay(sources,provider,monkeypatch):
    w=sources; model=model_for(monkeypatch)
    body={'document_id': w.alice_doc.id,'scope':'private','request_id':str(uuid4())}
    response=w.client.post('/api/retrieval/documents/summarize',headers=w.headers(w.alice),json=body)
    assert response.status_code==200, response.text
    result=response.json(); identity=result['run_id']
    assert get(w,f'/{identity}').json()['result']==result
    snap=w.db.query(AnalysisEvidence).filter_by(analysis_id=identity).one()
    assert snap.excerpt==f'SQL evidence {w.alice_doc.id}' and snap.page==3 and len(snap.evidence_hash)==64
    assert w.client.post('/api/retrieval/documents/summarize',headers=w.headers(w.alice),json=body).json()==result
    assert model.invoke.call_count==1
    w.db.query(DocumentChunk).delete(); w.db.commit()
    assert get(w,f'/{identity}').json()['evidence'][0]['excerpt']==snap.excerpt
    conflict=w.client.post('/api/retrieval/documents/summarize',headers=w.headers(w.alice),json={**body,'document_id':w.published.id,'scope':'public'})
    assert conflict.status_code==409


def test_failed_summary_has_no_saved_unvalidated_output(sources,provider,monkeypatch):
    model_for(monkeypatch, output='invalid')
    assert request(sources,sources.alice_doc.id).status_code==502
    row=get(sources).json()['items'][0]
    assert row['status']=='failed'
    detail=get(sources,f'/{row["id"]}').json()
    assert detail['result'] is None and detail['evidence']==[]


def test_summary_changed_evidence_during_generation_never_saved(sources,provider,monkeypatch):
    from types import SimpleNamespace
    from tests.test_phase13_document_summary import summary_json
    w=sources
    def mutate(*args):
        chunk=w.db.get(DocumentChunk,f'chunk-{w.alice_doc.id}')
        chunk.chunk_metadata={'page_content':'changed','page':3}; w.db.commit()
        return SimpleNamespace(content=summary_json())
    model_for(monkeypatch,side_effect=mutate)
    assert request(w,w.alice_doc.id).status_code==409
    assert w.db.query(AnalysisEvidence).count()==0


def test_empty_summary_is_saved_as_insufficient(sources,provider,monkeypatch):
    model=model_for(monkeypatch)
    sources.db.query(DocumentChunk).delete(); sources.db.commit()
    result=request(sources,sources.alice_doc.id).json()
    assert result['status']=='insufficient_evidence' and result['run_id']
    assert get(sources).json()['items'][0]['status']=='insufficient_evidence'
    model.invoke.assert_not_called()
