"""Opt-in synthetic summary/history gate, plus existing comparison and cleanup."""
from uuid import uuid4
from tests.phase15_live_acceptance import run


def check(owner, other, private_id, public_id, passed):
    assert owner.get('/api/insights/history').json()['items'] == []
    for identity, scope in ((private_id, 'private'), (public_id, 'public')):
        body = {'document_id': identity, 'scope': scope, 'request_id': str(uuid4())}
        response = owner.post('/api/retrieval/documents/summarize', json=body)
        assert response.status_code == 200, f'Summary HTTP {response.status_code}'
        result = response.json()
        assert result['status'] == 'complete'
        assert all(c['document_id'] == identity for section in result['sections'] for claim in section['claims'] for c in claim['citations'])
        assert any(section['claims'] for section in result['sections'])
        saved = owner.get(f'/api/insights/history/{result["run_id"]}').raise_for_status().json()
        assert saved['result'] == result and saved['evidence']
        assert saved['evidence'][0]['page'] == 0
        assert other.get(f'/api/insights/history/{result["run_id"]}').status_code == 404
        assert owner.post('/api/retrieval/documents/summarize', json=body).json() == result
    first = owner.get('/api/insights/history?limit=1&analysis_type=summary').raise_for_status().json()
    assert first['has_more'] and first['next_before_id']
    second = owner.get(f'/api/insights/history?limit=1&analysis_type=summary&before_id={first["next_before_id"]}').raise_for_status().json()
    assert len(second['items']) == 1 and not second['has_more']
    assert other.get('/api/insights/history').json()['items'] == []
    passed('Public/private summaries persisted; exact snapshots, history pagination, owner isolation and idempotent reopening')


def after(owner, other, private_id, public_id, run_id, passed):
    rows = owner.get('/api/insights/history').raise_for_status().json()['items']
    assert len(rows) == 3
    comparison = next(row for row in rows if row['id'] == run_id)
    assert not comparison['available'] and comparison['question'] is None and not comparison['documents']
    assert owner.get(f'/api/insights/history/{run_id}').status_code == 404
    private = [row for row in rows if row['scope'] == 'private']
    assert len(private) == 1 and private[0]['available']
    assert owner.get(f'/api/insights/history/{private[0]["id"]}').status_code == 200
    assert all(not row['available'] for row in rows if row['scope'] != 'private')
    passed('History includes comparison; revoked public sources redact rows and deny snapshots; private summary remains usable')


if __name__ == '__main__':
    run(extra_acceptance=check, after_comparison=after, phase='phase19')
