"""Groq STT/chat only. Local synthesis and explicit quota boundary, no fallback."""

import asyncio
import json

import httpx

from . import token_usage
from .local_tts import LocalSpeech, SpokenReply
from .voice_providers import DEEPSEEK_ENDPOINT, ProviderError, provider_config, wav_input

TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class QuotaError(ProviderError):
    def __init__(self, message, *, stage="chat", provider="Groq"):
        super().__init__(message)
        self.stage, self.provider = stage, provider


class GroqProviders:
    def __init__(self, key, config, *, transport=None, speech=None, deepseek_key=None):
        self.key, self.config = key, provider_config(config)
        self.deepseek_key = deepseek_key
        self.speech = speech or LocalSpeech()
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(40, connect=10), trust_env=False, follow_redirects=False, transport=transport
        )
        self.quota, self.blocked = {}, False

    async def aclose(self):
        await self.http.aclose()

    async def _request(self, endpoint, stage, **kwargs):
        if endpoint not in (TRANSCRIBE_URL, CHAT_URL, DEEPSEEK_ENDPOINT):
            raise ProviderError("Dịch vụ không hợp lệ.")
        deepseek = endpoint == DEEPSEEK_ENDPOINT
        provider = "DeepSeek" if deepseek else "Groq"
        key = self.deepseek_key if deepseek else self.key
        if not key:
            raise ProviderError(f"Thiếu {provider} API key trong Cài đặt.")
        if self.blocked:
            raise QuotaError("Phiên đang bị giới hạn. Chờ rồi chọn Retry.", stage=stage, provider=provider)
        try:
            async with asyncio.timeout(50):
                async with self.http.stream("POST", endpoint, headers={"Authorization": "Bearer " + key}, **kwargs) as response:
                    snapshot = {}
                    for field in ("limit-requests", "remaining-requests", "limit-tokens", "remaining-tokens"):
                        raw = response.headers.get("x-ratelimit-" + field, "")
                        if raw.isascii() and raw.isdigit() and len(raw) < 16:
                            snapshot[field] = int(raw)
                    if not deepseek:
                        self.quota[stage] = snapshot
                    if response.status_code in (402, 429):
                        self.blocked = True
                        raise QuotaError(
                            f"{provider} báo hết hạn mức / bị giới hạn. "
                            + (
                                "Phần nghe cần Groq phục hồi; DeepSeek không thay được phần nghe."
                                if stage == "speech"
                                else "Có thể đổi dịch vụ trả lời hoặc chờ rồi Retry."
                            ),
                            stage=stage,
                            provider=provider,
                        )
                    if response.status_code >= 300:
                        raise ProviderError(f"{provider} HTTP {response.status_code}. Kiểm tra key, model hoặc kết nối.")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 64000:
                            raise ProviderError(f"{provider}: phản hồi vượt giới hạn.")
                    return json.loads(raw)
        except (httpx.HTTPError, TimeoutError, ValueError):
            raise ProviderError(f"{provider}: chưa nhận được phản hồi hợp lệ. Thử lại.") from None

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
        token_usage.begin()
        if not self.speech.available():
            raise ProviderError("Thiếu giọng offline. Cài lại Companion Lite trước khi gọi Groq.")
        deepseek = self.config["voice_provider"] == "deepseek_local"
        payload = {
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
        }
        if deepseek:
            payload.update(model=self.config["deepseek_model"], thinking={"type": "disabled"}, max_tokens=1024)
            payload.pop("reasoning_effort")
            payload.pop("max_completion_tokens")
        result = await self._request(DEEPSEEK_ENDPOINT if deepseek else CHAT_URL, "chat", json=payload)
        token_usage.record("deepseek" if deepseek else "groq", result.get("usage") if isinstance(result, dict) else None)
        try:
            choice = result["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError()
            content = choice["message"]["content"]
            if not isinstance(content, str) or len(content) > 8000:
                raise ValueError()
            return SpokenReply(json.loads(content)["segments"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderError("Lời đáp song ngữ chưa hợp lệ. Thử lại.") from None

    async def speak(self, text, voice, slower=False):
        return await self.speech.speak(text, slower=slower)
