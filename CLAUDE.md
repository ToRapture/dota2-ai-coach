# Dota 2 AI Coach — 项目说明

这是一个 Dota 2 实时教练项目：一个 MCP server (`dota2-coach`) 暴露 GSI 快照、OpenDota 元数据、麦克风监听和 edge-tts 播报；由 agent (Claude Code / OpenCode) 作为宿主驱动。

## 给 Claude Code 的指引

本仓库自带一个 project-scoped skill `.claude/skills/dota2-coach/`，描述了 AI 教练人设、三种工作模式 (默认 / 轮询 / 语音) 及其循环规则。

**用户触发方式**：用户说 "进入 AI 教练模式" / "开始教练" / "开启轮询模式" / "开启语音模式" 时，调用 `dota2-coach` skill，不需要用户手动粘贴任何 system prompt。

**MCP server**：名字是 `dota2-coach`，通过 stdio 启动 (`uv --directory <本仓库> run python -m dota2_coach`)。如果 `/mcp` 里看不到它，用户需要：
- 运行 `claude mcp add --transport stdio --scope user dota2-coach -- uv --directory <本仓库> run python -m dota2_coach`
- 或手动编辑 `%USERPROFILE%\.claude.json` 在顶层加 `mcpServers.dota2-coach` 条目 (注意不是 `~/.claude/settings.json`)

## 项目结构 (只看需要的)

- `src/dota2_coach/server.py` — FastMCP + FastAPI 合体，stdio 跑 MCP，HTTP 跑 GSI (默认 127.0.0.1:27050)
- `src/dota2_coach/voice/listen.py` — silero-vad 切片 + faster-whisper 中文转录
- `src/dota2_coach/voice/speak.py` — edge-tts + miniaudio 播放
- `gsi/gamestate_integration_coach.cfg` — 用户安装到 Dota 2 的 GSI 配置
- `prompts/system.md` — 给 OpenCode 或旧版 Claude Code 用户手动贴的 system prompt (内容与 skill 文件保持一致)

## 冒烟验证

```powershell
uv run python -m dota2_coach --selftest       # 7 个 MCP 工具 + GSI 路由
uv run python -m tests.smoke                  # GSI / MCP / OpenDota
uv run python -m tests.tts_smoke              # edge-tts 合成 (不播放)
uv run python -m tests.whisper_load           # 首次会下 whisper base (~140MB)
```
