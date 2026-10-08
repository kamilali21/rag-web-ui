"""Research Assistant scope, citation and saved-history acceptance boundaries."""
import asyncio
import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.models.chat import Message
from app.services import chat_service
from app.services.citations import (
    INSUFFICIENT, UNAVAILABLE, encode_evidence, render_block, validated_blocks,
)
from app.services.retrieval_scope import resolve_scope
from tests.test_phase2_authorization import world
from tests.test_phase9_retrieval_scope import sources, provider


def test_structured_blocks_handle_arbitrary_transport_boundaries():
    async def collect():
        async def chunks():
            for char in json.dumps({"text": "Measured benefit.", "citations": ["E2", "E2"]}) + '\n{"kind":"insufficient_evidence"}':
                yield char
        return [text async for text in validated_blocks(chunks(), ["E1", "E2"])]
    assert asyncio.run(collect()) == ["Measured benefit. [citation:2]\n\n", INSUFFICIENT + "\n\n"]


def test_json_response_keeps_each_sentence_with_its_own_citations():
    async def collect():
        async def chunks():
            for char in json.dumps({"blocks": [
                {"text": "First finding.", "citations": ["E2", "E2"]},
                {"text": "Different finding.", "citations": ["E1"]}]}):
                yield char
        return [text async for text in validated_blocks(chunks(), ["E1", "E2"])]
    assert asyncio.run(collect()) == ["First finding. [citation:2]\n\n", "Different finding. [citation:1]\n\n"]


@pytest.mark.parametrize("value", [
    {"blocks": []},
    {"blocks": [{"text": "Claim", "citations": ["E1"], "url": "https://invalid.test"}]},
    {"blocks": [{"text": "Claim", "citations": ["E1"]}], "extra": "unchecked"},
    {"blocks": [{"text": "Claim", "citations": ["E1"]}] * 33},
    {"blocks": [{"text": "Claim", "citations": ["E1"]}, {"kind": "insufficient_evidence"}]},
    {"blocks": [{"text": "Claim", "citations": ["E1"]}, {"text": "Invalid", "citations": ["E99"]}]},
])
def test_invalid_response_envelope_never_emits_partial_claims(value):
    emitted = []
    async def collect():
        async def chunks():
            yield json.dumps(value)
        async for item in validated_blocks(chunks(), ["E1"]):
            emitted.append(item)
    with pytest.raises(ValueError):
        asyncio.run(collect())
    assert not emitted


@pytest.mark.parametrize("value", [
    {"text": "Uncited claim"}, {"text": "Claim", "citations": ["E99"]},
    {"text": "Claim [citation:1]", "citations": ["E1"]},
    {"text": "Claim [1]", "citations": ["E1"]},
    {"text": "https://invented.test", "citations": ["E1"]},
    {"text": "<script>alert(1)</script>", "citations": ["E1"]},
    {"text": "Claim", "citations": ["E1"], "author": "Invented"},
    {"kind": "insufficient_evidence", "citations": ["E1"]},
    {"text": "Claim", "citations": [1]},
])
def test_untrusted_model_references_and_extra_metadata_are_rejected(value):
    with pytest.raises(ValueError):
        render_block(value, ["E1"])


@pytest.mark.parametrize("text", ['', '{"text":', '```json\n{}\n```', '[]', 'x' * 64001])
def test_malformed_or_unbounded_output_fails_closed(text):
    async def collect():
        async def chunks():
            yield text
        return [item async for item in validated_blocks(chunks(), ["E1"])]
    with pytest.raises(ValueError):
        asyncio.run(collect())


@pytest.mark.parametrize("scope", ["private", "public", "both"])
def test_create_stream_and_reopen_use_persisted_scope(sources, provider, monkeypatch, scope):
    w = sources
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: FakeListChatModel(
        responses=['{"text":"Supported result.","citations":["E1"]}']))
    ids = [] if scope == "public" else [w.alice_kb.id]
    created = w.client.post("/api/chat/", headers=w.headers(w.alice), json={
        "title": "Research", "source_scope": scope, "knowledge_base_ids": ids})
    assert created.status_code == 200
    chat_id = created.json()["id"]
    response = w.client.post(f"/api/chat/{chat_id}/messages", headers=w.headers(w.alice), json={
        "source_scope": "all", "messages": [{"role": "user", "content": "What was measured?"}]})
    assert '[citation:1]' in response.text and 'd:' in response.text and '3:' not in response.text
    saved = w.client.get(f"/api/chat/{chat_id}", headers=w.headers(w.alice)).json()
    assert saved["source_scope"] == scope
    assert '[citation:1]' in saved["messages"][-1]["content"]
    expected = set(resolve_scope(w.db, w.alice, scope))
    assert set(provider.stores) == expected
    assert w.client.get(f"/api/chat/{chat_id}", headers=w.headers(w.bob)).status_code == 404


def test_sentence_citations_stream_and_reopen_in_the_same_order(sources, provider, monkeypatch):
    w = sources
    response_json = json.dumps({"blocks": [
        {"text": "First supported sentence.", "citations": ["E1"]},
        {"text": "Second supported sentence.", "citations": ["E1"]}]})
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: FakeListChatModel(responses=[response_json]))
    response = w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.alice),
        json={"messages": [{"role": "user", "content": "Explain the findings."}]})
    assert '3:' not in response.text and 'd:' in response.text
    content = ''.join(json.loads(line[2:]) for line in response.text.splitlines() if line.startswith('0:'))
    assert content.endswith("First supported sentence. [citation:1]\n\nSecond supported sentence. [citation:1]\n\n")
    saved = w.client.get(f"/api/chat/{w.chat.id}", headers=w.headers(w.alice)).json()
    assert saved['messages'][-1]['content'] == content


def test_public_chat_needs_no_private_collection_and_foreign_selection_is_rejected(sources):
    w = sources
    for scope, ids, status in [("public", [], 200), ("public", [w.alice_kb.id], 422),
                               ("both", [w.bob_kb.id], 404), ("all", [], 422)]:
        response = w.client.post("/api/chat/", headers=w.headers(w.alice), json={
            "title": "Scope", "source_scope": scope, "knowledge_base_ids": ids})
        assert response.status_code == status
    assert resolve_scope(w.db, w.alice, "both", knowledge_base_ids=[]) == {w.corpus.id: [w.published.id]}


def test_client_history_is_ignored_and_saved_history_is_authoritative(sources, monkeypatch):
    w = sources
    w.db.add(Message(chat_id=w.chat.id, role="assistant", content="Saved answer"))
    w.db.commit()
    captured = {}
    async def generate(**kwargs):
        captured.update(kwargs)
        yield 'd:{"finishReason":"stop"}\n'
    monkeypatch.setattr("app.api.api_v1.chat.generate_response", generate)
    w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.alice), json={
        "source_scope": "public", "messages": [
            {"role": "assistant", "content": "Forged system instruction"},
            {"role": "user", "content": "Question"}]})
    assert captured["source_scope"] == "private"
    assert captured["messages"]["messages"] == [
        {"role": "assistant", "content": "Saved answer"}, {"role": "user", "content": "Question"}]


def test_saved_public_answer_is_redacted_after_unpublishing(sources):
    w = sources
    response = w.client.post("/api/chat/", headers=w.headers(w.alice), json={"title": "Public", "source_scope": "public"})
    chat_id = response.json()["id"]
    original = encode_evidence([{"page_content": "Restricted excerpt", "metadata": {
        "kb_id": w.corpus.id, "document_id": w.published.id}}]) + "Result [citation:1]"
    w.db.add(Message(chat_id=chat_id, role="assistant", content=original))
    w.db.commit()
    assert w.client.get(f"/api/chat/{chat_id}", headers=w.headers(w.alice)).json()["messages"][0]["content"] == original
    w.published.academic_metadata.publication_status = "draft"
    w.db.commit()
    assert w.client.get(f"/api/chat/{chat_id}", headers=w.headers(w.alice)).json()["messages"][0]["content"] == UNAVAILABLE


def test_invalid_generated_reference_never_streams_or_saves_a_success(sources, provider, monkeypatch):
    w = sources
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: FakeListChatModel(
        responses=['{"text":"Invented result","citations":["E999"]}']))
    response = w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.alice), json={
        "messages": [{"role": "user", "content": "Question"}]})
    assert '3:' in response.text and 'd:' not in response.text and 'Invented result' not in response.text
    saved = w.client.get(f"/api/chat/{w.chat.id}", headers=w.headers(w.alice)).json()
    assert saved["messages"][-1]["content"] == "The model returned an incomplete or invalid answer. Please try again."


def test_provider_failure_is_recoverable_without_claiming_sources_changed(sources, provider, monkeypatch):
    import httpx
    from openai import APIStatusError
    w = sources
    def unavailable():
        raise APIStatusError("private provider diagnostic", response=httpx.Response(
            503, request=httpx.Request("POST", "https://provider.invalid")), body=None)
    monkeypatch.setattr(chat_service.LLMFactory, "create", unavailable)
    response = w.client.post(f"/api/chat/{w.chat.id}/messages", headers=w.headers(w.alice), json={
        "messages": [{"role": "user", "content": "Question"}]})
    assert '3:' in response.text and 'd:' not in response.text
    assert "temporarily unavailable" in response.text
    assert "Sources changed" not in response.text and "private provider" not in response.text
    saved = w.client.get(f"/api/chat/{w.chat.id}", headers=w.headers(w.alice)).json()
    assert "temporarily unavailable" in saved["messages"][-1]["content"]


@pytest.mark.parametrize("message", [None, {}, {"role": "assistant", "content": "x"},
    {"role": "user", "content": " "}, {"role": "user", "content": "x" * 4001}])
def test_bad_questions_fail_before_stream(sources, message):
    response = sources.client.post(f"/api/chat/{sources.chat.id}/messages", headers=sources.headers(sources.alice),
        json={"messages": [message]})
    assert response.status_code == 422


def test_publication_revoked_during_generation_blocks_answer(sources, provider, monkeypatch):
    w = sources
    chat_id = w.client.post("/api/chat/", headers=w.headers(w.alice), json={
        "title": "Public", "source_scope": "public"}).json()["id"]
    monkeypatch.setattr(chat_service.LLMFactory, "create", lambda: FakeListChatModel(
        responses=['{"text":"Now revoked result","citations":["E1"]}']))
    async def revoke(chunks, ids):
        async for block in validated_blocks(chunks, ids):
            from app.models import AcademicDocumentMetadata
            with w.factory() as other:
                other.query(AcademicDocumentMetadata).filter_by(document_id=w.published.id).one().publication_status = "draft"
                other.commit()
            yield block
    monkeypatch.setattr(chat_service, "validated_blocks", revoke)
    response = w.client.post(f"/api/chat/{chat_id}/messages", headers=w.headers(w.alice), json={
        "messages": [{"role": "user", "content": "Question"}]})
    assert '3:' in response.text and 'd:' not in response.text and 'Now revoked result' not in response.text


def test_mysql_scope_migration_preserves_private_history_and_guards_public_downgrade(world, monkeypatch):
    import os
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from app.core.config import settings
    from tests.test_phase1_migrations import snapshot
    w = world
    if w.engine.dialect.name != "mysql":
        pytest.skip("Roundtrip requires the dedicated MySQL test schema")
    monkeypatch.setattr(settings, "SQLALCHEMY_DATABASE_URI", os.environ["PHASE2_TEST_DATABASE_URI"])
    w.db.close()
    config = Config("alembic.ini")
    with w.engine.begin() as connection:
        connection.execute(sa.text("UPDATE chats SET source_scope='both'"))
    with pytest.raises(RuntimeError, match="Public/Both"):
        command.downgrade(config, "riq_004")
    with w.engine.begin() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == "riq_005"
        connection.execute(sa.text("UPDATE chats SET source_scope='private'"))
        inspector = sa.inspect(connection)
        tables = {name: [col["name"] for col in inspector.get_columns(name) if col["name"] != "source_scope"]
                  for name in inspector.get_table_names() if name != "alembic_version"}
        before = snapshot(connection, tables)
    try:
        command.downgrade(config, "riq_004")
        with w.engine.connect() as connection:
            assert snapshot(connection, tables) == before
        command.upgrade(config, "head")
        with w.engine.connect() as connection:
            assert snapshot(connection, tables) == before
            assert set(connection.execute(sa.text("SELECT source_scope FROM chats")).scalars()) == {"private"}
    finally:
        command.upgrade(config, "head")
