"""Greeting, bounded recovery and model reuse regressions without external providers."""
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.models.chat import Message
from app.services import chat_service
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider


def send(w, query):
    return w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.alice),
        json={"messages": [{"role": "user", "content": query}]})


@pytest.mark.parametrize("query", ["hi", " Hello! ", "HEY", "hello there", "Good morning", "Assalamu alaikum"])
def test_greetings_save_and_stream_without_retrieval_or_llm(sources, provider, monkeypatch, query):
    model = MagicMock(side_effect=AssertionError("Greeting must not call the provider"))
    monkeypatch.setattr(chat_service.LLMFactory, "create", model)
    response = send(sources, query)
    assert response.status_code == 200 and 'd:' in response.text and '3:' not in response.text
    text = ''.join(json.loads(line[2:]) for line in response.text.splitlines() if line.startswith('0:'))
    assert text == chat_service.GREETING and '__LLM_RESPONSE__' not in text
    saved = sources.client.get(f"/api/chat/{sources.chat.id}", headers=sources.headers(sources.alice)).json()
    assert [(m['role'], m['content']) for m in saved['messages']] == [('user', query), ('assistant', text)]
    provider.assert_not_called()
    model.assert_not_called()


def test_greetings_still_require_chat_ownership(sources, provider):
    w = sources
    before = w.db.query(Message).count()
    response = w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.bob),
        json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 404 and w.db.query(Message).count() == before
    provider.assert_not_called()


def test_greeting_prefix_does_not_bypass_citations_and_greetings_do_not_trigger_rewrite(sources, provider, monkeypatch):
    w = sources
    send(w, 'hi')
    model = FakeListChatModel(responses=[
        '{"text":"Supported result.","citations":["E1"]}', 'Must not need a second model call'])
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: model)
    response = send(w, 'Hi, what does this paper report?')
    assert '[citation:1]' in response.text and 'd:' in response.text and '3:' not in response.text
    provider.assert_called()
    assert model.i == 1


def test_invalid_first_output_retries_once_without_streaming_or_persisting_it(sources, provider, monkeypatch):
    model = FakeListChatModel(responses=['Unvalidated prose', '{"text":"Supported result.","citations":["E1"]}'])
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: model)
    response = send(sources, 'What does this paper report?')
    assert 'd:' in response.text and '3:' not in response.text and 'Unvalidated prose' not in response.text
    assert response.text.count('[citation:1]') == 1 and response.text.count('__LLM_RESPONSE__') == 1
    sources.db.expire_all()
    saved = sources.db.query(Message).filter_by(chat_id=sources.chat.id).order_by(Message.id).all()
    assert len(saved) == 2 and '[citation:1]' in saved[-1].content


def test_invalid_retry_still_fails_closed_and_never_reaches_a_third_answer(sources, provider, monkeypatch):
    model = FakeListChatModel(responses=['Bad prose', '{"text":"Invented","citations":["E999"]}',
        '{"text":"A third attempt must not occur","citations":["E1"]}'])
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: model)
    response = send(sources, 'Question')
    assert '3:' in response.text and 'd:' not in response.text
    assert '__LLM_RESPONSE__' not in response.text and 'Invented' not in response.text
    assert model.i == 2


def test_partial_valid_answer_is_not_replayed_after_a_later_invalid_block(sources, provider, monkeypatch):
    model = FakeListChatModel(responses=[
        '{"text":"First claim","citations":["E1"]}{"text":"Invalid claim","citations":["E99"]}',
        '{"text":"Do not retry partial output","citations":["E1"]}'])
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: model)
    response = send(sources, 'Question')
    assert '3:' in response.text and 'd:' not in response.text
    assert response.text.count('First claim') == 1 and 'Invalid claim' not in response.text
    assert model.i == 1


def test_local_embedding_model_is_reused_and_failed_initialization_is_retryable(monkeypatch):
    from app.services.embedding import embedding_factory as module
    module._huggingface_model.cache_clear()
    monkeypatch.setattr(module.settings, 'EMBEDDINGS_PROVIDER', 'huggingface')
    monkeypatch.setattr(module.settings, 'HUGGINGFACE_EMBEDDINGS_MODEL', 'test-model')
    monkeypatch.setattr(module.settings, 'HUGGINGFACE_API_KEY', '')
    model = object()
    constructor = MagicMock(side_effect=[RuntimeError('temporary failure'), model])
    monkeypatch.setattr(module, 'HuggingFaceEmbeddings', constructor)
    try:
        with pytest.raises(RuntimeError):
            module.EmbeddingsFactory.create()
        with ThreadPoolExecutor(max_workers=4) as pool:
            loaded = list(pool.map(lambda _: module.EmbeddingsFactory.create(), range(8)))
        assert all(item is model for item in loaded) and constructor.call_count == 2
        constructor.assert_called_with(model_name='test-model', model_kwargs={})
        monkeypatch.setattr(module.settings, 'HUGGINGFACE_EMBEDDINGS_MODEL', 'other-model')
        constructor.side_effect = None
        constructor.return_value = object()
        assert module.EmbeddingsFactory.create() is not model and constructor.call_count == 3
    finally:
        module._huggingface_model.cache_clear()
