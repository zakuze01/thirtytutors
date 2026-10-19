import asyncio
import base64
import io
import json
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from thirtytutors import backup, hybrid_session, main, memory, profiles_store, secret_store
from thirtytutors.hybrid_session import HybridSession
from thirtytutors.local_access import LAUNCH_TOKEN
from thirtytutors.voice_providers import (
    DEEPSEEK_ENDPOINT,
    GOOGLE_ENDPOINT,
    MAX_PCM_BYTES,
    HybridProviders,
    ProviderError,
    provider_config,
    wav_input,
)

KEY = "synthetic-deepseek-credential-not-real"


def client():
    return TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})


def audio_result(pcm=b"\x01\x00" * 240, rate=24000):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(pcm)
    return {
        "steps": [{"type": "model_output", "content": [{"type": "audio", "data": base64.b64encode(output.getvalue()).decode()}]}]
    }


def test_deepseek_key_round_trip_and_backup(make_profile, make_conversation):
    p = make_profile(api_key="synthetic-gemini-credential", deepseek_api_key=KEY)
    c = make_conversation(p["id"])
    memory.insert_turn(c["id"], "user", KEY)
    public = client().get(f"/api/profiles/{p['id']}").json()
    assert public["has_deepseek_api_key"] and public["deepseek_api_key"] is None
    assert KEY not in json.dumps(public)
    assert profiles_store.get_profile_by_id(p["id"])["deepseek_api_key"] == KEY
    assert KEY not in profiles_store.PROFILES_FILE.read_text()
    vault = secret_store._path(profiles_store.DATA_DIR, p["id"], "deepseek_api_key")
    assert KEY.encode() not in vault.read_bytes()
    raw = backup.build_profile_backup_zip(p["id"])
    assert KEY.encode() not in raw
    # Inspect decompressed data as well: ZIP compression alone is not protection.
    import zipfile

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert all(KEY.encode() not in archive.read(name) for name in archive.namelist())
    backup.import_profile_backup_zip(raw)
    assert profiles_store.get_profile_by_id(p["id"])["deepseek_api_key"] == KEY
    assert client().delete(f"/api/profiles/{p['id']}").status_code == 200
    assert not vault.exists()


def test_deepseek_legacy_migration_encrypts_rollback():
    raw = json.dumps({"profiles": [{"id": "legacy", "deepseek_api_key": KEY}]}).encode()
    profiles_store.PROFILES_FILE.write_bytes(raw)
    assert profiles_store.load_profiles()[0]["deepseek_api_key"] == KEY
    assert KEY not in profiles_store.PROFILES_FILE.read_text()
    assert KEY not in profiles_store._backup_path().read_text()
    snapshot = profiles_store.PROFILES_FILE.with_suffix(".json.pre-secrets.dpapi")
    assert secret_store.unprotect(snapshot.read_bytes()) == raw


def test_provider_settings_validation_and_key_creation(make_profile):
    api = client()
    p = api.post("/api/profiles", json={"name": "Test", "deepseek_api_key": KEY}).json()
    assert p["has_deepseek_api_key"] and KEY not in json.dumps(p)
    path = f"/api/profiles/{p['id']}/conversations"
    conv = api.post(path, json={"voice_provider": "deepseek_gemini", "deepseek_model": "deepseek-v4-pro"}).json()
    assert conv["config"]["deepseek_model"] == "deepseek-v4-pro"
    assert (
        api.put(path + "/" + conv["id"], json={"voice_provider": "gemini_live"}).json()["config"]["voice_provider"]
        == "gemini_live"
    )
    for invalid in ("", None, "http://arbitrary-endpoint", ["deepseek_gemini"]):
        assert api.post(path, json={"voice_provider": invalid}).status_code == 400
        assert api.put(path + "/" + conv["id"], json={"voice_provider": invalid}).status_code == 400


@pytest.mark.parametrize(
    "config", [{"deepseek_model": "deepseek-chat"}, {"tts_model": "arbitrary"}, {"transcription_model": None}]
)
def test_invalid_models_fail_before_network(config):
    with pytest.raises(ValueError):
        provider_config(config)


@pytest.mark.asyncio
async def test_exact_provider_routing_headers_and_formats():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append((request, body))
        if request.url == DEEPSEEK_ENDPOINT:
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "Chuẩn rồi fen! Good job!"}, "finish_reason": "stop"}]}
            )
        if body["model"].endswith("tts"):
            return httpx.Response(200, json=audio_result())
        return httpx.Response(
            200, json={"steps": [{"type": "model_output", "content": [{"type": "text", "text": '{"text":"con thích a cat"}'}]}]}
        )

    providers = HybridProviders("gemini-test", KEY, {}, transport=httpx.MockTransport(handler))
    try:
        text = await providers.transcribe(b"\x02\x00" * 160)
        assert text == "con thích a cat"
        answer = await providers.reply("Bilingual friend", [], text)
        pcm = await providers.speak(answer, "Kore", True)
        assert pcm == b"\x01\x00" * 240
    finally:
        await providers.aclose()
    assert len(requests) == 3
    google, deepseek, tts = requests
    assert str(google[0].url) == str(tts[0].url) == GOOGLE_ENDPOINT
    assert google[0].headers["x-goog-api-key"] == "gemini-test"
    assert "authorization" not in google[0].headers
    assert deepseek[0].headers["authorization"] == "Bearer " + KEY
    assert "x-goog-api-key" not in deepseek[0].headers
    assert deepseek[1]["messages"][-1]["content"] == text
    assert deepseek[1]["thinking"] == {"type": "disabled"}
    assert deepseek[1]["max_tokens"] == 512
    assert google[1]["store"] is tts[1]["store"] is False
    assert tts[1]["input"][0]["content"][0]["text"] == answer
    assert providers.http.trust_env is False
    assert providers.http.follow_redirects is False
    with wave.open(io.BytesIO(base64.b64decode(google[1]["input"][1]["data"]))) as wav:
        assert wav.getframerate() == 16000 and wav.getnchannels() == 1


@pytest.mark.parametrize("status", [302, 400, 401, 403, 404, 402, 429, 500])
@pytest.mark.asyncio
async def test_errors_never_expose_raw_body_or_credentials(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=KEY, headers={"Location": "https://example.org/leak"})

    providers = HybridProviders("gemini-test", KEY, {}, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderError) as error:
            await providers.reply("policy", [], "hello")
        assert KEY not in str(error.value)
        assert str(status) in str(error.value)
        assert len(calls) == 1  # no redirect, retry or provider fallback
    finally:
        await providers.aclose()


@pytest.mark.asyncio
async def test_invalid_or_truncated_provider_outputs():
    for response in ({"choices": []}, {"choices": [{"message": {"content": "cut off"}, "finish_reason": "length"}]}):
        providers = HybridProviders("test", KEY, {}, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)))
        with pytest.raises(ProviderError):
            await providers.reply("policy", [], "hello")
        await providers.aclose()
    providers = HybridProviders(
        "test", KEY, {}, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=audio_result(rate=16000)))
    )
    with pytest.raises(ProviderError):
        await providers.speak("hello", "Kore")
    await providers.aclose()


@pytest.mark.parametrize("pcm", [b"", b"x", b"\0" * (MAX_PCM_BYTES + 2)], ids=["empty", "odd", "oversize"])
def test_input_audio_bounds(pcm):
    with pytest.raises(ValueError):
        wav_input(pcm)


class Socket:
    def __init__(self):
        self.sent = []

    async def send_json(self, value):
        self.sent.append(value)


class Providers:
    config = {"deepseek_model": "deepseek-flash"}

    def __init__(self):
        self.calls = []
        self.text = "con thích a cat"

    async def transcribe(self, pcm):
        self.calls.append("transcribe")
        return self.text

    async def reply(self, instruction, context, request):
        self.calls.append((instruction, context, request))
        return "Meow! A hungry cat!"

    async def speak(self, text, voice, slower):
        self.calls.append((text, voice, slower))
        return b"\x01\x00" * 25000

    async def aclose(self):
        pass


def session(make_profile, make_conversation, **config):
    p = make_profile()
    c = make_conversation(p["id"], native_language="Vietnamese", target_language="English", **config)
    return HybridSession(Socket(), p, c, Providers())


@pytest.mark.asyncio
async def test_voice_pipeline_persists_observed_turns_only(make_profile, make_conversation):
    s = session(make_profile, make_conversation)
    await s.handle({"type": "audio_chunk", "data": "invalid before start is discarded"})
    await s.handle({"type": "turn_complete"})
    assert not s.tasks
    await s.handle({"type": "start_turn"})
    await s.handle({"type": "audio_chunk", "data": base64.b64encode(b"\x01\x00" * 160).decode()})
    await s.handle({"type": "turn_complete"})
    await asyncio.gather(*s.tasks)
    assert [t["text"] for t in memory.get_turns(s.conv["id"])] == ["con thích a cat", "Meow! A hungry cat!"]
    assert len([m for m in s.socket.sent if m["type"] == "audio"]) == 3
    assert s.socket.sent[-1]["type"] == "turn_complete"
    assert not s.pcm
    await s.close()


@pytest.mark.parametrize("stage", ["transcribe", "reply", "speak"])
@pytest.mark.asyncio
async def test_barge_in_rejects_late_results_even_if_transport_ignores_cancel(make_profile, make_conversation, stage):
    s = session(make_profile, make_conversation)
    entered, release = asyncio.Event(), asyncio.Event()
    original = getattr(s.providers, stage)

    async def delayed(*args):
        entered.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            await release.wait()  # synthetic misbehaving transport
        return await original(*args)

    setattr(s.providers, stage, delayed)
    s.launch(pcm=b"\x01\x00" * 160)
    await asyncio.wait_for(entered.wait(), 2)
    old_tasks = list(s.tasks)
    await s.handle({"type": "start_turn"})
    boundary = len(s.socket.sent)
    release.set()
    await asyncio.gather(*old_tasks)
    assert len(s.socket.sent) == boundary
    assert not any(m["type"] == "audio" for m in s.socket.sent)
    if stage == "transcribe":
        assert not memory.get_turns(s.conv["id"])
    elif stage == "reply":
        assert len(memory.get_turns(s.conv["id"])) == 1
    await s.close()


@pytest.mark.parametrize("erase", ["conversation", "profile", "memory"])
@pytest.mark.asyncio
async def test_erasure_during_transcription_blocks_further_providers_and_writes(make_profile, make_conversation, erase):
    s = session(make_profile, make_conversation)

    async def transcribe(pcm):
        if erase == "conversation":
            memory.delete_conversation(s.conv["id"])
        elif erase == "profile":
            memory.erase_profile_memory(s.profile["id"])
        else:
            memory.invalidate_derived_memory(s.profile["id"])
        return "late transcript"

    s.providers.transcribe = transcribe
    await s.pipeline(s.generation, pcm=b"\x01\x00")
    assert not s.providers.calls
    assert not memory.get_turns(s.conv["id"])
    assert not any(m["type"] == "transcript_in" for m in s.socket.sent)
    await s.close()


@pytest.mark.asyncio
async def test_memory_off_and_policy_switch_do_not_seed_stored_history(make_profile, make_conversation):
    s = session(make_profile, make_conversation, memory_policy="off")
    memory.insert_turn(s.conv["id"], "user", "PRIVATE stored history")
    memory.upsert_summary(s.conv["id"], "PRIVATE summary", 1)
    fresh = HybridSession(Socket(), s.profile, memory.get_conversation(s.conv["id"]), Providers())
    assert fresh.turns == []
    assert "PRIVATE" not in fresh.instruction()
    await fresh.pipeline(fresh.generation, pcm=b"\x01\x00")
    request = fresh.providers.calls[1]
    assert request[1] == []
    assert "PRIVATE" not in request[0]
    await fresh.handle({"type": "policy_change", "policy": {"mode": "teacher", "memory_policy": "allowed"}})
    assert fresh.policy.mode == "teacher" and fresh.turns == []
    assert fresh.socket.sent[-1]["type"] == "session_status"
    await fresh.close()
    await s.close()


@pytest.mark.asyncio
async def test_silence_does_not_request_deepseek_or_tts(make_profile, make_conversation):
    s = session(make_profile, make_conversation)
    s.providers.text = ""
    await s.pipeline(s.generation, pcm=b"\x00\x00")
    assert s.providers.calls == ["transcribe"]
    assert not memory.get_turns(s.conv["id"])
    await s.close()


@pytest.mark.asyncio
async def test_tts_failure_retains_text_without_fabricating_audio(make_profile, make_conversation):
    s = session(make_profile, make_conversation)

    async def fail(*args):
        raise ProviderError("Gemini HTTP 429. Kiểm tra quota.")

    s.providers.speak = fail
    await s.pipeline(s.generation, pcm=b"\x01\x00")
    assert len(memory.get_turns(s.conv["id"])) == 2
    assert any(m["type"] == "transcript_out" for m in s.socket.sent)
    assert not any(m["type"] == "audio" for m in s.socket.sent)
    assert s.socket.sent[-2]["type"] == "error"
    assert s.socket.sent[-1]["type"] == "turn_complete"
    await s.close()


@pytest.mark.asyncio
async def test_close_cancels_pending_request_without_late_writes(make_profile, make_conversation):
    s = session(make_profile, make_conversation)
    entered, cancelled = asyncio.Event(), asyncio.Event()

    async def pending(pcm):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    s.providers.transcribe = pending
    s.launch(pcm=b"\x01\x00")
    await asyncio.wait_for(entered.wait(), 2)
    await s.close()
    assert cancelled.is_set() and s.closed and not s.pcm and not s.turns
    assert not memory.get_turns(s.conv["id"])


@pytest.mark.asyncio
async def test_invalid_audio_cannot_grow_session_buffer(make_profile, make_conversation):
    s = session(make_profile, make_conversation)
    await s.handle({"type": "start_turn"})
    for data in ("not base64", "x" * 128004, base64.b64encode(b"x").decode()):
        with pytest.raises(ValueError):
            await s.handle({"type": "audio_chunk", "data": data})
        assert not s.pcm
    s.pcm.extend(b"\0" * MAX_PCM_BYTES)
    with pytest.raises(ValueError):
        await s.handle({"type": "audio_chunk", "data": "AAA="})
    await s.close()


@pytest.mark.asyncio
async def test_response_size_and_non_json_are_bounded():
    for content in (b"x" * 64001, b"not-json"):
        providers = HybridProviders(
            "test", KEY, {}, transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content))
        )
        with pytest.raises(ProviderError):
            await providers.reply("policy", [], "hello")
        await providers.aclose()


def test_hybrid_socket_requires_both_keys_and_owns_conversation(make_profile, make_conversation):
    p = make_profile(api_key="fake-gemini")
    c = make_conversation(p["id"], voice_provider="deepseek_gemini")
    with client().websocket_connect("ws://127.0.0.1/ws/hybrid") as ws:
        ws.send_json({"type": "init", "profile_id": p["id"], "conversation_id": c["id"]})
        assert "cả Gemini" in ws.receive_json()["message"]
        assert ws.receive_json()["unavailable"]
    other = make_profile(api_key="fake", deepseek_api_key=KEY)
    with client().websocket_connect("ws://127.0.0.1/ws/hybrid") as ws:
        ws.send_json({"type": "init", "profile_id": other["id"], "conversation_id": c["id"]})
        assert ws.receive_json()["type"] == "error"
    with client().websocket_connect("ws://127.0.0.1/ws/session") as ws:
        ws.send_json({"type": "init", "profile_id": p["id"], "conversation_id": c["id"]})
        assert "DeepSeek" in ws.receive_json()["message"]


def test_socket_protocol_greeting_review_and_close(make_profile, make_conversation, monkeypatch):
    p = make_profile(api_key="fake", deepseek_api_key=KEY)
    c = make_conversation(p["id"], voice_provider="deepseek_gemini")
    providers = Providers()
    monkeypatch.setattr(hybrid_session, "HybridProviders", lambda *args: providers)
    with client().websocket_connect("ws://127.0.0.1/ws/hybrid") as ws:
        ws.send_json({"type": "init", "profile_id": p["id"], "conversation_id": c["id"]})
        assert ws.receive_json()["type"] == "session_status"
        for kind in ("session_open", "review_request", "voice_preview"):
            ws.send_json({"type": kind})
            events = []
            while not events or events[-1]["type"] != "turn_complete":
                events.append(ws.receive_json())
            assert any(e["type"] == "audio" for e in events)
            assert not any(e["type"] == "transcript_in" for e in events)
    assert not hybrid_session.ACTIVE_SOCKETS.get(p["id"])
    assert all(t["role"] == "tutor" for t in memory.get_turns(c["id"]))
