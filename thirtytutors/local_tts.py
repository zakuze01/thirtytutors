"""Offline CLI synthesis: bounded stdin/stdout, no shell or audio files."""

import asyncio
import io
import os
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np

from .voice_providers import MAX_AUDIO_BYTES, ProviderError


class SpokenReply(str):
    def __new__(cls, segments):
        if not isinstance(segments, list) or not 1 <= len(segments) <= 24:
            raise ValueError("Invalid speech segments")
        cleaned = []
        for segment in segments:
            if not isinstance(segment, dict) or segment.get("lang") not in ("vi", "en"):
                raise ValueError("Invalid speech language")
            text = segment.get("text")
            if not isinstance(text, str) or not text.strip() or "\x00" in text:
                raise ValueError("Invalid speech text")
            cleaned.append({"lang": segment["lang"], "text": text.strip()})
        text = " ".join(s["text"] for s in cleaned)
        if len(text) > 3000:
            raise ValueError("Speech too long")
        result = super().__new__(cls, text)
        result.segments = cleaned
        return result


class LocalSpeech:
    def __init__(self, directory=None):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1] / "build"))
        self.directory = Path(directory) if directory else base / "offline-tts"

    def available(self):
        return (self.directory / "espeak-ng.exe").is_file() and (self.directory / "espeak-ng-data").is_dir()

    def _render(self, reply, slower, cancelled=None):
        if not self.available():
            raise ProviderError("Thiếu bộ đọc offline Việt–Anh. Cài lại bản Companion Lite có giọng offline.")
        if not isinstance(reply, SpokenReply):
            raise ProviderError("Lời đáp thiếu thông tin giọng Việt–Anh.")
        output = bytearray()
        deadline = time.monotonic() + 35
        env = {**os.environ, "PATH": str(self.directory.parent) + os.pathsep + os.environ.get("PATH", "")}
        for segment in reply.segments:
            if (cancelled and cancelled.is_set()) or time.monotonic() >= deadline:
                raise ProviderError("Đã dừng tạo giọng offline.")
            # No SSML, file input or shell interpretation. Text only on stdin.
            try:
                result = subprocess.run(
                    [
                        str(self.directory / "espeak-ng.exe"),
                        "--path=" + str(self.directory),
                        "--stdout",
                        "-b",
                        "1",
                        "-v",
                        "vi" if segment["lang"] == "vi" else "en-us",
                        "-s",
                        "135" if slower else "165",
                        "--stdin",
                    ],
                    input=segment["text"].encode("utf-8"),
                    capture_output=True,
                    timeout=12,
                    cwd=self.directory,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
                if result.returncode or not 44 < len(result.stdout) <= MAX_AUDIO_BYTES:
                    raise ValueError()
                if cancelled and cancelled.is_set():
                    raise ProviderError("Đã dừng tạo giọng offline.")
                with wave.open(io.BytesIO(result.stdout), "rb") as wav:
                    if (wav.getnchannels(), wav.getsampwidth(), wav.getcomptype()) != (1, 2, "NONE"):
                        raise ValueError()
                    rate = wav.getframerate()
                    if not 8000 <= rate <= 48000:
                        raise ValueError()
                    pcm = wav.readframes(MAX_AUDIO_BYTES // 2 + 1)
                values = np.frombuffer(pcm, dtype="<i2")
                if not len(values):
                    raise ValueError()
                positions = np.arange(round(len(values) * 24000 / rate)) * rate / 24000
                output.extend(np.interp(positions, np.arange(len(values)), values).astype("<i2").tobytes())
                if len(output) > MAX_AUDIO_BYTES:
                    raise ValueError()
            except (OSError, subprocess.SubprocessError, ValueError, wave.Error, EOFError):
                raise ProviderError("Không tạo được giọng offline. Lời đáp vẫn có trong transcript.") from None
        return bytes(output)

    async def speak(self, reply, slower=False):
        cancelled = threading.Event()
        try:
            return await asyncio.to_thread(self._render, reply, slower, cancelled)
        finally:
            cancelled.set()
