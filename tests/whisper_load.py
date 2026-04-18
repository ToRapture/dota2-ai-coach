"""T1-7 Whisper + silero-vad model load (no mic interaction).

Will download the base whisper model (~140MB) on first run.
"""
from __future__ import annotations

import sys
import time

from dota2_coach.config import load_config
from dota2_coach.voice.listen import VoiceListener


def main() -> int:
    config = load_config()
    listener = VoiceListener(config)
    start = time.time()
    print(f"T1-7  loading silero-vad + faster-whisper (model={config.whisper_model}, device={config.whisper_device})")
    listener._ensure_loaded()
    elapsed = time.time() - start
    print(f"  [OK]   loaded in {elapsed:.2f}s")

    # Synthesize 1s of silence and transcribe to sanity-check whisper invocation
    import numpy as np

    audio = np.zeros(16000, dtype=np.float32)
    segments, info = listener._whisper.transcribe(
        audio, language="zh", vad_filter=False, beam_size=1,
    )
    text = "".join(seg.text for seg in segments).strip()
    print(f"  [OK]   transcribe(silence) detected_lang={info.language} text={text!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
