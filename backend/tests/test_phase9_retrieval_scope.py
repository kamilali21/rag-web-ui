"""Source-set boundaries before Phase 9 connects them to vector retrieval."""
import pytest
from fastapi import HTTPException

from app.models import AcademicDocumentMetadata, Document
from app.models.knowledge import ProcessingTask
from app.services.public_corpus import provision_corpus
from app.services.retrieval_scope import resolve_scope
from tests.test_phase2_authorization import world


@pytest.fixture
def sources(world):
    w = world
    w.corpus = provision_corpus(w.db)
    def doc(kb, name, publication, state="completed"):
        row = Document(knowledge_base_id=kb.id, file_name=name, file_path=f"kb_{kb.id}/{name}", file_size=12, content_type="text/plain")
        row.academic_metadata = AcademicDocumentMetadata(title=name, publication_status=publication)
        w.db.add(row); w.db.flush()
        w.db.add(ProcessingTask(knowledge_base_id=kb.id, document_id=row.id, status=state))
        return row
    w.published = doc(w.corpus, "published.txt", "published")
    w.draft = doc(w.corpus, "draft.txt", "draft")
    w.archived = doc(w.corpus, "archived.txt", "archived")
    w.fake = doc(w.fake_public, "fake-public.txt", "published")
    w.failed = doc(w.corpus, "failed.txt", "published", "failed")
    for row in [w.alice_doc, w.bob_doc]:
        w.db.add(ProcessingTask(knowledge_base_id=row.knowledge_base_id, document_id=row.id, status="completed"))
    w.db.commit()
    return w


def test_each_scope_selects_only_owned_private_and_published_system_sources(sources):
    w = sources
    private = {w.alice_kb.id: [w.alice_doc.id]}
    public = {w.corpus.id: [w.published.id]}
    assert resolve_scope(w.db, w.alice, "private") == private
    assert resolve_scope(w.db, w.alice, "public") == public
    assert resolve_scope(w.db, w.alice, "both") == {**private, **public}
    assert resolve_scope(w.db, w.bob, "both") == {w.bob_kb.id: [w.bob_doc.id], **public}


@pytest.mark.parametrize("actor", ["professor", "superuser"])
def test_admin_and_legacy_superuser_cannot_expand_private_scope(sources, actor):
    w = sources
    assert resolve_scope(w.db, getattr(w, actor), "private") == {}
    assert resolve_scope(w.db, getattr(w, actor), "both") == {w.corpus.id: [w.published.id]}


def test_latest_attempt_and_publication_changes_remove_sources(sources):
    w = sources
    w.db.add(ProcessingTask(knowledge_base_id=w.alice_kb.id, document_id=w.alice_doc.id, status="failed"))
    w.published.academic_metadata.publication_status = "draft"
    w.db.commit()
    assert resolve_scope(w.db, w.alice, "both") == {}


@pytest.mark.parametrize("actor", ["inactive", "system"])
def test_inactive_and_system_actors_are_rejected_before_resolving(sources, actor):
    with pytest.raises(HTTPException) as error:
        resolve_scope(sources.db, getattr(sources, actor), "both")
    assert error.value.status_code == 401


def test_unknown_scope_never_falls_back_to_all_sources(sources):
    with pytest.raises(HTTPException) as error:
        resolve_scope(sources.db, sources.alice, "selected_documents")
    assert error.value.status_code == 422
