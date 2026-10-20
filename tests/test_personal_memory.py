import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from thirtytutors import backup, live_session, main, memory, personal_memory, secret_store
from thirtytutors.hybrid_session import HybridSession
from thirtytutors.local_access import LAUNCH_TOKEN

from .test_hybrid_voice import Providers, Socket


def test_card_is_encrypted_bounded_and_isolated(make_profile):
    a, b = make_profile(), make_profile()
    fact = "Private synthetic family fact 387296"
    personal_memory.save(a["id"], "family", fact)
    assert personal_memory.entries(a["id"])[0]["text"] == fact
    assert personal_memory.entries(b["id"]) == []
    for path in memory.DATA_DIR.glob("memory.db*"):
        assert fact.encode() not in path.read_bytes()
    for category in personal_memory.CATEGORIES:
        personal_memory.save(a["id"], category, "x" * 400)
    assert len(personal_memory.entries(a["id"])) == 6
    with pytest.raises(ValueError):
        personal_memory.save(a["id"], "family", "x" * 401)
    with pytest.raises(ValueError):
        personal_memory.save(a["id"], "inferred_personality", "guess")


def test_save_forget_invalidate_session_without_destroying_archives(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"])
    memory.insert_turn(c["id"], "user", "archived text")
    memory.upsert_summary(c["id"], "archived summary", 1)
    session = HybridSession(Socket(), p, c, Providers())
    personal_memory.save(p["id"], "preferences", "Short and funny, please")
    assert not session.valid(0)
    assert memory.get_summary(c["id"])["summary"] == "archived summary"
    assert memory.get_turns(c["id"])[0]["text"] == "archived text"
    personal_memory.remove(p["id"], "preferences")
    assert personal_memory.entries(p["id"]) == []
    assert "Short and funny" not in personal_memory.context(p["id"])


def test_expired_needs_are_visible_but_excluded_from_context(make_profile, monkeypatch):
    p = make_profile()
    monkeypatch.setattr(personal_memory.time, "time", lambda: 1000)
    personal_memory.save(p["id"], "needs", "Temporary learning goal", 1001)
    assert "Temporary learning goal" in personal_memory.context(p["id"])
    monkeypatch.setattr(personal_memory.time, "time", lambda: 1001)
    assert "Temporary learning goal" not in personal_memory.context(p["id"])
    assert personal_memory.entries(p["id"])[0]["expired"] is True


def test_card_vault_failure_never_falls_back_to_plaintext(make_profile, monkeypatch):
    p = make_profile()
    personal_memory.save(p["id"], "identity", "Synthetic name")
    monkeypatch.setattr(secret_store, "unprotect", lambda _: (_ for _ in ()).throw(ValueError("private details")))
    with pytest.raises(RuntimeError, match="Windows") as exc:
        personal_memory.context(p["id"])
    assert "private details" not in str(exc.value)


def test_card_backup_roundtrip_and_old_backup_compatibility(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"])
    memory.insert_turn(c["id"], "user", "old archive")
    personal_memory.save(p["id"], "interests", "Dinosaur stories")
    raw = backup.build_profile_backup_zip(p["id"])
    personal_memory.remove(p["id"], "interests")
    backup.import_profile_backup_zip(raw)
    assert "Dinosaur stories" in personal_memory.context(p["id"])
    assert memory.get_turn_count(c["id"]) == 1
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    manifest.pop("personal_card")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
    backup.import_profile_backup_zip(out.getvalue())
    assert "Dinosaur stories" in personal_memory.context(p["id"])


def test_invalid_backup_card_rejected_before_mutation(make_profile):
    p = make_profile()
    personal_memory.save(p["id"], "identity", "Existing card")
    with zipfile.ZipFile(io.BytesIO(backup.build_profile_backup_zip(p["id"]))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    manifest["personal_card"] = [{"category": "identity", "text": "x" * 401}]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(ValueError):
        backup.import_profile_backup_zip(out.getvalue())
    assert "Existing card" in personal_memory.context(p["id"])


@pytest.mark.asyncio
async def test_hybrid_sends_card_and_only_bounded_ram_never_archive(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"], memory_policy="allowed")
    memory.save_memory(p["id"], "conversation", "LEGACY FACT")
    memory.insert_turn(c["id"], "user", "ARCHIVED TURN")
    memory.upsert_summary(c["id"], "ARCHIVED SUMMARY", 1)
    personal_memory.save(p["id"], "preferences", "Keep it short")
    s = HybridSession(Socket(), p, c, Providers())
    assert s.turns == []
    prompt = s.instruction()
    assert "Keep it short" in prompt
    assert "LEGACY FACT" not in prompt and "ARCHIVED" not in prompt
    for i in range(24):
        s.append("user" if i % 2 == 0 else "assistant", str(i) + "x" * 3000)
    assert len(s.turns) == 12
    assert max(len(t["content"]) for t in s.turns) == personal_memory.MAX_TURN_TEXT
    await s.pipeline(0, pcm=b"\x01\x00")
    assert len(s.providers.calls[1][1]) == 12
    assert memory.get_turn_count(c["id"]) == 1
    await s.close()
    assert s.turns == []
    assert s.card_context is None
    fresh = HybridSession(Socket(), p, c, Providers())
    assert fresh.turns == []
    await fresh.close()


@pytest.mark.asyncio
async def test_explicit_remember_is_only_a_reviewable_suggestion(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"])
    provider = Providers()
    provider.text = "Nhớ giúp tôi: tôi thích khủng long"
    s = HybridSession(Socket(), p, c, provider)
    await s.pipeline(0, pcm=b"\x01\x00")
    suggested = [m for m in s.socket.sent if m["type"] == "personal_memory_proposal"]
    assert suggested[0]["text"] == "tôi thích khủng long"
    assert personal_memory.entries(p["id"]) == []
    assert memory.get_turn_count(c["id"]) == 0
    assert personal_memory.proposal("tôi thích khủng long") is None
    await s.close()


def test_card_api_validation_forget_and_full_erasure(make_profile, monkeypatch):
    p = make_profile()
    closed = []

    async def close(pid):
        closed.append(pid)

    from thirtytutors import routes_api

    monkeypatch.setattr(routes_api, "close_profile_sessions", close)
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    path = f"/api/profiles/{p['id']}/personal-card"
    assert client.put(path + "/identity", json={"text": "Synthetic learner"}).status_code == 200
    assert client.get(path).json()["entries"][0]["text"] == "Synthetic learner"
    assert closed == [p["id"]]
    assert client.put(path + "/needs", json={"text": "goal", "expires_at": True}).status_code == 400
    assert client.put(path + "/identity", json=[]).status_code == 400
    assert client.put(path + "/unknown", json={"text": "no"}).status_code == 400
    assert client.delete(path + "/identity").status_code == 200
    assert client.get(path).json()["entries"] == []
    personal_memory.save(p["id"], "family", "Example relative")
    assert client.delete(f"/api/profiles/{p['id']}/memory").status_code == 200
    assert personal_memory.entries(p["id"]) == []
    assert client.get("/api/profiles/missing/personal-card").status_code == 404


def test_live_context_has_card_but_no_archived_resume_or_summary(make_profile, make_conversation):
    p = make_profile()
    c = make_conversation(p["id"])
    personal_memory.save(p["id"], "interests", "Building toy rockets")
    memory.insert_turn(c["id"], "user", "old private history")
    memory.upsert_summary(c["id"], "old private summary", 1)
    memory.set_resumption(c["id"], "old private handle", c["config"])
    _, handle, context, terms, vocab = live_session._refresh_conversation_memory_context(c, {})
    assert handle is None and not terms and not vocab
    assert "Building toy rockets" in context
    assert "old private" not in context
    assert memory.get_summary(c["id"])["summary"] == "old private summary"


def test_memory_off_does_not_even_unlock_card(make_profile, make_conversation, monkeypatch):
    p = make_profile()
    c = make_conversation(p["id"], memory_policy="off")
    personal_memory.save(p["id"], "family", "Private synthetic relative")
    monkeypatch.setattr(secret_store, "unprotect", lambda _: (_ for _ in ()).throw(AssertionError("Must not decrypt")))
    _, _, context, _, _ = live_session._refresh_conversation_memory_context(c, {})
    assert context is None
    s = HybridSession(Socket(), p, c, Providers())
    assert "Private synthetic relative" not in s.instruction()


@pytest.mark.asyncio
async def test_hybrid_expiry_drops_ram_that_might_quote_old_fact(make_profile, make_conversation, monkeypatch):
    p = make_profile()
    c = make_conversation(p["id"], memory_policy="allowed")
    clock = [1000]
    monkeypatch.setattr(personal_memory.time, "time", lambda: clock[0])
    personal_memory.save(p["id"], "needs", "Expiring goal", 1001)
    s = HybridSession(Socket(), p, c, Providers())
    assert "Expiring goal" in s.instruction()
    s.append("assistant", "Let us practice your Expiring goal")
    clock[0] = 1001
    await s.pipeline(0, pcm=b"\x01\x00")
    assert "Expiring goal" not in s.providers.calls[1][0]
    assert s.providers.calls[1][1] == []
    await s.close()


def test_failed_backup_import_restores_existing_card(make_profile, monkeypatch):
    p = make_profile()
    personal_memory.save(p["id"], "identity", "Original card")
    raw = backup.build_profile_backup_zip(p["id"])
    personal_memory.save(p["id"], "identity", "Newer card")
    original = personal_memory.replace
    calls = []

    def fail_once(pid, items):
        calls.append(pid)
        if len(calls) == 1:
            raise RuntimeError("Synthetic import failure")
        return original(pid, items)

    monkeypatch.setattr(personal_memory, "replace", fail_once)
    with pytest.raises(ValueError, match="previous local data restored"):
        backup.import_profile_backup_zip(raw)
    assert "Newer card" in personal_memory.context(p["id"])
