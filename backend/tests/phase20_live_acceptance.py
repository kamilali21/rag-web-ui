"""Opt-in security acceptance against the local stack; only synthetic fixtures.

PHASE20_LIVE_ACCEPTANCE=1 python -m tests.phase20_live_acceptance
The shared harness verifies exact original SQL/object/vector equality on cleanup.
"""
from io import BytesIO
from PIL import Image
from tests.phase15_live_acceptance import run


def check(owner, other, private_id, public_id, passed):
    doc = owner.get(f'/api/insights/documents/{private_id}', params={'scope': 'private'}).raise_for_status().json()
    kb_id = doc['knowledge_base_id']
    private_path = f'/api/knowledge-base/{kb_id}/documents'
    for path in (f'{private_path}/{private_id}', f'{private_path}/{private_id}/content',
                 f'/api/insights/documents/{private_id}?scope=private'):
        assert other.get(path).status_code == 404
    for path in ('/api/researcher/admin', '/api/researcher/admin/count', '/api/corpus/tasks'):
        assert other.get(path).status_code == 403
    passed('Live owner boundaries and researcher denial of administrative review/corpus routes')

    for method, path in [('DELETE', '/api/ai-settings'), ('DELETE', '/api/researcher/profile/photo'),
                         ('POST', '/api/retrieval/documents/summarize'), ('POST', '/api/insights/analyses')]:
        request = owner.build_request(method, path, json={})
        del request.headers['X-CSRF-Token']
        response = owner.send(request)
        assert response.status_code == 403 and 'CSRF' in response.text
    request = owner.build_request('DELETE', '/api/ai-settings')
    request.headers['Origin'] = 'https://attacker.invalid'
    assert owner.send(request).status_code == 403
    passed('Live session CSRF and foreign-origin rejection across profile, provider settings and AI endpoints')

    for filename, data, mime, code in [('empty.txt', b'', 'text/plain', 400),
        ('spoof.pdf', b'<script>unsafe</script>', 'application/pdf', 400),
        ('payload.exe', b'MZ-unsafe', 'application/octet-stream', 400),
        ('spoof.txt', b'Synthetic text', 'text/html', 415)]:
        assert owner.post(private_path + '/upload', files={'files': (filename, data, mime)}).status_code == code
        expected = 413 if not data else code
        assert owner.post('/api/corpus/documents/upload', files={'file': (filename, data, mime)}).status_code == expected
    for path in (f'{private_path}/{private_id}/content?inline=true', f'/api/corpus/documents/{public_id}/content?inline=true'):
        response = owner.get(path).raise_for_status()
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert 'sandbox' in response.headers['content-security-policy']
        assert response.content.startswith(b'%PDF-')
    passed('Live invalid uploads blocked; valid PDFs still downloadable with sandbox/nosniff protections')

    departments = owner.get('/api/departments').raise_for_status().json()
    department = next(row for row in departments if row['is_active'])
    profile = {'full_name': 'Synthetic Security Researcher', 'department_id': department['id'],
               'degree': 'Synthetic degree', 'research_area': 'Synthetic security checks', 'ag_number': 'PRIVATE-SYNTHETIC'}
    owner.put('/api/researcher/profile', json=profile).raise_for_status()
    try:
        bad = owner.put('/api/researcher/profile/photo', files={'file': ('fake.png', b'\x89PNG\r\n\x1a\nforged header only', 'image/png')})
        assert bad.status_code == 415
        image = BytesIO()
        Image.new('RGB', (2, 2), 'green').save(image, format='PNG')
        owner.put('/api/researcher/profile/photo', files={'file': ('avatar.png', image.getvalue(), 'image/png')}).raise_for_status()
        assert owner.get('/api/researcher/profile/photo').content == image.getvalue()
        assert other.get('/api/researcher/profile/photo').status_code == 404
        assert other.get('/api/researcher/profile').json() is None
    finally:
        owner.delete('/api/researcher/profile/photo').raise_for_status()
    passed('Live photo decoding/upload/removal and profile isolation; no image object retained')


def after(owner, other, private_id, public_id, run_id, passed):
    assert other.get(f'/api/insights/history/{run_id}').status_code == 404
    assert owner.get(f'/api/insights/history/{run_id}').status_code == 404
    row = next(row for row in owner.get('/api/insights/history').json()['items'] if row['id'] == run_id)
    assert not row['available'] and row['question'] is None and not row['documents']
    other.post('/api/auth/logout').raise_for_status()
    assert other.get('/api/insights/history').status_code == 401
    passed('Live saved-history isolation, revoked-source redaction and session logout')


if __name__ == '__main__':
    run(extra_acceptance=check, after_comparison=after, phase='phase20')
