"""Standalone voice debug: runs VAD+Whisper continuously and prints each transcription.

Usage:
    uv run python -m tests.voice_debug

Press Ctrl+C to stop.
Each detected speech segment prints:
    raw    : exact Whisper output
    matched: whether wake phrase matched
    body   : text after stripping wake phrase prefix
"""
from __future__ import annotations

import sys
import os

# Force UTF-8 so Chinese doesn't blow up on Windows cp932
for _attr in ("stdout", "stderr"):
    _s = getattr(sys, _attr, None)
    if _s:
        try:
            _s.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

import logging
logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(name)s: %(message)s")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dota2_coach.config import load_config
from dota2_coach.voice.listen import VoiceListener

def main() -> None:
    config = load_config()
    print(f"Wake phrases : {config.wake_phrases}")
    print(f"Exit phrases : {config.exit_phrases}")
    print(f"Whisper model: {config.whisper_model}  lang={config.whisper_language}")
    print("Listening... (Ctrl+C to stop)\n")

    listener = VoiceListener(config)
    listener._ensure_loaded()

    while True:
        result = listener._blocking_listen(timeout=30)
        if not result.raw:
            print("[timeout — no speech detected in 30s]")
            continue
        wake_mark = "✓ WAKE" if result.matched_wake else "✗ skip"
        exit_mark = " [EXIT]" if result.is_exit else ""
        print(f"[{wake_mark}]{exit_mark}")
        print(f"  raw  : {result.raw!r}")
        if result.matched_wake:
            print(f"  body : {result.text!r}")
        print()
        if result.is_exit:
            print("Exit phrase detected — stopping.")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
