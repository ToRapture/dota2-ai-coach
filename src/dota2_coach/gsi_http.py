"""FastAPI app exposing /gsi for Dota 2 Game State Integration."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request

from .state import get_state

log = logging.getLogger("dota2_coach.gsi")


def build_app() -> FastAPI:
    app = FastAPI(title="dota2-coach GSI receiver")
    state = get_state()

    @app.post("/gsi")
    async def gsi(request: Request) -> dict[str, str]:
        payload = await request.json()
        await state.update(payload)
        log.debug("GSI payload received: keys=%s", list(payload.keys()))
        return {"status": "ok"}

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        snap = await state.snapshot()
        return {"ok": True, "has_data": snap["has_data"], "age_seconds": snap["age_seconds"]}

    return app
