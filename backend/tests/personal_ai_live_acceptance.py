"""Opt-in synthetic BYOK acceptance, using only the configured OpenRouter key.

The key is temporarily assigned to a synthetic owner, never printed or returned.
Only openrouter/free is used; no paid OpenAI request is made.
PERSONAL_AI_LIVE_ACCEPTANCE=1 python -m tests.personal_ai_live_acceptance
"""
import json
import time
from uuid import uuid4
from urllib.parse import urlparse
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Document, UserAISettings
from tests.phase15_live_acceptance import run


def check(owner, other, private_id, public_id, passed):
    assert urlparse(settings.OPENAI_API_BASE).hostname == 'openrouter.ai'
    assert settings.OPENAI_API_KEY
    def call(method, path, expected=200, **kwargs):
        response = owner.request(method, path, **kwargs)
        assert response.status_code == expected, (path, response.status_code)
        return response.json()
    assert not call('GET', '/api/ai-settings')['configured']
    saved = call('PUT', '/api/ai-settings', json={'provider':'openrouter','model':'openrouter/free',
        'api_key':settings.OPENAI_API_KEY,'consent':True})
    assert saved['configured'] and 'api_key' not in saved and 'encrypted_key' not in saved
    assert not other.get('/api/ai-settings').json()['configured']
    with SessionLocal() as db:
        private = db.get(Document, private_id)
        kb_id = private.knowledge_base_id
        owner_id = private.knowledge_base.user_id
        row = db.get(UserAISettings, owner_id)
        assert settings.OPENAI_API_KEY not in row.encrypted_key
    assert call('POST', '/api/ai-settings/check')['ok']
    passed('Personal OpenRouter key encrypted, owner-private and real JSON connection check passed')
    result = call('POST', '/api/retrieval/documents/summarize', json={'scope':'private','document_id':private_id})
    assert result['status'] == 'complete'
    claims = [claim for section in result['sections'] for claim in section['claims']]
    assert claims and all(c['document_id'] == private_id for claim in claims for c in claim['citations'])
    passed('Personal-key summary returned exact-document cited academic sections')
    chat_id = call('POST', '/api/chat/', json={'title':'Synthetic personal AI check','source_scope':'private','knowledge_base_ids':[kb_id]})['id']
    try:
        response = owner.post(f'/api/chat/{chat_id}/messages', json={'messages':[{'role':'user','content':'How much water did drip irrigation save in this study?'}]})
        assert response.status_code == 200 and '3:' not in response.text and '[citation:' in response.text
        saved_chat = call('GET', f'/api/chat/{chat_id}')
        assert any('[citation:' in item['content'] for item in saved_chat['messages'] if item['role']=='assistant')
        assert other.get(f'/api/chat/{chat_id}').status_code == 404
        passed('Personal-key streamed chat citations, saved reopening and ownership passed')
    finally:
        call('DELETE', f'/api/chat/{chat_id}')
    request = {'request_id':str(uuid4()),'scope':'both','document_ids':[private_id,public_id],
               'question':'Describe the findings and limitations of these synthetic irrigation studies.','include_related':False}
    started = time.monotonic()
    result = call('POST','/api/insights/analyses',json=request)
    assert result['status'] == 'complete' and len(result['result']['profiles']) == 2
    assert any(section['claims'] for section in result['result']['sections'])
    assert call('GET',f"/api/insights/analyses/{result['id']}") == result
    assert other.get(f"/api/insights/analyses/{result['id']}").status_code == 404
    passed(f'Personal-key research analysis, saved results and ownership passed ({time.monotonic()-started:.2f}s)')
    # The enclosing runner also runs Compare, reopens it and checks revocation.
    # CASCADE removes this synthetic user's encrypted key during final cleanup.


if __name__ == '__main__':
    run(extra_acceptance=check, phase='personal_ai')
