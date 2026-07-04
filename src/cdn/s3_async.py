"""Async S3-клиент (aioboto3) для Selectel и совместимых эндпоинтов."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3

from src.config import cfg


@asynccontextmanager
async def s3_client() -> AsyncIterator[Any]:
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
    ) as client:
        yield client
