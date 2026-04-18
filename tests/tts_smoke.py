"""T1-6 TTS: synthesize audio via edge-tts and decode via miniaudio,
WITHOUT playing through speakers (CI-friendly)."""
from __future__ import annotations

import asyncio
import sys


async def main() -> int:
    import edge_tts
    import miniaudio

    voice = "zh-CN-XiaoxiaoNeural"
    text = "测试语音合成"
    print(f"T1-6  edge-tts synthesize voice={voice} text={text!r}")

    communicate = edge_tts.Communicate(text, voice)
    mp3 = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3.extend(chunk["data"])

    if len(mp3) < 1000:
        print(f"  [FAIL] MP3 too small: {len(mp3)} bytes")
        return 1
    print(f"  [OK]   MP3 generated: {len(mp3)} bytes")

    decoded = miniaudio.decode(bytes(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1)
    duration = decoded.duration
    if duration < 0.3:
        print(f"  [FAIL] decoded duration too short: {duration}s")
        return 1
    print(f"  [OK]   miniaudio decode: {duration:.2f}s, sr={decoded.sample_rate}Hz")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
