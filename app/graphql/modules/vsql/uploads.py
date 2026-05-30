"""GraphQL multipart upload helpers: size limits and streaming to disk."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

# Maximum CSV/video upload size (10 GiB), enforced while streaming.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024

# Read chunk size for streaming uploads (1 MiB).
STREAM_CHUNK_SIZE = 1024 * 1024


async def stream_upload_to_file(
    upload: Any,
    dest: Path,
    *,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> int:
    """
    Copy an upload object to ``dest`` without holding the whole body in memory.

    Supports Starlette UploadFile (async read), plain ``bytes``, or sync ``read(n)``.

    Returns total bytes written. Raises ``ValueError`` on invalid upload or oversize file.
    """
    if upload is None:
        raise ValueError("No file was provided")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.unlink(missing_ok=True)

    total = 0

    try:
        if isinstance(upload, (bytes, bytearray, memoryview)):
            data = bytes(upload)
            if len(data) > max_bytes:
                raise ValueError(
                    f"File exceeds maximum allowed size ({max_bytes // (1024 ** 3)} GiB)"
                )
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            return len(data)

        if isinstance(upload, dict):
            raise ValueError(
                "Invalid file upload: the file variable was sent as JSON instead of a "
                "binary multipart part. Use GraphQL multipart/form-data."
            )

        read = getattr(upload, "read", None)
        if not callable(read):
            raise ValueError(f"Upload has no read() method (got {type(upload)!r})")

        with open(tmp, "wb") as out:
            while True:
                chunk = read(STREAM_CHUNK_SIZE)
                if asyncio.iscoroutine(chunk):
                    chunk = await chunk
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise ValueError("File read() did not return bytes")
                blen = len(chunk)
                total += blen
                if total > max_bytes:
                    raise ValueError(
                        f"File exceeds maximum allowed size ({max_bytes // (1024 ** 3)} GiB)"
                    )
                out.write(chunk)

        os.replace(tmp, dest)
        return total
    except ValueError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
