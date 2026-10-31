from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.models import AnalysisRun, AnalysisEvidence, DocumentChunk
from app.schemas.candidate_gaps import CandidateGapsDraft, CATEGORIES
from app.schemas.research_analysis import ProfilesDraft
from app.services import candidate_gaps, comparison
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase16_research_analysis import payload, model_draft, post

TEXT = "Only one season was studied; multi-season field validation is required."


@pytest.fixture
def papers(sources):
    for chunk in sources.db.query(DocumentChunk):
        chunk.chunk_metadata = {"page_content": TEXT, "page": 3}
    sources.db.commit()
    return sources


def body(w, **changes):
    return payload(w, focus='candidate_gaps', include_related=False, **changes)


def item(refs=None, category='limited_field_validation'):
    refs = refs or ['E1']
    return {'category':category, 'topic':'Multi-season field validation',
        'evidence_pattern':{'text':'In the retrieved evidence, only one season is studied and field validation is requested.', 'evidence_ids':refs},
        'evidence_quotes':[{'evidence_id':ref,'quote':TEXT} for ref in refs]}


def draft(schema, system, data, budget, label, **_kwargs):
    if schema is ProfilesDraft: return model_draft(schema, system, data, budget, label)
    return CandidateGapsDraft(candidates=[item([data['evidence'][0]['evidence_id']])])


@pytest.fixture
def generation(monkeypatch):
    fn = MagicMock(side_effect=draft)
    monkeypatch.setattr(comparison, 'generate_structured', fn)
    return fn


def test_gap_saved_with_quotes_qualification_ownership_and_replay(papers, provider, generation):
    w = papers; request = body(w)
    response = post(w, request); assert response.status_code == 200, response.text
    run = response.json(); gap = run['result']['candidate_gaps'][0]
    assert run['status'] == 'complete' and run['result']['focus'] == 'candidate_gaps'
    assert gap['title'] == 'Limited Field Validation' and gap['qualification'] == candidate_gaps.QUALIFICATION
    assert gap['evidence_quotes'][0]['quote'] == TEXT
    assert gap['evidence_quotes'][0]['citation']['document_id'] == w.alice_doc.id
    assert w.db.get(AnalysisRun, run['id']).analysis_type == 'candidate_gaps'
    assert post(w, request).json() == run and generation.call_count == 2
    assert post(w, {**request,'focus':'overview'}).status_code == 409
    paths = [f"/api/insights/analyses/{run['id']}",f"/api/insights/analyses/requests/{request['request_id']}"]
    for path in paths:
        assert w.client.get(path,headers=w.headers(w.alice)).json() == run
        assert w.client.get(path).status_code == 401
        for actor in (w.bob,w.professor,w.superuser):
            assert w.client.get(path,headers=w.headers(actor)).status_code == 404
    assert w.client.get(f"/api/insights/comparisons/{run['id']}",headers=w.headers(w.alice)).status_code == 404


@pytest.mark.parametrize('target',['bob_doc','draft','archived','failed','fake'])
def test_unauthorized_unready_sources_do_not_generate(papers,generation,target):
    w = papers
    assert post(w,body(w,document_ids=[getattr(w,target).id])).status_code == 404
    generation.assert_not_called()


@pytest.mark.parametrize('fault',['unknown','duplicate','quote_missing','invented_quote','unqualified','related_only'])
def test_invalid_patterns_fail_without_persisting_results(papers,provider,monkeypatch,fault):
    def bad(*args, **_kwargs):
        value = draft(*args)
        if isinstance(value,CandidateGapsDraft):
            gap = value.candidates[0]
            if fault=='unknown': gap.evidence_pattern.evidence_ids=['E999']
            if fault=='duplicate': gap.evidence_pattern.evidence_ids *= 2
            if fault=='quote_missing': gap.evidence_quotes=[]
            if fault=='invented_quote': gap.evidence_quotes[0].quote='An invented quotation that is absent from the source.'
            if fault=='unqualified': gap.topic='This is a first-ever discovery worldwide'
            if fault=='related_only':
                gap.evidence_pattern.evidence_ids=['E2']; gap.evidence_quotes[0].evidence_id='E2'
        return value
    monkeypatch.setattr(comparison,'generate_structured',bad)
    assert post(papers,body(papers)).status_code == 502
    assert papers.db.query(AnalysisRun).one().status == 'failed'
    assert papers.db.query(AnalysisEvidence).count() == 0


def test_empty_supported_patterns_abstain(papers,provider,monkeypatch):
    monkeypatch.setattr(comparison,'generate_structured',lambda *args, **_kw: model_draft(*args) if args[0] is ProfilesDraft else CandidateGapsDraft(candidates=[]))
    response = post(papers,body(papers)).json()
    assert response['status']=='insufficient_evidence' and response['result']['candidate_gaps']==[]
    assert 'not proven gaps' in response['result']['notice']


def test_no_evidence_does_not_call_model(papers,provider,generation):
    papers.db.query(DocumentChunk).delete(); papers.db.commit()
    assert post(papers,body(papers)).json()['status']=='insufficient_evidence'
    generation.assert_not_called()


def test_source_revocation_while_generating_discards_gaps(papers,provider,monkeypatch):
    def revoke(*args, **_kwargs):
        value=draft(*args)
        if isinstance(value,CandidateGapsDraft):
            papers.published.academic_metadata.publication_status='archived'; papers.db.commit()
        return value
    monkeypatch.setattr(comparison,'generate_structured',revoke)
    assert post(papers,body(papers,document_ids=[papers.published.id])).status_code==404
    assert papers.db.query(AnalysisEvidence).count()==0


@pytest.mark.parametrize('category',list(CATEGORIES))
def test_all_planned_categories_and_date_coverage(category):
    evidence=[{'evidence_id':'E1','document_id':1,'excerpt':TEXT},{'evidence_id':'E2','document_id':2,'excerpt':TEXT}]
    result=candidate_gaps.validate(CandidateGapsDraft(candidates=[item(['E1','E2'],category)]),evidence,[1],[{'id':1,'publication_year':2018},{'id':2,'publication_year':2020}],2026)
    assert result[0]['title']==CATEGORIES[category]
    if category in {'outdated_evidence','sparse_recent_evidence'}:
        assert result[0]['timeframe']=={'start_year':2022,'end_year':2026,'recent_papers':0,'dated_papers':2}


@pytest.mark.parametrize('category,years',[('conflicting_evidence',[2020]),('outdated_evidence',[2026]),('outdated_evidence',[None]),('sparse_recent_evidence',[2025,2026]),('sparse_recent_evidence',[2010,None])])
def test_conflict_and_recency_need_sufficient_documented_basis(category,years):
    evidence=[{'evidence_id':f'E{i+1}','document_id':i+1,'excerpt':TEXT} for i in range(len(years))]
    docs=[{'id':i+1,'publication_year':year} for i,year in enumerate(years)]
    with pytest.raises(HTTPException):
        candidate_gaps.validate(CandidateGapsDraft(candidates=[item([e['evidence_id'] for e in evidence],category)]),evidence,[1],docs,2026)


def test_schema_rejects_unknown_categories_and_unbounded_results():
    with pytest.raises(ValidationError): CandidateGapsDraft(candidates=[item(category='proven_novelty')])
    with pytest.raises(ValidationError): CandidateGapsDraft(candidates=[item()]*5)


def test_publication_year_changed_during_generation_is_revalidated(papers,provider,monkeypatch):
    w=papers
    w.published.academic_metadata.publication_year=2010; w.db.commit()
    def changed(*args, **_kwargs):
        value=draft(*args)
        if isinstance(value,CandidateGapsDraft):
            value.candidates[0].category='outdated_evidence'
            w.published.academic_metadata.publication_year=2026; w.db.commit()
        return value
    monkeypatch.setattr(comparison,'generate_structured',changed)
    assert post(w,body(w,document_ids=[w.published.id])).status_code==502
    assert w.db.query(AnalysisEvidence).count()==0
