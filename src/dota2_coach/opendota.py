"""Thin async OpenDota client with in-process TTL cache."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .config import Config

BASE_URL = "https://api.opendota.com/api"


class _Cache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str, ttl: float) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: float) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl, value)


class OpenDotaClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._cache = _Cache()
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=httpx.Timeout(20.0))
        self._heroes: list[dict[str, Any]] | None = None
        self._heroes_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, ttl: float, params: dict[str, Any] | None = None) -> Any:
        cache_key = f"{path}?{sorted((params or {}).items())}"
        cached = await self._cache.get(cache_key, ttl)
        if cached is not None:
            return cached
        params = dict(params or {})
        if self._config.opendota_api_key:
            params["api_key"] = self._config.opendota_api_key
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        await self._cache.set(cache_key, data, ttl)
        return data

    async def heroes(self) -> list[dict[str, Any]]:
        async with self._heroes_lock:
            if self._heroes is None:
                self._heroes = await self._get("/heroes", ttl=24 * 3600)
            return self._heroes

    async def _find_hero(self, name: str) -> dict[str, Any] | None:
        heroes = await self.heroes()
        needle = name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        for h in heroes:
            fields = [
                h.get("localized_name", ""),
                h.get("name", "").removeprefix("npc_dota_hero_"),
                h.get("name", ""),
            ]
            for f in fields:
                if f.lower().replace(" ", "").replace("_", "").replace("-", "") == needle:
                    return h
        return None

    async def hero_stats(self) -> list[dict[str, Any]]:
        """All hero stats (picks/wins by rank bucket)."""
        return await self._get("/heroStats", ttl=6 * 3600)

    async def hero_meta(self, name: str) -> dict[str, Any]:
        hero = await self._find_hero(name)
        if not hero:
            return {"error": f"hero not found: {name}"}
        stats = await self.hero_stats()
        row = next((s for s in stats if s.get("id") == hero["id"]), None)
        matchups = await self._get(f"/heroes/{hero['id']}/matchups", ttl=3600)
        # 计算近高分段胜率 (pro + 7/8)
        def winrate(prefix: str) -> float | None:
            picks = (row or {}).get(f"{prefix}_pick")
            wins = (row or {}).get(f"{prefix}_win")
            if not picks:
                return None
            return round(wins / picks * 100, 2)

        top_counters = sorted(
            [m for m in matchups if m.get("games_played", 0) >= 100],
            key=lambda m: m["wins"] / m["games_played"],
        )[:5]
        return {
            "hero": hero["localized_name"],
            "id": hero["id"],
            "roles": hero.get("roles", []),
            "winrate": {
                "pro": winrate("pro"),
                "herald_guardian_crusader": winrate("1"),
                "archon_legend_ancient": winrate("4"),
                "divine_immortal": winrate("7"),
            },
            "pick_rate_pro": (row or {}).get("pro_pick"),
            "top_counters": [
                {"hero_id": m["hero_id"], "games": m["games_played"], "win_vs_rate": round(m["wins"] / m["games_played"] * 100, 2)}
                for m in top_counters
            ],
        }

    async def top_items(self, name: str) -> dict[str, Any]:
        hero = await self._find_hero(name)
        if not hero:
            return {"error": f"hero not found: {name}"}
        data = await self._get(f"/heroes/{hero['id']}/itemPopularity", ttl=3600)
        return {"hero": hero["localized_name"], "item_popularity": data}

    async def winrate_table(self) -> list[dict[str, Any]]:
        stats = await self.hero_stats()
        rows = []
        for s in stats:
            picks = s.get("pub_pick")
            wins = s.get("pub_win")
            if not picks:
                continue
            rows.append(
                {
                    "hero": s.get("localized_name"),
                    "pub_winrate": round(wins / picks * 100, 2),
                    "pub_pick": picks,
                }
            )
        rows.sort(key=lambda r: r["pub_winrate"], reverse=True)
        return rows
