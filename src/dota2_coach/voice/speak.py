"""TTS via edge-tts + miniaudio playback."""
from __future__ import annotations

import asyncio
import logging

from ..config import Config

log = logging.getLogger("dota2_coach.voice.speak")


class Speaker:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._busy = asyncio.Lock()

    async def speak(self, text: str, voice: str | None = None) -> float:
        import edge_tts

        voice = voice or self.config.tts_voice
        log.info("TTS voice=%s text=%r", voice, text[:80])
        communicate = edge_tts.Communicate(text, voice)
        mp3_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_bytes.extend(chunk["data"])

        async with self._busy:
            duration = await asyncio.get_running_loop().run_in_executor(
                None, _play_mp3_bytes, bytes(mp3_bytes)
            )
        return duration


def _play_mp3_bytes(mp3_bytes: bytes) -> float:
    import miniaudio

    decoded = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1)
    duration = decoded.duration

    device = miniaudio.PlaybackDevice(
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
        sample_rate=decoded.sample_rate,
    )
    finished = __import__("threading").Event()

    def stream_gen():
        samples = decoded.samples
        total = len(samples)
        pos = 0
        required = yield b""
        while pos < total:
            chunk = samples[pos : pos + required * decoded.nchannels]
            pos += len(chunk)
            required = yield chunk.tobytes()
        finished.set()

    gen = stream_gen()
    next(gen)
    device.start(gen)
    finished.wait(timeout=max(duration + 2.0, 5.0))
    device.close()
    return duration


_GLOBAL: Speaker | None = None


def get_speaker(config: Config) -> Speaker:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = Speaker(config)
    return _GLOBAL
