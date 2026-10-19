"""Groq STT/chat only. Local synthesis and explicit quota boundary, no fallback."""

import asyncio
import json

import httpx

from .local_tts import LocalSpeech, SpokenReply
from .voice_providers import ProviderError, provider_config, wav_input

TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class QuotaError(ProviderError):
    pass


class GroqProviders:
    def __init__(self, key, config, *, transport=None, speech=None):
        self.key, self.config = key, provider_config(config)
        self.speech = speech or LocalSpeech()
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(40, connect=10), trust_env=False, follow_redirects=False, transport=transport
        )
        self.quota, self.blocked = {}, False

    async def aclose(self):
        await self.http.aclose()

    async def _request(self, endpoint, stage, **kwargs):
        if self.blocked:
            raise QuotaError("Groq đang hết hạn mức. Chờ quota phục hồi hoặc bấm chuyển sang Gemini trả phí.")
        try:
            async with asyncio.timeout(50):
                async with self.http.stream(
                    "POST", endpoint, headers={"Authorization": "Bearer " + self.key}, **kwargs
                ) as response:
                    snapshot = {}
                    for field in ("limit-requests", "remaining-requests", "limit-tokens", "remaining-tokens"):
                        raw = response.headers.get("x-ratelimit-" + field, "")
                        if raw.isascii() and raw.isdigit() and len(raw) < 16:
                            snapshot[field] = int(raw)
                    self.quota[stage] = snapshot
                    if response.status_code in (402, 429):
                        self.blocked = True
                        raise QuotaError(
                            "Groq báo hết hạn mức / bị giới hạn. Chờ rồi thử lại hoặc bấm chuyển sang Gemini trả phí."
                        )
                    if response.status_code >= 300:
                        raise ProviderError(f"Groq HTTP {response.status_code}. Kiểm tra key, model hoặc kết nối.")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 64000:
                            raise ProviderError("Groq: phản hồi vượt giới hạn.")
                    return json.loads(raw)
        except (httpx.HTTPError, TimeoutError, ValueError):
            raise ProviderError("Groq: chưa nhận được phản hồi hợp lệ. Thử lại.") from None

    async def transcribe(self, pcm):
        if not self.speech.available():
            raise ProviderError("Thiếu giọng offline. Cài lại Companion Lite trước khi gửi âm thanh đến Groq.")
        result = await self._request(
            TRANSCRIBE_URL,
            "speech",
            files={"file": ("speech.wav", wav_input(pcm), "audio/wav")},
            data={"model": self.config["groq_transcription_model"], "response_format": "json", "temperature": "0"},
        )
        text = result.get("text")
        if not isinstance(text, str) or len(text) > 6000:
            raise ProviderError("Groq: transcript không hợp lệ. Bạn thử nói lại nhé.")
        return text.strip()

    async def reply(self, instruction, turns, request):
        if not self.speech.available():
            raise ProviderError("Thiếu giọng offline. Cài lại Companion Lite trước khi gọi Groq.")
        result = await self._request(
            CHAT_URL,
            "chat",
            json={
                "model": self.config["groq_model"],
                "messages": [
                    {
                        "role": "system",
                        "content": instruction + '\nOutput a JSON object only: {"segments":[{"lang":"vi" or "en",'
                        '"text":"words to speak"}]}. Split Vietnamese/English phrases for offline voices; '
                        "keep the original concise, natural bilingual reply. No other fields or commentary.",
                    }
                ]
                + [{"role": t["role"], "content": t["content"][:2000]} for t in turns[-12:]]
                + [{"role": "user", "content": request[:6000]}],
                "response_format": {"type": "json_object"},
                "reasoning_effort": "low",
                "max_completion_tokens": 1024,
                "stream": False,
            },
        )
        try:
            choice = result["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError()
            content = choice["message"]["content"]
            if not isinstance(content, str) or len(content) > 8000:
                raise ValueError()
            return SpokenReply(json.loads(content)["segments"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Groq: lời đáp song ngữ chưa hợp lệ. Thử lại.") from None

    async def speak(self, text, voice, slower=False):
        return await self.speech.speak(text, slower=slower)
