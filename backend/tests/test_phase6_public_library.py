"""Added by ChatGPT: published catalog filters, stable cursors and safe document viewing."""
import pytest
from sqlalchemy import event

from app.models import AcademicDocumentMetadata, Document
from app.models.research import Department
from app.services import public_corpus
from tests.test_phase2_authorization import world
from tests.test_phase4_public_corpus import corpus
from tests.test_phase3_authentication import otp, login, csrf
from app.models.research import Bookmark


@pytest.fixture
def catalog(corpus):
    w = corpus
    w.department = Department(name="Agronomy", code="AGR")
    w.db.add(w.department); w.db.flush()
    def create(title, *, status="published", kb=None, year=2024, author="Ayesha Rahman", kind="paper"):
        doc = Document(knowledge_base_id=(kb or w.corpus).id, file_name=f"source-{title}.pdf",
                       file_path=f"kb_{(kb or w.corpus).id}/source-{title}.pdf", file_size=100, content_type="application/pdf")
        doc.academic_metadata = AcademicDocumentMetadata(title=title, authors_text=author,
            abstract="Synthetic experimental evidence", publication_status=status, publication_year=year,
            department_id=w.department.id, document_type=kind)
        w.db.add(doc); w.db.flush()
        return doc
    w.create = create
    w.irrigation = create("Irrigation efficiency")
    w.soil = create("Soil microbiome", year=2023, author="Fatima Khan", kind="thesis")
    w.draft = create("Irrigation draft secret", status="draft")
    w.archived = create("Irrigation deleted secret", status="archived")
    w.private = create("Irrigation private secret", kb=w.bob_kb)
    w.db.commit()
    return w


def rows(w, **params):
    response = w.client.get("/api/corpus/documents", params=params, headers=w.headers(w.alice))
    assert response.status_code == 200, response.text
    return response.json()


def test_bookmarks_are_idempotent_personal_and_filterable(catalog):
    w = catalog
    path = f"/api/corpus/documents/{w.irrigation.id}/bookmark"
    for _ in range(2):
        assert w.client.post(path, headers=w.headers(w.alice)).status_code == 204
    assert [r["id"] for r in rows(w, bookmarked=True, author="Ayesha")] == [w.irrigation.id]
    assert rows(w, bookmarked=True)[0]["is_bookmarked"] is True
    assert w.client.get("/api/corpus/documents?bookmarked=true", headers=w.headers(w.professor)).json() == []
    assert w.client.delete(path, headers=w.headers(w.professor)).status_code == 204
    assert len(rows(w, bookmarked=True)) == 1
    w.db.rollback()
    assert w.db.query(Bookmark).count() == 1
    for _ in range(2):
        assert w.client.delete(path, headers=w.headers(w.alice)).status_code == 204
    assert rows(w, bookmarked=True) == []


def test_bookmarks_cannot_reveal_private_draft_or_unpublished_documents(catalog):
    w = catalog
    for doc in [w.private, w.draft, w.archived]:
        for actor in [w.alice, w.professor]:
            for method in [w.client.post, w.client.delete]:
                assert method(f"/api/corpus/documents/{doc.id}/bookmark", headers=w.headers(actor)).status_code == 404
    public_corpus.set_bookmark(w.db, w.alice, w.irrigation.id, True)
    w.irrigation.academic_metadata.publication_status = "draft"
    w.db.commit()
    assert rows(w, bookmarked=True) == []
    w.irrigation.academic_metadata.publication_status = "published"
    w.db.commit()
    assert len(rows(w, bookmarked=True)) == 1
    assert w.client.post(f"/api/corpus/documents/{w.irrigation.id}/bookmark").status_code == 401


def test_bookmark_mutations_require_session_csrf_and_origin(catalog, otp):
    w = catalog
    login(w)
    path = f"/api/corpus/documents/{w.irrigation.id}/bookmark"
    for method in [w.client.post, w.client.delete]:
        assert method(path).status_code == 403
        assert method(path, headers={**csrf(w), "Origin": "https://evil.example"}).status_code == 403
        assert method(path, headers=csrf(w)).status_code == 204


def test_catalog_returns_compact_published_metadata_and_never_private_or_draft(catalog):
    w = catalog
    result = rows(w)
    assert [row["id"] for row in result] == [w.soil.id, w.irrigation.id]
    assert result[1]["title"] == "Irrigation efficiency" and result[1]["department_name"] == "Agronomy"
    assert result[1]["authors_text"] == "Ayesha Rahman" and result[1]["publication_year"] == 2024
    assert "file_path" not in result[0] and "abstract" not in result[0]
    assert not w.storage.objects and not w.store.documents
    assert [r["id"] for r in public_corpus.list_documents(w.db, w.professor)] == [w.soil.id, w.irrigation.id]


def test_filters_compose_against_metadata_not_filenames(catalog):
    w = catalog
    w.irrigation.file_name = "opaque-file.pdf"
    w.db.commit()
    for params in [{"search": "IRRIGA"}, {"author": "rahman"}, {"year_from": 2024, "year_to": 2024},
                   {"document_type": "paper"}, {"search": "irrigation", "author": "ayesha", "department_id": w.department.id,
                    "year_from": 2024, "year_to": 2025, "document_type": "paper"}]:
        assert [row["id"] for row in rows(w, **params)] == [w.irrigation.id]
    assert len(rows(w, search="experimental")) == 2
    assert rows(w, search="opaque") == []
    assert rows(w, search="irrigation", document_type="thesis") == []
    assert rows(w, department_id=999999) == []
    assert rows(w, search="+-_%") == []


def test_author_filter_escapes_wildcard_input(catalog):
    w = catalog
    w.irrigation.academic_metadata.authors_text = "Author_100%"
    w.db.commit()
    assert [row["id"] for row in rows(w, author="_100%")] == [w.irrigation.id]
    assert rows(w, author="%unknown") == []


def test_short_acronyms_are_searchable_even_below_fulltext_token_length(catalog):
    w = catalog
    w.irrigation.academic_metadata.title = "AI irrigation"
    w.db.commit()
    assert [row["id"] for row in rows(w, search="AI")] == [w.irrigation.id]
    assert [row["id"] for row in rows(w, search="AI irrigation")] == [w.irrigation.id]


def test_cursor_pages_remain_ordered_without_duplicates(catalog):
    w = catalog
    for index in range(24): w.create(f"Catalog study {index}")
    w.db.commit()
    first = rows(w, limit=21)
    second = rows(w, limit=21, before_id=first[19]["id"])
    ids = [row["id"] for row in first[:20] + second]
    assert len(ids) == len(set(ids)) == 26 and ids == sorted(ids, reverse=True)
    assert rows(w, limit=21, before_id=first[19]["id"], document_type="thesis")[0]["id"] == w.soil.id


@pytest.mark.parametrize("params", [{"year_from":2025,"year_to":2024}, {"year_from":999}, {"year_to":10000},
    {"department_id":0}, {"document_type":"invalid"}, {"limit":101}, {"before_id":-1}, {"search":"x"*201},
    {"author":"a"*201}, {"search":" ".join(["word"]*21)}])
def test_catalog_bounds(catalog, params):
    assert catalog.client.get("/api/corpus/documents", params=params, headers=catalog.headers(catalog.alice)).status_code == 422


def test_filters_do_not_bypass_admin_or_publication_checks(catalog):
    w = catalog
    assert w.client.get("/api/corpus/documents", params={"search":"irrigation"}).status_code == 401
    assert w.client.get("/api/corpus/documents?include_unpublished=true&search=irrigation", headers=w.headers(w.alice)).status_code == 403
    w.irrigation.academic_metadata.publication_status = "draft"
    w.department.is_active = False
    w.db.commit()
    assert rows(w, search="irrigation") == []
    assert rows(w, department_id=w.department.id)[0]["department_name"] == "Agronomy"


def test_catalog_query_count_does_not_grow_with_page_size(catalog):
    w = catalog
    for index in range(15): w.create(f"Efficiency {index}")
    w.db.commit()
    statements = []
    def record(*args): statements.append(args[2])
    event.listen(w.engine, "before_cursor_execute", record)
    try:
        rows(w, limit=1); one = len(statements); statements.clear()
        rows(w, limit=20); many = len(statements)
        assert many <= one + 1
    finally:
        event.remove(w.engine, "before_cursor_execute", record)


@pytest.mark.parametrize("mime,expected", [("application/pdf","application/pdf"), ("text/plain","text/plain"),
    ("text/markdown","text/plain"), ("text/html","text/html")])
def test_inline_view_is_opt_in_mime_restricted_and_still_authorized(catalog, mime, expected):
    w = catalog
    w.irrigation.content_type = mime
    w.db.commit()
    w.storage.objects[w.irrigation.file_path] = b"Synthetic content"
    path = f"/api/corpus/documents/{w.irrigation.id}/content"
    response = w.client.get(path+"?inline=true", headers=w.headers(w.alice))
    assert response.status_code == 200 and response.headers["content-type"].startswith(expected)
    assert response.headers["content-disposition"].startswith("attachment" if mime=="text/html" else "inline")
    assert response.headers["content-security-policy"] == "sandbox"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert w.client.get(path, headers=w.headers(w.alice)).headers["content-disposition"].startswith("attachment")
    assert w.client.get(path+"?inline=true").status_code == 401
    assert w.client.get(f"/api/corpus/documents/{w.private.id}/content?inline=true", headers=w.headers(w.professor)).status_code == 404
