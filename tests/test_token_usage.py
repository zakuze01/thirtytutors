import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from thirtytutors import main, memory, token_usage
from thirtytutors.groq_provider import GroqProviders
from thirtytutors.hybrid_session import HybridSession
from thirtytutors.local_access import LAUNCH_TOKEN
from thirtytutors.voice_providers import HybridProviders, ProviderError

from .test_groq_voice import Speech, chat_response
from .test_hybrid_voice import Providers, Socket


def test_usage_stores_only_counts_not_provider_content_or_credentials():
    private = "synthetic-private-prompt-key-DO-NOT-STORE"
    result = token_usage.record(
        "deepseek",
        {
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "prompt_cache_hit_tokens": 80,
            "prompt_cache_miss_tokens": 20,
            "completion_tokens_details": {"reasoning_tokens": 5, "private": private},
            "key": private,
            "prompt": private,
            "profile_id": private,
        },
    )
    assert result["input_tokens"] == 100 and result["cached_input_tokens"] == 80
    assert result["reasoning_tokens"] == 5 and result["saved"] is True
    assert set(result) == {"at", "provider", "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "saved"}
    assert token_usage.overview()["providers"] == [
        {
            "provider": "deepseek",
            "calls": 1,
            "input_tokens": 100,
            "output_tokens": 30,
            "cached_input_tokens": 80,
            "cache_reported_calls": 1,
        }
    ]
    for file in memory.DATA_DIR.glob("memory.db*"):
        assert private.encode() not in file.read_bytes()


@pytest.mark.parametrize("value", [None, True, -1, 1.5, "50", 1_000_000_001])
def test_invalid_token_numbers_are_not_reported_as_zero(value):
    token_usage.begin()
    assert token_usage.record("groq", {"prompt_tokens": value, "completion_tokens": 5}) is None
    assert token_usage.latest() is None
    assert token_usage.overview()["providers"] == []


def test_cache_unknown_and_zero_remain_distinct_and_not_double_counted():
    a = token_usage.record("groq", {"prompt_tokens": 10, "completion_tokens": 2})
    b = token_usage.record("groq", {"prompt_tokens": 20, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 0}})
    assert a["cached_input_tokens"] is None and b["cached_input_tokens"] == 0
    total = token_usage.overview()["providers"][0]
    assert total["input_tokens"] == 30 and total["cache_reported_calls"] == 1
    bad = token_usage.record(
        "deepseek", {"prompt_tokens": 5, "completion_tokens": 2, "prompt_cache_hit_tokens": 4, "prompt_cache_miss_tokens": 3}
    )
    assert bad["cached_input_tokens"] is None
    assert (
        token_usage.record(
            "groq", {"prompt_tokens": 5, "completion_tokens": 2, "completion_tokens_details": {"reasoning_tokens": 4}}
        )["reasoning_tokens"]
        is None
    )


def test_usage_retention_is_bounded_and_clearable(monkeypatch):
    monkeypatch.setattr(token_usage, "MAX_RECORDS", 3)
    for incoming in (1, 2, 3, 4):
        token_usage.record("groq", {"prompt_tokens": incoming, "completion_tokens": 1})
    total = token_usage.overview()["providers"][0]
    assert total["calls"] == 3 and total["input_tokens"] == 9
    token_usage.clear()
    assert token_usage.overview()["providers"] == []


@pytest.mark.asyncio
async def test_concurrent_cancelled_turn_counters_do_not_cross_tasks():
    token_usage.begin()

    async def task(incoming):
        token_usage.begin()
        token_usage.record("groq", {"prompt_tokens": incoming, "completion_tokens": 1})
        await asyncio.sleep(0)
        return token_usage.latest()["input_tokens"]

    assert await asyncio.gather(task(11), task(22)) == [11, 22]
    assert token_usage.latest() is None


@pytest.mark.asyncio
async def test_groq_counts_truncated_paid_reply_without_retrying():
    requests = []

    def handler(request):
        requests.append(request)
        result = chat_response()
        result["choices"][0]["finish_reason"] = "length"
        result["usage"] = {"prompt_tokens": 200, "completion_tokens": 1024}
        return httpx.Response(200, json=result)

    provider = GroqProviders("synthetic-key", {}, speech=Speech(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ProviderError):
            await provider.reply("fixed system", [], "hello")
        assert len(requests) == 1
        assert token_usage.latest()["output_tokens"] == 1024
        assert token_usage.overview()["providers"][0]["calls"] == 1
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_deepseek_system_prefix_is_stable_and_usage_comes_from_response():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hi!"}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 3,
                    "prompt_cache_hit_tokens": 60,
                    "prompt_cache_miss_tokens": 40,
                },
            },
        )

    provider = HybridProviders("synthetic-google", "synthetic-deepseek", {}, transport=httpx.MockTransport(handler))
    try:
        await provider.reply("fixed system and confirmed card", [], "hello")
        await provider.reply("fixed system and confirmed card", [{"role": "user", "content": "hello"}], "next")
        assert len(requests) == 2
        assert requests[0]["messages"][0] == requests[1]["messages"][0]
        total = token_usage.overview()["providers"][0]
        assert total["input_tokens"] == 200 and total["cached_input_tokens"] == 120
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_token_stats_storage_failure_does_not_fail_or_repeat_chat(monkeypatch):
    import sqlite3

    def fail():
        raise sqlite3.OperationalError("synthetic storage failure")

    monkeypatch.setattr(memory, "_transaction", fail)
    result = token_usage.record("groq", {"prompt_tokens": 12, "completion_tokens": 4})
    assert result["saved"] is False and result["input_tokens"] == 12


@pytest.mark.asyncio
async def test_pipeline_emits_counts_even_if_tts_fails_without_persisting_speech(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"])
    provider = Providers()

    async def reply(*args):
        token_usage.record("deepseek", {"prompt_tokens": 42, "completion_tokens": 5})
        return "Short reply"

    async def speak(*args):
        raise ProviderError("Synthetic TTS failure")

    provider.reply, provider.speak = reply, speak
    session = HybridSession(Socket(), p, c, provider)
    await session.pipeline(0, request="hello")
    events = [m for m in session.socket.sent if m["type"] == "token_usage"]
    assert len(events) == 1 and events[0]["usage"]["input_tokens"] == 42
    assert memory.get_turns(c["id"]) == []
    assert session.socket.sent[-1]["type"] == "turn_complete"
    await session.close()


def test_usage_api_requires_local_auth_and_clears_only_counters(make_profile):
    from thirtytutors import personal_memory

    p = make_profile()
    personal_memory.save(p["id"], "identity", "Synthetic personal card")
    token_usage.record("groq", {"prompt_tokens": 12, "completion_tokens": 4})
    unauthorized = TestClient(main.app, base_url="http://127.0.0.1")
    assert unauthorized.get("/api/token-usage").status_code in (401, 403)
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    assert client.get("/api/token-usage").json()["providers"][0]["calls"] == 1
    assert client.delete("/api/token-usage").status_code == 200
    assert client.get("/api/token-usage").json()["providers"] == []
    assert "Synthetic personal card" in personal_memory.context(p["id"])
