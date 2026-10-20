import asyncio
import io
import json
import subprocess
import wave
import zipfile
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from thirtytutors import backup, main, memory, profiles_store, secret_store
from thirtytutors.groq_provider import CHAT_URL, GroqProviders, QuotaError
from thirtytutors.hybrid_session import HybridSession
from thirtytutors.local_access import LAUNCH_TOKEN
from thirtytutors.local_tts import LocalSpeech, SpokenReply
from thirtytutors.voice_providers import ProviderError, provider_config

KEY = "synthetic-groq-key-not-real"
DEEPSEEK_KEY = "synthetic-deepseek-key-not-real"
SEGMENTS = [{"lang": "vi", "text": "Chuẩn rồi!"}, {"lang": "en", "text": "Good job!"}]


class Speech:
    def __init__(self):
        self.calls = []

    def available(self):
        return True

    async def speak(self, reply, slower=False):
        self.calls.append((reply.segments, slower))
        return b"\x01\x00" * 240


def chat_response():
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"segments": SEGMENTS})}}]}


def test_groq_key_is_private_and_backup_redacts_transcript(make_profile, make_conversation):
    p = make_profile(groq_api_key=KEY)
    c = make_conversation(p["id"], voice_provider="groq_local")
    memory.insert_turn(c["id"], "user", KEY)
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    public = client.get(f"/api/profiles/{p['id']}").json()
    assert public["has_groq_api_key"] and public["groq_api_key"] is None
    assert KEY not in json.dumps(public) and KEY not in profiles_store.PROFILES_FILE.read_text()
    raw = backup.build_profile_backup_zip(p["id"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert all(KEY.encode() not in archive.read(n) for n in archive.namelist())
    backup.import_profile_backup_zip(raw)
    assert profiles_store.get_profile_by_id(p["id"])["groq_api_key"] == KEY
    vault = secret_store._path(profiles_store.DATA_DIR, p["id"], "groq_api_key")
    assert KEY.encode() not in vault.read_bytes()
    client.delete(f"/api/profiles/{p['id']}")
    assert not vault.exists()


def test_groq_profile_create_and_config_validation():
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    p = client.post("/api/profiles", json={"name": "QA", "groq_api_key": KEY}).json()
    assert p["has_groq_api_key"] and KEY not in json.dumps(p)
    assert provider_config({"voice_provider": "groq_local"})["groq_model"] == "openai/gpt-oss-20b"
    assert provider_config({"voice_provider": "deepseek_local"})["deepseek_model"] == "deepseek-flash"
    for config in [{"groq_model": "http://arbitrary"}, {"groq_transcription_model": "unknown"}]:
        with pytest.raises(ValueError):
            provider_config(config)


@pytest.mark.asyncio
async def test_groq_uses_transcription_not_translation_and_local_speech():
    requests, speech = [], Speech()

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("transcriptions"):
            return httpx.Response(200, json={"text": "Con thích a cat"}, headers={"x-ratelimit-remaining-requests": "19"})
        return httpx.Response(200, json=chat_response())

    provider = GroqProviders(KEY, {}, transport=httpx.MockTransport(handler), speech=speech)
    assert await provider.transcribe(b"\x01\x00" * 160) == "Con thích a cat"
    reply = await provider.reply("short friend", [], "con thích a cat")
    assert str(reply) == "Chuẩn rồi! Good job!"
    assert await provider.speak(reply, "ignored", True)
    assert speech.calls == [(SEGMENTS, True)]
    assert len(requests) == 2 and all(r.url.host == "api.groq.com" for r in requests)
    assert all(r.headers["authorization"] == "Bearer " + KEY for r in requests)
    assert b'filename="speech.wav"' in requests[0].content
    assert b'name="language"' not in requests[0].content  # mixed language auto-detection
    body = json.loads(requests[1].content)
    assert body["messages"][-1]["content"] == "con thích a cat"
    assert body["stream"] is False and body["reasoning_effort"] == "low"
    assert provider.quota["speech"]["remaining-requests"] == 19
    await provider.aclose()


@pytest.mark.parametrize("code", [402, 429])
@pytest.mark.asyncio
async def test_quota_stops_requests_without_retry_or_paid_provider(code):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(code, text=KEY, headers={"x-ratelimit-remaining-requests": "0"})

    provider = GroqProviders(KEY, {}, transport=httpx.MockTransport(handler), speech=Speech())
    for _ in range(2):
        with pytest.raises(QuotaError) as error:
            await provider.reply("short", [], "hello")
        assert KEY not in str(error.value)
    assert len(requests) == 1 and str(requests[0].url) == CHAT_URL
    await provider.aclose()


@pytest.mark.asyncio
async def test_deepseek_offline_uses_groq_only_for_speech_and_isolates_keys():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200, json={"text": "con thích a cat"} if request.url.path.endswith("transcriptions") else chat_response()
        )

    provider = GroqProviders(
        KEY,
        {"voice_provider": "deepseek_local"},
        deepseek_key=DEEPSEEK_KEY,
        transport=httpx.MockTransport(handler),
        speech=Speech(),
    )
    await provider.transcribe(b"\x01\x00" * 160)
    reply = await provider.reply("short", [], "con thích a cat")
    await provider.speak(reply, "ignored")
    assert [r.url.host for r in requests] == ["api.groq.com", "api.deepseek.com"]
    assert requests[0].headers["authorization"] == "Bearer " + KEY
    assert requests[1].headers["authorization"] == "Bearer " + DEEPSEEK_KEY
    body = json.loads(requests[1].content)
    assert body["model"] == "deepseek-flash" and body["thinking"] == {"type": "disabled"}
    assert body["response_format"] == {"type": "json_object"} and body["max_tokens"] == 1024
    assert "reasoning_effort" not in body and "max_completion_tokens" not in body
    assert provider.speech.calls == [(SEGMENTS, False)]
    await provider.aclose()


@pytest.mark.parametrize("stage", ["speech", "chat"])
@pytest.mark.asyncio
async def test_quota_event_identifies_the_exhausted_stage(stage):
    provider = GroqProviders(KEY, {}, speech=Speech(), transport=httpx.MockTransport(lambda r: httpx.Response(429, text=KEY)))
    with pytest.raises(QuotaError) as error:
        if stage == "speech":
            await provider.transcribe(b"\x01\x00" * 160)
        else:
            await provider.reply("short", [], "hello")
    assert error.value.stage == stage and error.value.provider == "Groq"
    assert KEY not in str(error.value)
    await provider.aclose()


@pytest.mark.asyncio
async def test_deepseek_missing_key_never_calls_a_provider():
    def forbidden(request):
        raise AssertionError("No outbound call without DeepSeek key")

    provider = GroqProviders(KEY, {"voice_provider": "deepseek_local"}, speech=Speech(), transport=httpx.MockTransport(forbidden))
    with pytest.raises(ProviderError, match="DeepSeek API key"):
        await provider.reply("short", [], "hello")
    await provider.aclose()


def test_deepseek_offline_websocket_needs_no_gemini_key(monkeypatch, make_profile, make_conversation):
    from thirtytutors import hybrid_session

    p = make_profile(api_key=None, groq_api_key=KEY, deepseek_api_key=DEEPSEEK_KEY)
    c = make_conversation(p["id"], voice_provider="deepseek_local")

    def factory(key, config, **kwargs):
        assert key == KEY and kwargs["deepseek_key"] == DEEPSEEK_KEY
        return GroqProviders(
            key,
            config,
            **kwargs,
            speech=Speech(),
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=chat_response())),
        )

    monkeypatch.setattr(hybrid_session, "GroqProviders", factory)
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    with client.websocket_connect("ws://127.0.0.1/ws/hybrid", headers={"X-Companion-Token": LAUNCH_TOKEN}) as ws:
        ws.send_json({"type": "init", "profile_id": p["id"], "conversation_id": c["id"]})
        assert ws.receive_json()["model_name"] == "deepseek-flash"
        ws.send_json({"type": "voice_preview"})
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "turn_complete":
                break
        assert any(m["type"] == "audio" for m in messages)
        assert not any(m["type"] == "error" for m in messages)


@pytest.mark.parametrize("content", ["not json", '{"segments":[]}', '{"segments":[{"lang":"es","text":"hello"}]}'])
@pytest.mark.asyncio
async def test_malformed_reply_does_not_reach_synthesizer(content):
    provider = GroqProviders(
        KEY,
        {},
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]})
        ),
        speech=Speech(),
    )
    with pytest.raises(ProviderError):
        await provider.reply("short", [], "hello")
    assert not provider.speech.calls
    await provider.aclose()


@pytest.mark.asyncio
async def test_missing_local_engine_blocks_audio_upload():
    speech = Speech()
    speech.available = lambda: False

    def forbidden(request):
        raise AssertionError("No upload without offline engine")

    provider = GroqProviders(KEY, {}, transport=httpx.MockTransport(forbidden), speech=speech)
    with pytest.raises(ProviderError, match="offline"):
        await provider.transcribe(b"\x01\x00" * 160)
    await provider.aclose()


@pytest.mark.asyncio
async def test_groq_pipeline_quota_event_preserves_text_and_stops_tts(make_profile, make_conversation):
    p = make_profile(groq_api_key=KEY)
    c = make_conversation(p["id"], voice_provider="groq_local")
    sent = []

    class Socket:
        async def send_json(self, value):
            sent.append(value)

    def handler(request):
        if request.url.path.endswith("transcriptions"):
            return httpx.Response(200, json={"text": "chào bạn"})
        return httpx.Response(429, text=KEY)

    speech = Speech()
    provider = GroqProviders(KEY, c["config"], transport=httpx.MockTransport(handler), speech=speech)
    session = HybridSession(Socket(), p, c, provider)
    await session.pipeline(0, pcm=b"\x01\x00" * 160)
    assert not memory.get_turns(c["id"])
    assert [t["content"] for t in session.turns] == ["chào bạn"]
    assert any(m["type"] == "quota_exhausted" for m in sent)
    assert not speech.calls and not any(m["type"] == "audio" for m in sent)
    assert KEY not in json.dumps(sent)
    await session.close()


def test_offline_cli_stdin_languages_and_resampling(monkeypatch, tmp_path):
    speech = LocalSpeech(tmp_path)
    monkeypatch.setattr(speech, "available", lambda: True)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x01\x00" * 2205)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=output.getvalue())

    monkeypatch.setattr(subprocess, "run", run)
    pcm = speech._render(SpokenReply(SEGMENTS), True)
    assert len(pcm) == 2 * 2400 * 2  # two 100ms segments at 24kHz
    assert [c[0][c[0].index("-v") + 1] for c in calls] == ["vi", "en-us"]
    assert calls[0][1]["input"] == SEGMENTS[0]["text"].encode()
    assert all("shell" not in c[1] and c[1]["timeout"] == 12 for c in calls)


@pytest.mark.asyncio
async def test_groq_success_persists_plain_text_and_emits_local_audio(make_profile, make_conversation):
    p = make_profile(groq_api_key=KEY)
    c = make_conversation(p["id"], voice_provider="groq_local")
    sent = []

    class Socket:
        async def send_json(self, value):
            sent.append(value)

    provider = GroqProviders(
        KEY,
        c["config"],
        speech=Speech(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=chat_response())),
    )
    session = HybridSession(Socket(), p, c, provider)
    await session.pipeline(0, request="Say hello")
    assert not memory.get_turns(c["id"])
    assert [t["content"] for t in session.turns] == ["Chuẩn rồi! Good job!"]
    assert any(m["type"] == "audio" for m in sent)
    assert not any(m["type"] == "error" for m in sent)
    await session.close()


def test_local_preview_uses_no_provider(monkeypatch):
    async def speak(self, reply, slower=False):
        assert isinstance(reply, SpokenReply) and {s["lang"] for s in reply.segments} == {"vi", "en"}
        return b"\x01\x00" * 160

    monkeypatch.setattr(LocalSpeech, "speak", speak)
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    assert client.post("/api/local-voice/preview").status_code == 200


@pytest.mark.parametrize("segments", [[], [{"lang": "en", "text": ""}], [{"lang": "en", "text": "x" * 3001}]])
def test_offline_text_bounds(segments):
    with pytest.raises(ValueError):
        SpokenReply(segments)


@pytest.mark.asyncio
async def test_cancelled_offline_speech_does_not_process_more_segments(monkeypatch):
    import threading

    speech, entered, release = LocalSpeech(), threading.Event(), threading.Event()
    cancelled_seen = []

    def render(reply, slower, cancelled):
        entered.set()
        release.wait(2)
        cancelled_seen.append(cancelled.is_set())
        return b""

    monkeypatch.setattr(speech, "_render", render)
    task = asyncio.create_task(speech.speak(SpokenReply(SEGMENTS)))
    await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    await asyncio.to_thread(lambda: release.wait(0.05))
    for _ in range(20):
        if cancelled_seen:
            break
        await asyncio.sleep(0.01)
    assert cancelled_seen == [True]
