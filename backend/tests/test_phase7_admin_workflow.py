"""Added by ChatGPT: admin inbox, terminal archive and unchanged private/source boundaries."""
from datetime import datetime
from app.models import AdminAllowlist
from app.models.knowledge import DocumentUpload, ProcessingTask
from app.services import public_corpus as service
from tests.test_phase2_authorization import world
from tests.test_phase4_public_corpus import corpus, upload, publish
from tests.test_phase3_authentication import otp, login, csrf


def test_admin_inbox_filters_pages_and_failed_sources(corpus):
    w = corpus
    task = upload(w)
    failed = DocumentUpload(knowledge_base_id=w.corpus.id, file_name="failed_source.txt", file_hash="f"*64,
        file_size=5, content_type="text/plain", temp_path=f"kb_{w.corpus.id}/temp/failed.txt", status="failed", created_at=datetime.utcnow())
    w.db.add(failed); w.db.flush()
    w.db.add(ProcessingTask(knowledge_base_id=w.corpus.id, document_upload_id=failed.id,status="failed",error_message="SECRET PROVIDER ERROR")); w.db.commit()
    headers=w.headers(w.professor)
    result=w.client.get("/api/corpus/tasks?limit=1",headers=headers)
    assert result.status_code==200
    row=result.json()[0]
    assert row["status"]=="failed" and row["document_id"] is None
    assert "SECRET" not in str(row) and "temp_path" not in row
    page=w.client.get(f"/api/corpus/tasks?before_id={row['id']}",headers=headers).json()
    assert [r["id"] for r in page]==[task["id"]]
    assert w.client.get("/api/corpus/tasks?search=_source&status=failed&publication_status=draft",headers=headers).json()==[row]
    assert w.client.get("/api/corpus/tasks?search=%25unknown",headers=headers).json()==[]
    assert w.client.get("/api/corpus/tasks?publication_status=published",headers=headers).json()==[]
    for params in ["limit=101","status=bad","before_id=0","publication_status=bad"]:
        assert w.client.get('/api/corpus/tasks?'+params,headers=headers).status_code==422


def test_inbox_and_archive_require_current_admin_and_hide_private(corpus):
    w=corpus
    task=upload(w)
    for actor in [w.alice,w.superuser]:
        assert w.client.get('/api/corpus/tasks',headers=w.headers(actor)).status_code==403
        assert w.client.post(f"/api/corpus/documents/{task['document_id']}/archive",headers=w.headers(actor)).status_code==403
    assert w.client.post(f'/api/corpus/documents/{w.bob_doc.id}/archive',headers=w.headers(w.professor)).status_code==404
    ids={r['id'] for r in w.client.get('/api/corpus/tasks',headers=w.headers(w.professor)).json()}
    assert w.task.id not in ids
    entry=w.db.query(AdminAllowlist).filter_by(email=w.professor.email).one();entry.is_active=False;w.db.commit()
    assert w.client.get('/api/corpus/tasks',headers=w.headers(w.professor)).status_code==403
    assert w.client.post(f"/api/corpus/documents/{task['document_id']}/archive",headers=w.headers(w.professor)).status_code==403


def test_archive_hides_keeps_resources_and_cannot_revive_cleanup(corpus):
    w=corpus; task=upload(w); doc_id=task['document_id'];publish(w,doc_id)
    service.set_bookmark(w.db,w.alice,doc_id,True)
    objects=dict(w.storage.objects); vectors=dict(w.store.documents)
    path=f'/api/corpus/documents/{doc_id}'
    for _ in range(2): assert w.client.post(path+'/archive',headers=w.headers(w.professor)).status_code==200
    assert w.storage.objects==objects and w.store.documents==vectors
    assert w.client.get('/api/corpus/documents?bookmarked=true',headers=w.headers(w.alice)).json()==[]
    assert w.client.get(path+'/content',headers=w.headers(w.alice)).status_code==404
    assert w.client.post('/api/corpus/query',json={'query':'irrigation'},headers=w.headers(w.alice)).json()['results']==[]
    for action in ['publish','unpublish']:
        assert w.client.post(path+'/'+action,headers=w.headers(w.professor)).status_code==409
    assert w.client.patch(path+'/metadata',json={'title':'Revive'},headers=w.headers(w.professor)).status_code==409
    assert w.client.delete(path,headers=w.headers(w.professor)).status_code==200
    assert not w.storage.objects and not w.store.documents


def test_archive_processing_conflict_and_session_csrf(corpus,otp):
    w=corpus
    login(w,w.professor.email)
    result=w.client.post('/api/corpus/documents/upload',files={'file':('session.txt',b'Synthetic irrigation evidence.','text/plain')},headers=csrf(w))
    assert result.status_code==202
    task=w.client.get(f"/api/corpus/tasks/{result.json()['id']}").json()
    path=f"/api/corpus/documents/{task['document_id']}/archive"
    w.db.rollback()
    assert w.client.post(path).status_code==403
    assert w.client.post(path,headers={**csrf(w),'Origin':'https://evil.example'}).status_code==403
    row=w.db.get(ProcessingTask,task['id']);row.status='processing';w.db.commit()
    assert w.client.post(path,headers=csrf(w)).status_code==409
    row.status='completed';w.db.commit()
    assert w.client.post(path,headers=csrf(w)).status_code==200
