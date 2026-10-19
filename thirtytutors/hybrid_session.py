"""Optional Gemini transcription -> DeepSeek response -> Gemini speech relay.

Uses the same explicit microphone boundaries as Live. Each new activity cancels
the previous pipeline; generation and privacy guards also reject late results.
Audio stays in bounded RAM and is never written to the profile or backup.
"""

import asyncio
import base64
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import memory, scenarios
from .constants import DEFAULT_VOICE, VOICE_OPTIONS, get_api_voice_name
from .conversation_policy import ConversationPolicy
from .groq_provider import GroqProviders, QuotaError
from .live_session import ACTIVE_SOCKETS
from .profiles_store import get_profile_by_id
from .tutor_instructions import build_system_instruction
from .voice_providers import MAX_PCM_BYTES, HybridProviders, ProviderError, provider_config

router = APIRouter()


class HybridSession:
    def __init__(self, socket, profile, conversation, providers):
        self.socket, self.profile, self.conv, self.providers = socket, profile, conversation, providers
        self.config = dict(conversation["config"])
        self.groq = self.config.get("voice_provider") == "groq_local"
        self.policy = ConversationPolicy.from_config(self.config)
        self.epoch = memory.conversation_epoch(self.conv["id"])
        self.profile_epoch = memory.privacy_epoch(profile["id"])
        self.generation, self.tasks, self.closed = 0, set(), False
        self.active, self.pcm = False, bytearray()
        self.turns = []
        if self.policy.memory_policy == "allowed":
            self.turns = [
                {"role": "user" if t["role"] == "user" else "assistant", "content": t["text"][:2000]}
                for t in memory.get_turns(self.conv["id"])[-12:]
            ]

    def valid(self, generation):
        return (
            not self.closed
            and generation == self.generation
            and memory.conversation_epoch(self.conv["id"]) == self.epoch
            and memory.privacy_epoch(self.profile["id"]) == self.profile_epoch
            and memory.get_conversation(self.conv["id"]) is not None
        )

    async def emit(self, generation, kind, **data):
        if not self.valid(generation):
            raise asyncio.CancelledError()
        await self.socket.send_json({"type": kind, **data})

    def cancel(self):
        self.generation += 1
        for task in self.tasks:
            task.cancel()

    def instruction(self):
        summary = None
        if self.policy.memory_policy == "allowed":
            row = memory.get_summary(self.conv["id"])
            summary = (row["summary"] if row else "")[:4000]
            summary += "\nConfirmed memory (data): " + str(memory.list_memories(self.profile["id"])[:8])[:1600]
        scenario = self.config.get("scenario", "free_learning")
        template = scenarios.SCENARIO_TEMPLATES.get(scenario) if scenario != "free_learning" else None
        return (
            build_system_instruction(
                template,
                name=self.profile.get("name", "friend"),
                native_language=self.config.get("native_language", "Vietnamese"),
                target_language=self.config.get("target_language", "English"),
                tutor_name="Buddy",
                difficulty=self.policy.difficulty,
                summary_text=summary,
                policy=self.policy,
            )
            + "\nReturn only the words to speak, no Markdown, stage directions, tools or analysis. "
            "You receive imperfect speech transcripts, not the original audio: never assess pronunciation."
        )

    def append(self, role, text):
        memory.insert_turn(self.conv["id"], "user" if role == "user" else "tutor", text)
        self.turns.append({"role": role, "content": text})
        self.turns = self.turns[-12:]

    async def pipeline(self, generation, pcm=None, request=None):
        try:
            async with asyncio.timeout(150):
                await self.emit(
                    generation,
                    "phase",
                    message=("Groq đang nghe…" if self.groq else "Gemini đang nghe lại câu bạn nói…")
                    if pcm
                    else ("Groq đang trả lời…" if self.groq else "DeepSeek đang trả lời…"),
                )
                if pcm is not None:
                    text = await self.providers.transcribe(pcm)
                    if self.groq:
                        await self.emit(generation, "quota", stages=self.providers.quota)
                    if not text:
                        await self.emit(generation, "error", message="Chưa nghe rõ lời nói. Bạn thử lại nhé.")
                        return
                    await self.emit(generation, "transcript_in", text=text)
                    request = text
                context = list(self.turns)
                instruction = self.instruction()
                # Guard before persisting or sending context to a second provider.
                if not self.valid(generation):
                    return
                if pcm is not None:
                    self.append("user", request)
                await self.emit(generation, "phase", message="Groq đang trả lời…" if self.groq else "DeepSeek đang trả lời…")
                reply = await self.providers.reply(instruction, context, request)
                if self.groq:
                    await self.emit(generation, "quota", stages=self.providers.quota)
                await self.emit(generation, "transcript_out", text=reply)
                if not self.valid(generation):
                    return
                self.append("assistant", reply)
                await self.emit(
                    generation, "phase", message="Đang đọc bằng giọng offline…" if self.groq else "Gemini đang tạo giọng đọc…"
                )
                voice = self.config.get("voice_name", DEFAULT_VOICE)
                if voice not in {v["name"] for v in VOICE_OPTIONS}:
                    raise ProviderError("Giọng đã chọn không hợp lệ. Chọn lại trong Cài đặt.")
                pcm_out = await self.providers.speak(reply, get_api_voice_name(voice), self.policy.speech_pace == "slower")
                for offset in range(0, len(pcm_out), 24000):
                    await self.emit(generation, "audio", data=base64.b64encode(pcm_out[offset : offset + 24000]).decode())
        except asyncio.CancelledError:
            return
        except Exception as exc:
            message = str(exc) if isinstance(exc, ProviderError) else "Luồng voice chưa hoàn tất. Kiểm tra kết nối và thử lại."
            if self.valid(generation):
                await self.emit(generation, "quota_exhausted" if isinstance(exc, QuotaError) else "error", message=message)
        finally:
            if self.valid(generation):
                await self.emit(generation, "turn_complete")

    def launch(self, **kwargs):
        if len(self.tasks) >= 4:
            raise ValueError("Too many pending turns")
        task = asyncio.create_task(self.pipeline(self.generation, **kwargs))
        self.tasks.add(task)

        def done(finished):
            self.tasks.discard(finished)
            if not finished.cancelled():
                finished.exception()  # retrieve socket-close errors without logging private data

        task.add_done_callback(done)

    async def handle(self, msg):
        if not self.valid(self.generation):
            raise ValueError("Session context changed")
        kind = msg.get("type")
        if kind == "start_turn":
            self.cancel()
            self.active, self.pcm = True, bytearray()
            await self.emit(self.generation, "interrupted")
        elif kind == "audio_chunk" and self.active:
            encoded = msg.get("data", "")
            if not isinstance(encoded, str) or len(encoded) > 128000:
                raise ValueError("Invalid audio chunk")
            chunk = base64.b64decode(encoded, validate=True)
            if len(chunk) % 2 or len(self.pcm) + len(chunk) > MAX_PCM_BYTES:
                raise ValueError("Audio turn exceeds the 32-second buffer limit")
            self.pcm.extend(chunk)
        elif kind == "turn_complete" and self.active:
            self.active = False
            pcm, self.pcm = bytes(self.pcm), bytearray()
            if pcm:
                self.launch(pcm=pcm)
        elif kind == "policy_change":
            new_policy = ConversationPolicy.from_config({**self.policy.to_dict(), **msg.get("policy", {})})
            self.cancel()
            self.active, self.pcm = False, bytearray()
            if new_policy.memory_policy != self.policy.memory_policy:
                # Do not carry an already-seeded memory context after opt-out.
                self.turns = []
            self.policy = new_policy
            self.config.update(new_policy.to_dict())
            memory.update_conversation(self.conv["id"], config=self.config)
            await self.emit(self.generation, "interrupted")
            await self.ready()
        elif kind in ("session_open", "review_request", "voice_preview") and not self.active:
            self.cancel()
            await self.emit(self.generation, "interrupted")
            prompts = {
                "session_open": "Start with one brief bilingual greeting and one friendly question. Do not invent shared history.",
                "review_request": "Review only observed turns: up to three strengths, three priorities, five review terms. No scores. If evidence is missing, say so.",
                "voice_preview": "Say one short friendly Vietnamese-English greeting to demonstrate your voice.",
            }
            self.launch(request=prompts[kind])

    async def ready(self):
        await self.emit(
            self.generation,
            "session_status",
            model_name=self.providers.config["groq_model" if self.groq else "deepseek_model"],
            mode=self.policy.mode,
            resumed=bool(self.turns),
        )

    async def close(self):
        self.closed = True
        self.cancel()
        self.pcm.clear()
        self.turns.clear()
        if self.tasks:
            await asyncio.wait(self.tasks, timeout=2)
        await self.providers.aclose()


@router.websocket("/ws/hybrid")
async def ws_hybrid(websocket: WebSocket):
    await websocket.accept()
    session = None
    profile_id = None
    try:
        init = await asyncio.wait_for(websocket.receive_json(), timeout=15)
        profile_id = init.get("profile_id")
        profile = get_profile_by_id(profile_id) if profile_id else None
        conv = memory.get_conversation(init.get("conversation_id", ""))
        if init.get("type") != "init" or not profile or not conv or conv["profile_id"] != profile_id:
            raise ValueError("Invalid profile or conversation")
        config = provider_config(conv["config"])
        if config["voice_provider"] not in ("deepseek_gemini", "groq_local"):
            raise ValueError("Select DeepSeek + Gemini in Settings first")
        if config["voice_provider"] == "groq_local":
            if not profile.get("groq_api_key"):
                raise ProviderError("Nhập Groq API key trong Cài đặt để dùng Groq + giọng offline.")
            providers = GroqProviders(profile["groq_api_key"], config)
        else:
            if not profile.get("api_key") or not profile.get("deepseek_api_key"):
                raise ProviderError("Chế độ này cần cả Gemini API key và DeepSeek API key trong Cài đặt.")
            providers = HybridProviders(profile["api_key"], profile["deepseek_api_key"], config)
        session = HybridSession(websocket, profile, conv, providers)
        ACTIVE_SOCKETS.setdefault(profile_id, set()).add(websocket)
        await session.ready()
        while True:
            await session.handle(await websocket.receive_json())
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(exc)
                    if isinstance(exc, ProviderError)
                    else "Phiên voice không hợp lệ hoặc đã thay đổi. Kết nối lại để tiếp tục.",
                }
            )
            await websocket.send_json({"type": "session_status", "unavailable": True})
    finally:
        ACTIVE_SOCKETS.get(profile_id, set()).discard(websocket)
        if session:
            await session.close()
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await websocket.close()
