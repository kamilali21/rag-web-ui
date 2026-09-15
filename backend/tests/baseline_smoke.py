"""Added by ChatGPT: opt-in live PDF -> retrieval -> cited chat acceptance check.

Run from backend with: python -m tests.baseline_smoke
Uses synthetic data and the configured providers. Never prints credentials.
"""
import base64
import io
import json
import os
import re
import secrets
import time
import uuid

import requests
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def fixture_pdf():
    # Added by ChatGPT: one-page synthetic evidence generated in memory, with no real research data.
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 48 730 Td "
                    b"(ResearchIQ synthetic irrigation experiment.) Tj 0 -24 Td "
                    b"(The experiment included 120 plots.) Tj 0 -24 Td "
                    b"(Drip irrigation reduced water use by 23 percent.) Tj 0 -24 Td "
                    b"(This is software test data, not a scientific finding.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def run():
    base = os.getenv("BASELINE_API_URL", "http://nginx/api").rstrip("/")
    session = requests.Session()
    name = f"baseline_{uuid.uuid4().hex[:16]}"
    user_id = kb_id = chat_id = None
    task_ids = []
    verified = []

    def check(method, path, **kwargs):
        response = session.request(method, base + path, timeout=(10, 180), **kwargs)
        if not response.ok:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}")
        return response

    def passed(step):
        verified.append(step)
        print(json.dumps({"passed": step}), flush=True)

    try:
        password = secrets.token_urlsafe(24)
        user_id = check("POST", "/auth/register", json={
            "email": f"{name}@example.com", "username": name, "password": password
        }).json()["id"]
        token = check("POST", "/auth/token", data={"username": name, "password": password}).json()["access_token"]
        session.headers["Authorization"] = f"Bearer {token}"
        passed("existing registration and sign-in")
        kb_id = check("POST", "/knowledge-base", json={"name": name, "description": "Synthetic baseline acceptance test"}).json()["id"]
        print(json.dumps({"fixture_user_id": user_id, "fixture_kb_id": kb_id}), flush=True)
        uploaded = check("POST", f"/knowledge-base/{kb_id}/documents/upload", files={
            "files": ("baseline-irrigation.pdf", fixture_pdf(), "application/pdf")
        }).json()
        preview = check("POST", f"/knowledge-base/{kb_id}/documents/preview", json={
            "document_ids": [uploaded[0]["upload_id"]], "chunk_size": 1000, "chunk_overlap": 200
        }).json()
        assert "120" in json.dumps(preview), "PDF extraction lost the synthetic fact"
        passed("PDF upload, MinIO storage and text preview")
        tasks = check("POST", f"/knowledge-base/{kb_id}/documents/process", json=uploaded).json()["tasks"]
        task_ids = [task["task_id"] for task in tasks]
        deadline = time.monotonic() + 180
        while True:
            task_status = check("GET", f"/knowledge-base/{kb_id}/documents/tasks", params={
                "task_ids": ",".join(map(str, task_ids))
            }).json()
            rows = [task_status[str(task_id)] for task_id in task_ids if str(task_id) in task_status]
            if any(row["status"] == "failed" for row in rows):
                raise RuntimeError("Synthetic PDF processing failed; inspect its task before retrying")
            if rows and all(row["status"] == "completed" for row in rows):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Synthetic PDF processing timed out")
            time.sleep(2)
        library = check("GET", f"/knowledge-base/{kb_id}").json()
        document_id = library["documents"][0]["id"]
        passed("PDF processing and relational document persistence")
        retrieval = check("POST", "/knowledge-base/test-retrieval", json={
            "kb_id": kb_id, "query": "How many plots were included?", "top_k": 2
        }).json()
        assert "120" in json.dumps(retrieval), "Retrieval omitted the synthetic fact"
        passed("configured embeddings and Chroma retrieval")
        chat_id = check("POST", "/chat/", json={"title": name, "knowledge_base_ids": [kb_id]}).json()["id"]
        response = check("POST", f"/chat/{chat_id}/messages", json={"messages": [{
            "role": "user", "content": "How many plots were in the synthetic irrigation experiment? Cite the document."
        }]}, stream=True)
        content, complete = "", False
        with response:
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("3:"):
                    raise RuntimeError("Configured LLM failed during streamed answer generation")
                if line.startswith("0:"):
                    content += json.loads(line[2:])
                if line.startswith("d:"):
                    complete = True
        encoded, answer = content.split("__LLM_RESPONSE__", 1)
        evidence = json.loads(base64.b64decode(encoded))["context"]
        citations = [int(value) for value in re.findall(r"\[citation:(\d+)\]", answer)]
        assert complete and "120" in answer and citations, "Incomplete or uncited synthetic answer"
        assert all(1 <= index <= len(evidence) for index in citations), "Invented citation index"
        assert all(evidence[index - 1]["metadata"]["document_id"] == document_id for index in citations)
        assert all(evidence[index - 1]["metadata"]["page"] == 0 for index in citations)
        saved = check("GET", f"/chat/{chat_id}").json()
        assert any(message["content"] == content for message in saved["messages"]), "Chat was not persisted"
        passed("real LLM streaming, grounded citation mapping and saved conversation")
    finally:
        # Added by ChatGPT: remove only records created by this invocation, never existing user data.
        if chat_id is not None:
            check("DELETE", f"/chat/{chat_id}")
        if kb_id is not None:
            cleanup = check("DELETE", f"/knowledge-base/{kb_id}").json()
            if cleanup.get("warnings"):
                raise RuntimeError("Synthetic collection cleanup reported warnings")
            from app.core.config import settings
            from app.core.minio import get_minio_client
            import chromadb
            from chromadb.errors import NotFoundError
            client = chromadb.HttpClient(host=settings.CHROMA_DB_HOST, port=settings.CHROMA_DB_PORT)
            try:
                client.get_collection(f"kb_{kb_id}")
            except NotFoundError:
                pass
            else:
                raise RuntimeError("Synthetic Chroma collection was not deleted")
            assert not list(get_minio_client().list_objects(settings.MINIO_BUCKET_NAME, prefix=f"kb_{kb_id}/", recursive=True))
        if user_id is not None:
            from app.db.session import SessionLocal
            from app.models.user import User
            from app.models.knowledge import ProcessingTask
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == user_id, User.username == name).one()
                assert not user.knowledge_bases and not user.chats
                for task in db.query(ProcessingTask).filter(ProcessingTask.id.in_(task_ids)).all():
                    db.delete(task)
                db.delete(user)
                db.commit()
            passed("synthetic fixture cleanup")
        session.close()
    print(json.dumps({"result": "passed", "checks": verified}), flush=True)


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        # Report assertion/known test failures only; provider errors can contain secrets.
        message = str(error) if isinstance(error, (AssertionError, RuntimeError)) else type(error).__name__
        print(json.dumps({"result": "failed", "reason": message}), flush=True)
        raise SystemExit(1)
