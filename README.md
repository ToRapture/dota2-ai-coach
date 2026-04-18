# Dota 2 AI Coach

一个基于 **GSI + MCP + LLM** 的 Dota 2 实时教练工具。由 Claude Code 或 OpenCode 作为 agent 宿主驱动，通过 MCP server 接入：

- 你当前对局的 GSI 数据（英雄、等级、经济、物品、事件…）
- OpenDota 的版本元数据（胜率、出装流行度、克制关系）
- 本地麦克风输入（Whisper 伪唤醒词 "教练" / "AI教练"）
- 本地语音播报（edge-tts）
- 一个"轮询节拍"工具（`sleep_seconds`，可用 ESC 打断）

运行时 agent 可以在三种模式之间切换：

| 模式 | 进入方式 | 说明 |
|---|---|---|
| **默认（打字）** | 直接对话 | 打字提问 → 文字回答 + 语音播报 |
| **轮询** | 说 "开启轮询模式" | 每 30 秒分析当前对局并播报，ESC 打断 |
| **语音** | 说 "开启语音模式" | 说 "教练, 要不要买 BKB" 即可提问，说 "教练 退出语音模式" 离开 |

---

## 系统要求

- **Windows 10 / 11**（脚本用 PowerShell；Dota 2 GSI 配置路径也是 Windows）
- **Python 3.11+**
- **Steam 版 Dota 2**，启动项需要加 `-gamestateintegration`
- **麦克风**（如需语音模式）
- 可选：NVIDIA GPU（Whisper/VAD 更快，不是必须；CPU 上也能跑）
- **Claude Code** 或 **OpenCode** 其中之一

---

## 安装

### 1. 装 uv（Python 项目管理器）

```powershell
winget install astral-sh.uv
```

或参考 <https://github.com/astral-sh/uv> 的官方安装方式。

### 2. 克隆项目并拉依赖

```powershell
git clone https://github.com/ToRapture/dota2-ai-coach.git
cd dota2-ai-coach
uv sync
```

首次 `uv sync` 会装 PyTorch（约 600MB）等依赖。

`faster-whisper` 的 `base` 模型（约 140MB）在第一次调用语音工具时自动下载，不需要手动操作。

### 3. 安装 Dota 2 GSI 配置

```powershell
pwsh scripts\install-gsi.ps1
```

脚本会：
1. 自动定位 Steam 里 Dota 2 的安装目录
2. 将 `gsi\gamestate_integration_coach.cfg` 复制到 `…\dota 2 beta\game\dota\cfg\gamestate_integration\`

如果自动定位失败，传参指定根目录：
```powershell
pwsh scripts\install-gsi.ps1 -DotaRoot "D:\SteamLibrary\steamapps\common\dota 2 beta"
```

### 4. 给 Dota 2 加启动项

Steam 库 → 右键 Dota 2 → 属性 → 启动选项 → 添加：
```
-gamestateintegration
```

### 5. 配置 agent 的 MCP

#### Claude Code

推荐走 CLI：

```powershell
claude mcp add --transport stdio --scope user dota2-coach -- uv --directory D:/Codes/github/ToRapture/dota2-ai-coach run python -m dota2_coach
```

或者手动编辑 `%USERPROFILE%\.claude.json`（**注意是家目录下的点文件，不是 `%USERPROFILE%\.claude\settings.json`**。Claude Code 不会从 `settings.json` 读取 `mcpServers`），在顶层 `"mcpServers"` 键下添加：

```json
"dota2-coach": {
  "command": "uv",
  "args": ["--directory", "D:/Codes/github/ToRapture/dota2-ai-coach", "run", "python", "-m", "dota2_coach"]
}
```

> 记得把 `--directory` 改成你自己的项目路径。改完重启 Claude Code 终端，会话里 `/mcp` 看到 `dota2-coach connected` 即可。

本仓库自带 `.claude/skills/dota2-coach/` 与根目录 `CLAUDE.md`：**在项目目录启动 Claude Code 后，直接说 "进入 AI 教练模式"，agent 会自动激活 skill，不需要再手动粘贴 `prompts/system.md`**。

#### OpenCode

编辑 `~/.config/opencode/config.json`（Windows 上一般是 `C:\Users\<你>\AppData\Roaming\opencode\config.json`）：

```json
{
  "mcp": {
    "dota2-coach": {
      "type": "local",
      "command": [
        "uv",
        "--directory",
        "D:/Codes/github/ToRapture/dota2-ai-coach",
        "run",
        "python",
        "-m",
        "dota2_coach"
      ],
      "enabled": true
    }
  }
}
```

### 6. 冒烟验证

```powershell
uv run python -m dota2_coach --selftest
```

应该看到 7 个 MCP 工具注册成功、GSI 路由 `/gsi` 和 `/healthz` 已绑定。

更完整的 smoke 测试（会请求 OpenDota、下载 Whisper base 模型约 140MB）：

```powershell
uv run python -m tests.smoke         # GSI / MCP / OpenDota
uv run python -m tests.tts_smoke     # edge-tts 合成 (不播放)
uv run python -m tests.whisper_load  # 首次跑会下载 whisper 模型
```

---

## 启动

1. 启动 Dota 2，进入任意对局或 demo
2. 开一个终端，进项目目录，跑 `claude` 或 `opencode`
3. **Claude Code**：直接说 "进入 AI 教练模式"，会话会通过仓库里的 `.claude/skills/dota2-coach/` 自动加载人设
   **OpenCode**：把 `prompts/system.md` 的内容作为第一条消息贴给 agent
4. 用以下任意一种方式交互：

### 默认模式（打字）
```
我现在是影魔中单对线水晶室女，该先出黑切还是魔瓶？
```

### 轮询模式
```
开启轮询模式
```
之后 agent 会每 30 秒分析一次对局并播报。想停下时：**按 ESC** 打断当前工具调用，然后打字"停止"或直接说别的。

### 语音模式
```
开启语音模式
```
之后对着麦克风说：
```
教练  我该买什么装备
教练  什么时候肉山
教练  退出语音模式
```

想强制退出：**按 ESC** 中断工具调用。

---

## 模式切换 / 退出机制

| 场景 | 操作 |
|---|---|
| 轮询或语音模式下想停 | **按 ESC** 中断 → agent 收到工具取消错误，回退到默认模式 |
| 语音模式下"软"退出 | 说 "教练 退出语音模式" |
| 完全结束会话 | 直接关掉 Claude Code / OpenCode 终端 |

---

## 常见问题

### GSI 没数据
1. 先 `curl http://127.0.0.1:27050/healthz` 看服务是否活着
2. 确认 Dota 2 启动项里有 `-gamestateintegration`
3. 开一局 demo，静候 5-10 秒，再 `/healthz` 看 `has_data`
4. Dota 2 窗口模式切出，看终端是否有日志 `GSI payload received`

### 语音模式识别不到唤醒词
- 说话前先深呼吸停顿一下，让 VAD 能检测到完整语音段
- 说完整 "教练 ..." 或 "AI教练 ..."，不要拖音
- 环境太吵时 Whisper 可能识别成"爱教练"/"AI叫练"，config 里默认都匹配
- 调大灵敏度可以改 `whisper_model` 为 `small`（pyproject.toml 装更大模型 → 更准但更慢）

### edge-tts 没声音
- Windows 默认播放设备对了吗？（蓝牙耳机/USB 声卡有时会被 sounddevice 跳过）
- `miniaudio` 装失败的话 `uv sync` 会报错；MSVC Build Tools 没装的话可以装 <https://aka.ms/vs/17/release/vs_BuildTools.exe>

### OpenDota 请求被限流
OpenDota 免费档 60 req/min。本项目已经做了 1-6h 的 TTL 缓存，正常使用不会触发。若被限流，申请一个 key：<https://www.opendota.com/api-keys>，然后：
```powershell
setx OPENDOTA_API_KEY "你的key"
```

### Windows 麦克风权限
设置 → 隐私和安全性 → 麦克风 → 允许应用使用麦克风 / 允许桌面应用使用麦克风 都要打开。

---

## 环境变量（全部可选）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DOTA2_COACH_GSI_HOST` | `127.0.0.1` | GSI HTTP 监听地址 |
| `DOTA2_COACH_GSI_PORT` | `27050` | GSI HTTP 监听端口 |
| `OPENDOTA_API_KEY` | 空 | OpenDota API key |
| `DOTA2_COACH_WHISPER_MODEL` | `base` | `tiny` / `base` / `small` / `medium` |
| `DOTA2_COACH_WHISPER_DEVICE` | `auto` | `auto` / `cpu` / `cuda` |
| `DOTA2_COACH_WHISPER_LANG` | `zh` | whisper 识别语言 |
| `DOTA2_COACH_TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 见 `edge-tts --list-voices` |

---

## 完全删除

一条命令清除本地痕迹（不会碰 agent 配置）：

```powershell
pwsh scripts\uninstall-all.ps1
```

它会：
1. 删除 Dota 2 目录下的 `gamestate_integration_coach.cfg`
2. 删除项目 `.venv`
3. 清理 uv 缓存
4. 删除 HuggingFace / torch hub 里的 whisper + silero-vad 模型缓存

**仍需手动**：
1. 从 Claude Code `%USERPROFILE%\.claude.json` (顶层 `mcpServers` 键) / OpenCode `config.json` 中删掉 `dota2-coach` 条目
2. 在 Steam Dota 2 启动项里去掉 `-gamestateintegration`
3. 要连项目源码也删掉：`Remove-Item -Recurse -Force D:\Codes\github\ToRapture\dota2-ai-coach`

---

## 许可证 / 致谢

- [Dota 2 GSI](https://developer.valvesoftware.com/wiki/Dota_2_Workshop_Tools/Scripting/Game_State_Integration)
- [OpenDota API](https://docs.opendota.com/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [silero-vad](https://github.com/snakers4/silero-vad)
- [edge-tts](https://github.com/rany2/edge-tts)
- [Model Context Protocol](https://modelcontextprotocol.io/)
