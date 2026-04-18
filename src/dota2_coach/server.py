"""Combined FastMCP server + GSI HTTP server, single process, shared asyncio loop."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP

from .config import Config, load_config
from .gsi_http import build_app
from .opendota import OpenDotaClient
from .state import get_state
from .voice.listen import get_listener
from .voice.speak import get_speaker

log = logging.getLogger("dota2_coach.server")


def build_mcp(config: Config, opendota: OpenDotaClient) -> FastMCP:
    mcp = FastMCP("dota2-coach")
    state = get_state()

    @mcp.tool(description="获取 Dota 2 当前对局 GSI 状态 (英雄/物品/小地图/玩家等)")
    async def get_game_state() -> dict[str, Any]:
        return await state.snapshot()

    @mcp.tool(description="获取指定英雄的元数据: 胜率分段、Pro出场率、克制统计等 (OpenDota, 1h 缓存)")
    async def get_hero_meta(hero: str) -> dict[str, Any]:
        return await opendota.hero_meta(hero)

    @mcp.tool(description="获取指定英雄在 OpenDota 上的出装流行度 (1h 缓存)")
    async def get_top_items(hero: str) -> dict[str, Any]:
        return await opendota.top_items(hero)

    @mcp.tool(description="获取当前版本全英雄路人对局胜率排行 (OpenDota, 6h 缓存)")
    async def get_hero_winrates() -> dict[str, Any]:
        return {"heroes": await opendota.winrate_table()}

    @mcp.tool(
        description=(
            "轮询模式的节拍: 阻塞 n 秒. 用户按 ESC 会中断此调用, agent 会收到一个工具取消错误, "
            "此时应当停止当前轮询循环并回到默认模式."
        )
    )
    async def sleep_seconds(n: int) -> dict[str, str]:
        await asyncio.sleep(max(0, int(n)))
        return {"status": "ok"}

    listener = get_listener(config)
    speaker = get_speaker(config)

    @mcp.tool(
        description=(
            "语音模式: 监听麦克风一段语音后立即返回转录结果 (不做唤醒词过滤). "
            "返回 {text, is_exit, matched_wake, raw}: "
            "matched_wake=true 表示本段以 'AI教练' 开头, agent 应把 text 当成用户问题; "
            "matched_wake=false 表示环境噪音/旁白, agent 应忽略并再次调用本工具; "
            "is_exit=true 表示用户说了 '退出语音模式', agent 退出循环; "
            "raw 是原始 Whisper 输出 (空字符串=timeout 内没有检测到任何语音)."
        )
    )
    async def listen_for_command(timeout: int = 60) -> dict[str, Any]:
        result = await listener.listen_once(timeout=float(timeout) if timeout else None)
        return {
            "text": result.text,
            "is_exit": result.is_exit,
            "matched_wake": result.matched_wake,
            "raw": result.raw,
        }

    @mcp.tool(description="用 edge-tts 播报文本 (中文). voice 可传 zh-CN 的 edge-tts voice 名, 如 zh-CN-YunyangNeural.")
    async def speak(text: str, voice: str | None = None) -> dict[str, Any]:
        duration = await speaker.speak(text, voice)
        return {"duration_seconds": round(duration, 3)}

    return mcp


async def run(config: Config | None = None) -> None:
    config = config or load_config()
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")

    opendota = OpenDotaClient(config)
    mcp = build_mcp(config, opendota)

    app = build_app()
    uvicorn_config = uvicorn.Config(
        app,
        host=config.gsi_host,
        port=config.gsi_port,
        log_level="warning",
        access_log=False,
    )
    http = uvicorn.Server(uvicorn_config)
    http_task = asyncio.create_task(http.serve(), name="gsi-http")
    log.info("GSI HTTP endpoint: http://%s:%d/gsi", config.gsi_host, config.gsi_port)

    try:
        await mcp.run_stdio_async()
    finally:
        http.should_exit = True
        try:
            await asyncio.wait_for(http_task, timeout=2.0)
        except asyncio.TimeoutError:
            http_task.cancel()
        await opendota.aclose()


async def run_selftest(config: Config | None = None) -> int:
    config = config or load_config()
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    log.info("selftest: importing MCP/GSI modules ...")
    opendota = OpenDotaClient(config)
    try:
        mcp = build_mcp(config, opendota)
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        log.info("selftest: %d MCP tools registered: %s", len(tools), tool_names)
        expected = {
            "get_game_state",
            "get_hero_meta",
            "get_top_items",
            "get_hero_winrates",
            "sleep_seconds",
            "listen_for_command",
            "speak",
        }
        missing = expected - set(tool_names)
        if missing:
            log.error("selftest: missing tools %s", missing)
            return 1
        app = build_app()
        route_paths = [getattr(r, "path", "?") for r in app.routes]
        log.info("selftest: FastAPI routes: %s", route_paths)
        if "/gsi" not in route_paths or "/healthz" not in route_paths:
            log.error("selftest: expected routes missing")
            return 1
        log.info("selftest OK")
        return 0
    finally:
        await opendota.aclose()
