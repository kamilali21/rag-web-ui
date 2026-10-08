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


@pytest.mark.parametrize("query", ["hi", " Hello! ", "HEY", "hello there", "Good morning", "god morning", "helo", "Assalamu alaikum"])
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
        constructor.assert_called_with(model_name='test-model', model_kwargs={'local_files_only': True})
        monkeypatch.setattr(module.settings, 'HUGGINGFACE_EMBEDDINGS_MODEL', 'other-model')
        constructor.side_effect = None
        constructor.return_value = object()
        assert module.EmbeddingsFactory.create() is not model and constructor.call_count == 3
    finally:
        module._huggingface_model.cache_clear()


@pytest.mark.parametrize('rewrite', ['', 'x' * 4001])
def test_empty_or_oversized_rewrite_uses_original_question(sources, provider, monkeypatch, rewrite):
    w = sources
    w.db.add(Message(chat_id=w.chat.id, role='user', content='An earlier question'))
    w.db.commit()
    model = FakeListChatModel(responses=[rewrite, '{"text":"Supported result.","citations":["E1"]}'])
    monkeypatch.setattr(chat_service.LLMFactory, 'create', lambda: model)
    response = send(w, 'How do I set it up?')
    assert 'd:' in response.text and '3:' not in response.text
    assert provider.stores[w.alice_kb.id].search_permitted.call_args.args[0] == 'How do I set it up?'


def test_failed_rewrite_does_not_abort_answer(sources, provider, monkeypatch):
    import httpx
    from openai import APIConnectionError
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda
    w = sources
    w.db.add(Message(chat_id=w.chat.id, role='user', content='An earlier question'))
    w.db.commit()
    calls = []
    async def model(messages, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise APIConnectionError(request=httpx.Request('POST', 'https://provider.invalid'))
        return AIMessage(content='{"text":"Supported result.","citations":["E1"]}')
    monkeypatch.setattr(chat_service.LLMFactory, 'create', lambda: RunnableLambda(model))
    response = send(w, 'Original question')
    assert 'd:' in response.text and '3:' not in response.text and '[citation:1]' in response.text
    assert provider.stores[w.alice_kb.id].search_permitted.call_args.args[0] == 'Original question'


def test_missing_local_model_downloads_once_then_reuses_it(monkeypatch):
    from app.services.embedding import embedding_factory as module
    module._huggingface_model.cache_clear()
    model = object()
    constructor = MagicMock(side_effect=[OSError('not cached'), model])
    monkeypatch.setattr(module, 'HuggingFaceEmbeddings', constructor)
    try:
        assert module._huggingface_model('fresh-model', '') is model
        assert module._huggingface_model('fresh-model', '') is model
        assert constructor.call_count == 2
        assert constructor.call_args_list[0].kwargs['model_kwargs'] == {'local_files_only': True}
        assert constructor.call_args_list[1].kwargs['model_kwargs'] == {}
    finally:
        module._huggingface_model.cache_clear()


def test_openrouter_json_mode_applies_only_to_answer_and_keeps_citation_validation(sources, provider, monkeypatch):
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda
    monkeypatch.setattr(chat_service.settings, 'CHAT_PROVIDER', 'openai')
    monkeypatch.setattr(chat_service.settings, 'OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
    sources.db.add(Message(chat_id=sources.chat.id, role='user', content='Earlier question'))
    sources.db.commit()
    calls = []
    async def model(messages, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return AIMessage(content='Standalone question')
        # Provider JSON mode is a format aid; invented references must still fail.
        return AIMessage(content='{"kind":"answer","text":"Invented claim","citations":["E99"]}')
    monkeypatch.setattr(chat_service.LLMFactory, 'create', lambda: RunnableLambda(model))
    response = send(sources, 'Follow-up question')
    assert 'response_format' not in calls[0]
    assert calls[1]['response_format'] == {'type': 'json_object'}
    assert calls[1]['extra_body']['provider']['require_parameters'] is True
    assert '3:' in response.text and 'Invented claim' not in response.text
