"""Checks shared by public/private ingestion, before any object is stored."""
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile

from fastapi import HTTPException

from app.services.document_processor import validate_docx_archive

CONTENT_TYPES = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown",
                 ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def validate_filename(name: str, *, max_chars=200, max_bytes=255):
    if (not name or len(name) > max_chars or len(name.encode("utf-8")) > max_bytes
            or any(c in name for c in '/\\:') or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or PurePosixPath(name).suffix.lower() not in CONTENT_TYPES):
        raise HTTPException(400, "Use a plain filename with PDF, DOCX, TXT or MD extension")
    return name


def validate_document(name: str, content: bytes, declared_type: str | None = None) -> str:
    validate_filename(name)
    extension = PurePosixPath(name).suffix.lower()
    mime = CONTENT_TYPES[extension]
    # Browsers may omit MIME or send generic binary; neither bypasses content checks.
    declared = (declared_type or "").split(";", 1)[0].strip().lower()
    allowed = {"", "application/octet-stream", mime}
    if extension == ".md":
        allowed.add("text/plain")
    if not content:
        raise HTTPException(400, "Choose a non-empty document")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(400, "Invalid PDF document")
    if extension == ".docx":
        try:
            validate_docx_archive(BytesIO(content))
        except (BadZipFile, ValueError, OSError):
            raise HTTPException(400, "Invalid or oversized DOCX document") from None
    if extension in {".txt", ".md"}:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "Text documents must use UTF-8 encoding") from None
        if "\x00" in text:
            raise HTTPException(400, "Text documents must not contain binary data")
    if declared not in allowed:
        raise HTTPException(415, "Document content type does not match its extension")
    return mime
