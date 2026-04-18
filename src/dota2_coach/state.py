"""In-memory store of the latest Dota 2 GSI snapshot."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class GameState:
    def __init__(self) -> None:
        self._payload: dict[str, Any] = {}
        self._received_at: float = 0.0
        self._lock = asyncio.Lock()
        self._updated = asyncio.Event()

    async def update(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            self._payload = payload
            self._received_at = time.time()
            self._updated.set()
            self._updated.clear()

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "received_at": self._received_at,
                "age_seconds": (time.time() - self._received_at) if self._received_at else None,
                "has_data": bool(self._payload),
                "payload": self._payload,
            }

    async def wait_for_update(self, timeout: float | None = None) -> bool:
        try:
            await asyncio.wait_for(self._updated.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


_GLOBAL: GameState | None = None


def get_state() -> GameState:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = GameState()
    return _GLOBAL
