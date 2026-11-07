"""Disposable Linux parser worker. No database, embedding model or LLM access."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from app.services import preview_limits as limits


class PreviewLimit(ValueError):
    pass


def constrain_process():
    # The supported application runtime is Linux Docker. Fail closed elsewhere.
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (limits.MEMORY_BYTES, limits.MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (limits.CPU_SECONDS, limits.CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.MAX_FILE_BYTES, limits.MAX_FILE_BYTES))


def parse_file(path, size, overlap, source):
    limits.check_chunk_settings(size, overlap)
    if Path(path).stat().st_size > limits.MAX_FILE_BYTES:
        raise PreviewLimit("File is too large to preview")
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    chunks, text_chars, output_chars = [], 0, 0

    def add(text, metadata):
        nonlocal text_chars, output_chars
        text_chars += len(text)
        if len(text) > limits.MAX_PAGE_CHARS or text_chars > limits.MAX_TEXT_CHARS:
            raise PreviewLimit("Extracted text exceeds the preview limit")
        # Split one bounded page at a time, never an unbounded document list.
        for content in splitter.split_text(text):
            if len(chunks) >= limits.MAX_CHUNKS:
                raise PreviewLimit("Document exceeds the preview chunk limit")
            output_chars += len(content)
            if output_chars > limits.MAX_TEXT_CHARS * 2:
                raise PreviewLimit("Preview output is too large")
            chunks.append({"content": content, "metadata": {"source": source, **metadata}})

    extension = Path(path).suffix.lower()
    if extension == ".pdf":
        from pypdf import PdfReader
        with open(path, "rb") as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted or len(reader.pages) > limits.MAX_PAGES:
                raise PreviewLimit("Encrypted PDF or too many pages for preview")
            for index, page in enumerate(reader.pages):
                add(page.extract_text() or "", {"page": index, "total_pages": len(reader.pages)})
    elif extension == ".docx":
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if (len(entries) > 5000 or "word/document.xml" not in archive.namelist()
                    or sum(e.file_size for e in entries) > 100 * 1024 * 1024):
                raise PreviewLimit("DOCX archive exceeds preview limits")
        import docx2txt
        text = docx2txt.process(path)
        if len(text) > limits.MAX_TEXT_CHARS:
            raise PreviewLimit("Extracted text exceeds the preview limit")
        # Non-paged formats use bounded text segments without rejecting normal theses.
        for start in range(0, len(text), limits.MAX_PAGE_CHARS):
            add(text[start:start + limits.MAX_PAGE_CHARS], {})
    elif extension in {".txt", ".md"}:
        with open(path, encoding="utf-8") as stream:
            text = stream.read(limits.MAX_TEXT_CHARS + 1)
        if len(text) > limits.MAX_TEXT_CHARS:
            raise PreviewLimit("Extracted text exceeds the preview limit")
        for start in range(0, len(text), limits.MAX_PAGE_CHARS):
            add(text[start:start + limits.MAX_PAGE_CHARS], {})
    else:
        raise PreviewLimit("Unsupported preview file type")
    result = {"chunks": chunks, "total_chunks": len(chunks)}
    if len(json.dumps(result).encode()) > limits.MAX_OUTPUT_BYTES:
        raise PreviewLimit("Preview output is too large")
    return result


def download(client, bucket, key, path):
    if client.stat_object(bucket, key).size > limits.MAX_FILE_BYTES:
        raise PreviewLimit("File is too large to preview")
    response = client.get_object(bucket, key)
    try:
        total = 0
        with open(path, "wb") as target:
            while True:
                part = response.read(min(64 * 1024, limits.MAX_FILE_BYTES - total + 1))
                if not part:
                    break
                total += len(part)
                if total > limits.MAX_FILE_BYTES:
                    raise PreviewLimit("File is too large to preview")
                target.write(part)
    finally:
        response.close()
        response.release_conn()


def main():
    constrain_process()
    payload = json.loads(sys.stdin.read(8192))
    # Scratch directory is created/owned by the parent, which removes it even if killed.
    directory = Path(sys.argv[1])
    try:
        from app.core.minio import get_minio_client
        from app.core.config import settings
        key = payload["key"]
        path = directory / ("input" + Path(key).suffix.lower())
        download(get_minio_client(), settings.MINIO_BUCKET_NAME, key, path)
        result = parse_file(path, payload["size"], payload["overlap"], key)
        status = {"ok": result}
    except PreviewLimit as error:
        status = {"error": str(error), "status": 413}
    except Exception:
        status = {"error": "Document could not be previewed; check its format and retry", "status": 422}
    (directory / "result.json").write_text(json.dumps(status), encoding="utf-8")


if __name__ == "__main__":
    main()
