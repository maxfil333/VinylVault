"""TTL-кэш ответов Last.fm: повторные запросы не тратят квоту внешнего API."""

from __future__ import annotations

import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_sec: float, max_size: int = 500):
        self._ttl_sec = ttl_sec
        self._max_size = max_size
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at <= time.monotonic():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._items) >= self._max_size:
            self._evict()
        self._items[key] = (time.monotonic() + self._ttl_sec, value)

    def _evict(self) -> None:
        now = time.monotonic()
        for key in [k for k, (expires_at, _) in self._items.items() if expires_at <= now]:
            self._items.pop(key, None)
        # Кэш забит живыми записями — вытесняем самую старую по сроку жизни
        while len(self._items) >= self._max_size:
            oldest = min(self._items, key=lambda k: self._items[k][0])
            self._items.pop(oldest, None)
