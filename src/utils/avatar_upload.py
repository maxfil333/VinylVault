"""Чтение и проверка загружаемых аватаров."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

READ_CHUNK_SIZE = 64 * 1024


async def read_upload_up_to(file: UploadFile, max_bytes: int) -> bytes:
    """Читает upload чанками и обрывает чтение, если файл больше лимита."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=400, detail="Файл больше 5 МБ")
        chunks.append(chunk)
    return b"".join(chunks)


def detect_image_content_type(data: bytes) -> str | None:
    """Определяет тип изображения по сигнатуре файла."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
