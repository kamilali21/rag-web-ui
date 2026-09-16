"""Added by ChatGPT: baseline contracts before adding ResearchIQ features."""
import asyncio
import base64
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.retrievers import BaseRetriever


class FixtureRetriever(BaseRetriever):
    documents: list[Document]

    def _get_relevant_documents(self, query, *, run_manager):
        return self.documents


def test_chat_retrieves_all_selected_collections_and_persists_the_stream():
    from app.services import chat_service

    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [
        [object()], [object()]
    ]
    stores = []
    for kb_id in [11, 12]:
        store = MagicMock()
        store.as_retriever.return_value = FixtureRetriever(documents=[Document(
            page_content=f"Irrigation experiment from collection {kb_id}.",
            metadata={"kb_id": kb_id, "document_id": kb_id, "page": 0},
        )])
        stores.append(store)
    messages = {"messages": [{"role": "user", "content": "Compare irrigation."}]}

    async def collect():
        return [part async for part in chat_service.generate_response(
            "Compare irrigation.", messages, [11, 12], 1, db, SimpleNamespace(id=3)
        )]

    # Added by ChatGPT: isolate this RAG contract; Phase 2 tests exercise real authorization separately.
    with patch.object(chat_service, "require_chat_sources", return_value=[
        SimpleNamespace(id=11), SimpleNamespace(id=12)
    ]), patch.object(chat_service.EmbeddingsFactory, "create"), patch.object(
        chat_service.VectorStoreFactory, "create", side_effect=stores
    ), patch.object(chat_service.LLMFactory, "create", return_value=FakeListChatModel(
        responses=["Irrigation results differ. [citation:1][citation:2]"]
    )):
        frames = asyncio.run(collect())
    text = "".join(json.loads(frame[2:]) for frame in frames if frame.startswith("0:"))
    encoded, answer = text.split("__LLM_RESPONSE__", 1)
    evidence = json.loads(base64.b64decode(encoded))["context"]
    assert {item["metadata"]["kb_id"] for item in evidence} == {11, 12}
    assert "[citation:1][citation:2]" in answer
    assert any(frame.startswith("d:") for frame in frames)
    assert db.add.call_args_list[1].args[0].content == text
    assert messages == {"messages": [{"role": "user", "content": "Compare irrigation."}]}


def test_chat_failure_is_a_valid_json_stream_frame_without_internal_error_details():
    from app.services import chat_service

    db = MagicMock()
    db.query.side_effect = RuntimeError('private provider token "secret"\ntrace')

    async def collect():
        return [part async for part in chat_service.generate_response(
            "Question", {"messages": [{"role": "user", "content": "Question"}]}, [11], 1, db, SimpleNamespace(id=3)
        )]

    with patch.object(chat_service, "require_chat_sources", return_value=[SimpleNamespace(id=11)]), patch.object(
        chat_service.EmbeddingsFactory, "create"
    ):
        frames = asyncio.run(collect())
    assert isinstance(json.loads(frames[-1][2:]), str)
    assert "secret" not in frames[-1]
    db.rollback.assert_called()


def test_migration_check_compares_database_to_script_head():
    from app.startup.migarate import DatabaseMigrator

    migrator = DatabaseMigrator("sqlite://")
    connection = MagicMock()

    @contextmanager
    def connect():
        yield connection

    with patch.object(migrator, "database_connection", connect), patch(
        "app.startup.migarate.MigrationContext"
    ) as migration, patch("app.startup.migarate.ScriptDirectory") as scripts:
        migration.configure.return_value.get_current_revision.return_value = "old_revision"
        scripts.from_config.return_value.get_current_head.return_value = "new_revision"
        assert migrator.check_migration_needed() == (True, "old_revision", "new_revision")
        migration.configure.return_value.get_current_revision.return_value = "new_revision"
        assert migrator.check_migration_needed() == (False, "new_revision", "new_revision")


def test_collection_deletion_uses_store_contract_and_recursive_object_cleanup():
    from app.api.api_v1 import knowledge_base

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(documents=[])
    store, minio = MagicMock(), MagicMock()
    minio.list_objects.return_value = [SimpleNamespace(object_name="kb_71/temp/fixture.pdf")]
    with patch.object(knowledge_base, "require_private_knowledge_base", return_value=SimpleNamespace(documents=[])), patch.object(
        knowledge_base, "get_minio_client", return_value=minio
    ), patch.object(
        knowledge_base.EmbeddingsFactory, "create"
    ), patch.object(knowledge_base.VectorStoreFactory, "create", return_value=store):
        result = asyncio.run(knowledge_base.delete_knowledge_base(
            db=db, kb_id=71, current_user=SimpleNamespace(id=3)
        ))
    store.delete_collection.assert_called_once_with()
    assert minio.list_objects.call_args.kwargs["recursive"] is True
    assert "warnings" not in result


def test_chroma_insertion_reuses_chunk_ids():
    from app.services.vector_store.chroma import ChromaVectorStore

    store = object.__new__(ChromaVectorStore)
    store._store = MagicMock()
    documents = [Document(page_content="Synthetic evidence", metadata={"chunk_id": "a" * 64})]
    store.add_documents(documents)
    store._store.add_documents.assert_called_once_with(documents, ids=["a" * 64])
