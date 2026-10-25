import asyncio
import base64
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from app.models import UserAISettings
from app.services import ai_settings as service, comparison, research_analysis, document_summary
from app.services.llm import llm_factory
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider
from tests.test_phase15_comparison import payload as compare_payload, draft as compare_draft
from tests.test_phase16_research_analysis import payload as analyze_payload, model_draft
from tests.test_phase13_document_summary import summary_json

KEY = "sk-test-" + "x" * 32


@pytest.fixture(autouse=True)
def encryption(monkeypatch):
    monkeypatch.setattr(service.settings, "AI_KEY_ENCRYPTION_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode())


def body(**changes):
    return {"provider": "openrouter", "model": "openrouter/free", "api_key": KEY, "consent": True, **changes}


def put(w, actor=None, **changes):
    return w.client.put("/api/ai-settings", headers=w.headers(actor or w.alice), json=body(**changes))


def test_owner_only_masked_encrypted_replace_delete(world):
    w = world
    response = put(w)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.json() == {"configured": True, "provider": "openrouter", "model": "openrouter/free", "key_last4": "xxxx"}
    w.db.expire_all()
    row = w.db.get(UserAISettings, w.alice.id)
    first = row.encrypted_key
    assert KEY not in first and KEY not in repr(service.resolve(w.db, w.alice))
    assert service.decrypt(row).get_secret_value() == KEY
    for actor in (w.bob, w.professor, w.superuser):
        assert not w.client.get("/api/ai-settings", headers=w.headers(actor)).json()["configured"]
        assert w.client.get(f"/api/ai-settings/{w.alice.id}", headers=w.headers(actor)).status_code == 404
        assert w.client.delete("/api/ai-settings", headers=w.headers(actor)).status_code == 200
    assert w.db.get(UserAISettings, w.alice.id)
    assert put(w, api_key=None, model="vendor/another").status_code == 200
    w.db.expire_all()
    assert w.db.get(UserAISettings, w.alice.id).encrypted_key != first
    assert put(w, provider="openai", model="gpt-4.1-mini", api_key=None).status_code == 422
    assert put(w, provider="openai", model="gpt-4.1-mini").status_code == 200
    assert w.client.delete("/api/ai-settings", headers=w.headers(w.alice)).json()["configured"] is False
    w.db.expire_all()
    assert w.db.get(UserAISettings, w.alice.id) is None


@pytest.mark.parametrize("changes", [{"provider":"other"}, {"model":"https://attacker.invalid/key"},
    {"model":"../key"}, {"provider":"openai","model":"unsupported"}, {"api_key":"secret\nvalue"},
    {"api_key":"x"*513}, {"consent":False}, {"user_id":2}, {"base_url":"https://attacker.invalid"}])
def test_invalid_input_never_echoes_key(world, changes):
    response = put(world, **changes)
    assert response.status_code == 422
    assert KEY not in response.text and "secret\nvalue" not in response.text
    assert world.db.query(UserAISettings).count() == 0


def test_auth_body_bounds_and_invalid_json(world):
    assert world.client.put("/api/ai-settings", json=body()).status_code == 401
    assert world.client.get("/api/ai-settings").status_code == 401
    response = world.client.put("/api/ai-settings", headers=world.headers(world.alice), content='{"api_key":"secret')
    assert response.status_code == 422 and "secret" not in response.text
    assert world.client.put("/api/ai-settings", headers=world.headers(world.alice), content="x"*9000).status_code == 413


def test_cipher_tamper_copy_and_missing_master_fail_closed(world, monkeypatch):
    w = world
    assert put(w).status_code == 200
    w.db.expire_all()
    row = w.db.get(UserAISettings, w.alice.id)
    copied = UserAISettings(user_id=w.bob.id, provider=row.provider, model=row.model, encrypted_key=row.encrypted_key, key_last4=row.key_last4)
    w.db.add(copied); w.db.commit()
    with pytest.raises(HTTPException, match="") as failed:
        service.resolve(w.db, w.bob)
    assert failed.value.status_code == 503
    row.encrypted_key = row.encrypted_key[:-8] + "AAAAAAAA"; w.db.commit()
    with pytest.raises(HTTPException): service.resolve(w.db, w.alice)
    monkeypatch.setattr(service.settings, "AI_KEY_ENCRYPTION_KEY", "")
    assert put(w).status_code == 503
    # The owner can remove an unreadable key without decryption.
    assert w.client.delete("/api/ai-settings", headers=w.headers(w.alice)).status_code == 200


def test_factory_fixed_destination_no_sdk_retries_no_global_mutation(world, monkeypatch):
    w = world
    original = service.settings.OPENAI_API_KEY
    put(w, provider="openai", model="gpt-4.1-mini")
    spy = MagicMock(); monkeypatch.setattr(llm_factory, "ChatOpenAI", spy)
    with service.user_context(w.db, w.alice):
        llm_factory.LLMFactory.create(streaming=False)
        assert service.provider_kind() == "openai" and not service.is_openrouter()
    kwargs = spy.call_args.kwargs
    assert kwargs["openai_api_key"] == KEY and kwargs["openai_api_base"] == "https://api.openai.com/v1"
    assert kwargs["model"] == "gpt-4.1-mini" and kwargs["max_retries"] == 0
    assert service.current_config() is None and service.settings.OPENAI_API_KEY == original


def test_concurrent_contexts_and_exception_reset(world):
    w = world; put(w); put(w, w.bob, provider="openai", model="gpt-4.1-mini", api_key="sk-bob-"+"b"*32)
    async def task(actor):
        with service.user_context(w.db, actor):
            await asyncio.sleep(.01)
            return service.current_config().api_key.get_secret_value()
    async def run(): return await asyncio.gather(task(w.alice), task(w.bob))
    assert asyncio.run(run()) == [KEY, "sk-bob-"+"b"*32]
    with pytest.raises(RuntimeError):
        with service.user_context(w.db, w.alice): raise RuntimeError()
    assert service.current_config() is None


def test_connection_check_is_owner_scoped_and_redacts_provider_errors(world, monkeypatch):
    w = world; put(w)
    model = MagicMock(); model.bind.return_value = model
    seen = []
    def factory(**kwargs):
        seen.append(service.current_config().api_key.get_secret_value()); return model
    monkeypatch.setattr(llm_factory.LLMFactory, "create", factory)
    model.invoke.return_value = SimpleNamespace(content='{"ok":true}')
    assert w.client.post("/api/ai-settings/check", headers=w.headers(w.alice)).json()["ok"]
    assert w.client.post("/api/ai-settings/check", headers=w.headers(w.professor)).status_code == 422
    model.invoke.side_effect = RuntimeError(KEY)
    response = w.client.post("/api/ai-settings/check", headers=w.headers(w.alice))
    assert response.status_code == 503 and KEY not in response.text and seen == [KEY, KEY]
    assert service.current_config() is None


def test_all_structured_features_share_owner_config(sources, provider, monkeypatch):
    w = sources; put(w)
    seen = []
    def verify():
        config = service.current_config(); assert config and config.api_key.get_secret_value() == KEY
        seen.append(config.model)
    def comparison_output(request, evidence): verify(); return compare_draft(request, evidence)
    monkeypatch.setattr(comparison, "generate", comparison_output)
    assert w.client.post("/api/insights/comparisons", headers=w.headers(w.alice), json=compare_payload(w)).status_code == 200
    def analysis_output(schema, system, payload, budget, label):
        verify(); return model_draft(schema, system, payload, budget, label)
    monkeypatch.setattr(comparison, "generate_structured", analysis_output)
    result = w.client.post("/api/insights/analyses", headers=w.headers(w.alice), json=analyze_payload(w))
    assert result.status_code == 200, result.text
    def summary_output(evidence): verify(); return document_summary.SummaryDraft.model_validate_json(summary_json())
    monkeypatch.setattr(document_summary, "_generate_draft", summary_output)
    assert w.client.post("/api/retrieval/documents/summarize", headers=w.headers(w.alice), json={"document_id":w.alice_doc.id,"scope":"private"}).status_code == 200
    assert len(seen) >= 4 and set(seen) == {"openrouter/free"}
    assert service.current_config() is None


def test_streamed_chat_uses_personal_model_and_preserves_citations(sources, provider, monkeypatch):
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from app.services import chat_service
    from tests.test_chat_reliability import send
    w = sources; put(w, provider="openai", model="gpt-4.1-mini")
    seen = []
    def factory():
        config = service.current_config()
        seen.append((config.provider, config.model, config.api_key.get_secret_value()))
        return FakeListChatModel(responses=['{"text":"Supported result.","citations":["E1"]}'])
    monkeypatch.setattr(chat_service.LLMFactory, "create", factory)
    response = send(w, "What does this paper report?")
    assert '[citation:1]' in response.text and 'd:' in response.text and '3:' not in response.text
    assert seen == [("openai", "gpt-4.1-mini", KEY)]
    assert service.current_config() is None


def test_provider_rejects_personal_key_without_shared_fallback(sources, provider, monkeypatch):
    import httpx
    from openai import AuthenticationError
    w = sources; put(w)
    model = MagicMock(); model.bind.return_value = model
    model.invoke.side_effect = AuthenticationError(KEY, response=httpx.Response(401, request=httpx.Request('POST','https://openrouter.ai/api/v1/chat/completions')), body={"secret":KEY})
    seen = []
    def factory(**kwargs):
        seen.append(service.current_config().api_key.get_secret_value()); return model
    monkeypatch.setattr(llm_factory.LLMFactory, "create", factory)
    response = w.client.post("/api/insights/comparisons", headers=w.headers(w.alice), json=compare_payload(w))
    assert response.status_code == 503 and KEY not in response.text
    assert seen == [KEY] and model.invoke.call_count == 1
