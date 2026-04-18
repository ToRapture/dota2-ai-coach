"""Runtime configuration loaded from env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    gsi_host: str = "127.0.0.1"
    gsi_port: int = 27050
    opendota_api_key: str | None = None
    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_language: str = "zh"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    wake_phrases: tuple[str, ...] = ("教练", "ai教练", "ai 教练", "艾教练", "爱教练")
    exit_phrases: tuple[str, ...] = ("退出语音模式", "退出语音", "停止语音")


def load_config() -> Config:
    return Config(
        gsi_host=os.environ.get("DOTA2_COACH_GSI_HOST", "127.0.0.1"),
        gsi_port=int(os.environ.get("DOTA2_COACH_GSI_PORT", "27050")),
        opendota_api_key=os.environ.get("OPENDOTA_API_KEY") or None,
        whisper_model=os.environ.get("DOTA2_COACH_WHISPER_MODEL", "large-v3"),
        whisper_device=os.environ.get("DOTA2_COACH_WHISPER_DEVICE", "auto"),
        whisper_language=os.environ.get("DOTA2_COACH_WHISPER_LANG", "zh"),
        tts_voice=os.environ.get("DOTA2_COACH_TTS_VOICE", "zh-CN-XiaoxiaoNeural"),
    )
