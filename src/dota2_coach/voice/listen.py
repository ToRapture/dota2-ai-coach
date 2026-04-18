"""Microphone listening: silero-vad segments, faster-whisper transcribes,
pseudo wake phrase detection ("AI教练")."""
from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import sounddevice as sd

from ..config import Config

log = logging.getLogger("dota2_coach.voice.listen")

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512  # silero-vad requires 512 at 16kHz
MAX_UTTERANCE_SECONDS = 15.0


@dataclass
class ListenResult:
    text: str
    is_exit: bool
    matched_wake: bool
    raw: str


class VoiceListener:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._whisper = None
        self._vad_model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._vad_model is None:
                from silero_vad import load_silero_vad

                self._vad_model = load_silero_vad()
            if self._whisper is None:
                from faster_whisper import WhisperModel

                device = self.config.whisper_device
                if device == "auto":
                    try:
                        import torch

                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    except Exception:
                        device = "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                log.info("Loading faster-whisper model=%s device=%s", self.config.whisper_model, device)
                self._whisper = WhisperModel(self.config.whisper_model, device=device, compute_type=compute_type)

    async def listen_once(self, timeout: float | None = 60.0) -> ListenResult:
        self._ensure_loaded()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._blocking_listen, timeout)

    def _blocking_listen(self, timeout: float | None) -> ListenResult:
        from silero_vad import VADIterator

        vad_iter = VADIterator(
            self._vad_model,
            threshold=0.5,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=600,
            speech_pad_ms=200,
        )
        q: queue.Queue[np.ndarray] = queue.Queue()
        deadline = time.time() + timeout if timeout else None

        def cb(indata, frames, time_info, status):  # sounddevice thread
            if status:
                log.debug("sounddevice status: %s", status)
            q.put(indata.copy().reshape(-1))

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=cb,
        ):
            speech_started = False
            collected: list[np.ndarray] = []
            speech_start_time: float | None = None

            while True:
                if deadline and time.time() > deadline:
                    return ListenResult(text="", is_exit=False, matched_wake=False, raw="")

                try:
                    chunk = q.get(timeout=0.2)
                except queue.Empty:
                    continue

                if chunk.shape[0] != FRAME_SAMPLES:
                    continue

                event = vad_iter(chunk, return_seconds=False)
                if event:
                    if "start" in event:
                        speech_started = True
                        speech_start_time = time.time()
                        collected = [chunk]
                        continue
                    if "end" in event and speech_started:
                        collected.append(chunk)
                        audio = np.concatenate(collected, axis=0).astype(np.float32)
                        result = self._transcribe(audio)
                        vad_iter.reset_states()
                        return result

                if speech_started:
                    collected.append(chunk)
                    if speech_start_time and (time.time() - speech_start_time) > MAX_UTTERANCE_SECONDS:
                        audio = np.concatenate(collected, axis=0).astype(np.float32)
                        result = self._transcribe(audio)
                        vad_iter.reset_states()
                        return result

    def _transcribe(self, audio: np.ndarray) -> ListenResult:
        segments, _info = self._whisper.transcribe(
            audio,
            language=self.config.whisper_language,
            initial_prompt="以下是普通话对话。",
            vad_filter=False,
            beam_size=5,
        )
        text = "".join(seg.text for seg in segments).strip()
        log.info("ASR: %r", text)
        return _match_phrase(text, self.config.wake_phrases, self.config.exit_phrases)


def _normalize(s: str) -> str:
    return "".join(ch for ch in s.lower() if not ch.isspace() and ch not in "，。！？、,.!?")


def _match_phrase(text: str, wake_phrases: Iterable[str], exit_phrases: Iterable[str]) -> ListenResult:
    norm = _normalize(text)
    matched_wake = False
    body = text
    for wp in wake_phrases:
        nwp = _normalize(wp)
        if norm.startswith(nwp):
            matched_wake = True
            # trim matched prefix from original
            idx = 0
            count = 0
            for i, ch in enumerate(text):
                if ch in " ，。！？、,.!?" or ch.isspace():
                    continue
                count += 1
                if count >= len(nwp):
                    idx = i + 1
                    break
            body = text[idx:].strip(" ，。！？、,.!?")
            break
    is_exit = False
    for ep in exit_phrases:
        if _normalize(ep) in norm:
            is_exit = True
            break
    return ListenResult(text=body, is_exit=is_exit, matched_wake=matched_wake, raw=text)


_GLOBAL: VoiceListener | None = None


def get_listener(config: Config) -> VoiceListener:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = VoiceListener(config)
    return _GLOBAL
