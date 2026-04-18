"""Tier-1 smoke tests. Run with `uv run python -m tests.smoke`.

Covers T1-3 (GSI HTTP), T1-4 (MCP stdio), T1-5 (OpenDota).
TTS and Whisper load are separate (interactive / heavy download).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import uvicorn

from dota2_coach.config import load_config
from dota2_coach.gsi_http import build_app
from dota2_coach.opendota import OpenDotaClient
from dota2_coach.server import build_mcp
from dota2_coach.state import get_state

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "sample_gsi.json"


class Reporter:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def ok(self, name: str, detail: str = "") -> None:
        print(f"  [OK]   {name}  {detail}")

    def fail(self, name: str, detail: str) -> None:
        self.failures.append(f"{name}: {detail}")
        print(f"  [FAIL] {name}  {detail}")


async def t1_3_gsi_http(r: Reporter) -> None:
    print("T1-3  GSI HTTP smoke")
    config = load_config()
    app = build_app()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", access_log=False)
    )
    server_task = asyncio.create_task(server.serve())
    try:
        # wait for startup and get actual port
        for _ in range(50):
            await asyncio.sleep(0.05)
            if server.started and server.servers and server.servers[0].sockets:
                break
        port = server.servers[0].sockets[0].getsockname()[1]
        base = f"http://127.0.0.1:{port}"

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{base}/gsi", json=payload)
            if resp.status_code == 200 and resp.json() == {"status": "ok"}:
                r.ok("POST /gsi", "200 ok")
            else:
                r.fail("POST /gsi", f"{resp.status_code} {resp.text}")

            resp = await client.get(f"{base}/healthz")
            data = resp.json()
            if data.get("has_data") and data.get("age_seconds", 999) < 2:
                r.ok("GET /healthz", f"age={data['age_seconds']:.3f}s")
            else:
                r.fail("GET /healthz", json.dumps(data))

        snap = await get_state().snapshot()
        if snap["payload"].get("hero", {}).get("name") == "npc_dota_hero_invoker":
            r.ok("state payload round-trip")
        else:
            r.fail("state payload", f"hero missing in {list(snap['payload'].keys())}")
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, timeout=2)
        except asyncio.TimeoutError:
            server_task.cancel()


async def t1_4_mcp_tools(r: Reporter) -> None:
    print("T1-4  FastMCP tool registration")
    config = load_config()
    opendota = OpenDotaClient(config)
    try:
        mcp = build_mcp(config, opendota)
        tools = await mcp.list_tools()
        names = sorted(t.name for t in tools)
        expected = sorted([
            "get_game_state", "get_hero_meta", "get_top_items",
            "get_hero_winrates", "sleep_seconds", "listen_for_command", "speak",
        ])
        if names == expected:
            r.ok("list_tools", f"{len(names)} tools")
        else:
            r.fail("list_tools", f"got={names}  expected={expected}")

        # call get_game_state directly via FastMCP
        result = await mcp.call_tool("get_game_state", {})
        # FastMCP returns (content, structured) or a single list depending on version
        payload_text = None
        if isinstance(result, tuple):
            content_list = result[0]
        else:
            content_list = result
        for c in content_list:
            text = getattr(c, "text", None)
            if text:
                payload_text = text
                break
        if payload_text and "invoker" in payload_text:
            r.ok("call_tool(get_game_state)", "contains invoker")
        else:
            r.fail("call_tool(get_game_state)", f"payload={payload_text!r:.120s}")
    finally:
        await opendota.aclose()


async def t1_5_opendota(r: Reporter) -> None:
    print("T1-5  OpenDota client")
    client = OpenDotaClient(load_config())
    try:
        meta = await client.hero_meta("invoker")
        if "error" in meta:
            r.fail("hero_meta(invoker)", meta["error"])
            return
        if meta.get("hero", "").lower() == "invoker" and meta.get("winrate"):
            r.ok("hero_meta(invoker)", f"pro_winrate={meta['winrate'].get('pro')}")
        else:
            r.fail("hero_meta(invoker)", json.dumps(meta)[:200])
    except Exception as exc:
        r.fail("hero_meta(invoker)", f"{type(exc).__name__}: {exc}")
    finally:
        await client.aclose()


async def main() -> int:
    r = Reporter()
    await t1_3_gsi_http(r)
    await t1_4_mcp_tools(r)
    await t1_5_opendota(r)
    print()
    if r.failures:
        print(f"FAILED ({len(r.failures)}):")
        for f in r.failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
