"""Killable preview parsing; no blocking parser/download on the ASGI event loop."""
import asyncio
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore

from fastapi import HTTPException
from app.services import preview_limits as limits

_slots = BoundedSemaphore(limits.MAX_PARALLEL)


async def preview(file_path, size, overlap):
    limits.check_chunk_settings(size, overlap)
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Document previews are busy; retry shortly", headers={"Retry-After": "2"})
    process = None
    try:
        with TemporaryDirectory(prefix="researchiq-preview-") as scratch:
            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "app.services.preview_worker", scratch,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                body = json.dumps({"key": file_path, "size": size, "overlap": overlap}).encode()
                await asyncio.wait_for(process.communicate(body), timeout=limits.TIMEOUT_SECONDS)
                output = Path(scratch) / "result.json"
                if process.returncode != 0 or not output.exists():
                    raise HTTPException(422, "Document exceeded parser resources or could not be previewed")
                if output.stat().st_size > limits.MAX_OUTPUT_BYTES + 1024:
                    raise HTTPException(413, "Preview output is too large")
                result = json.loads(output.read_text(encoding="utf-8"))
                if "error" in result:
                    raise HTTPException(result["status"], result["error"])
                return result["ok"]
            except asyncio.TimeoutError:
                raise HTTPException(504, "Document preview timed out; try a smaller document") from None
            finally:
                # Cancellation/timeout must reap the child BEFORE releasing its capacity
                # and before deleting scratch files, including partial downloads.
                if process is not None and process.returncode is None:
                    process.kill()
                    await process.wait()
    finally:
        _slots.release()
