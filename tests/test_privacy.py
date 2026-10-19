import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from thirtytutors import backup, live_session, main, memory, profiles_store, secret_store, summarization
from thirtytutors.local_access import LAUNCH_TOKEN

SENTINEL = "synthetic-test-credential-never-a-real-key"


def test_credentials_are_encrypted_and_excluded_from_exports(make_profile, make_conversation):
    p = make_profile(api_key=SENTINEL)
    conv = make_conversation(p["id"])
    memory.insert_turn(conv["id"], "user", "accidental paste " + SENTINEL)
    assert profiles_store.get_profile_by_id(p["id"])["api_key"] == SENTINEL
    for file in profiles_store.DATA_DIR.rglob("*"):
        if file.is_file() and file.suffix not in (".db", "-wal", "-shm"):
            assert SENTINEL.encode() not in file.read_bytes()
    raw = backup.build_profile_backup_zip(p["id"])
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert SENTINEL not in zf.read("manifest.json").decode()
        assert not any("secret" in name or name.endswith(".dpapi") for name in zf.namelist())
    client = TestClient(main.app, base_url="http://127.0.0.1", headers={"X-Companion-Token": LAUNCH_TOKEN})
    response = client.get(f"/api/profiles/{p['id']}")
    assert SENTINEL not in response.text
    assert response.json()["has_api_key"] is True
    imported = client.post("/api/profiles/import", files={"file": ("backup.zip", raw, "application/zip")})
    assert imported.status_code == 200
    assert SENTINEL not in imported.text


def test_legacy_plaintext_migration_has_encrypted_rollback():
    profiles_store.DATA_DIR.mkdir(exist_ok=True)
    original = json.dumps({"profiles": [{"id": "legacy", "name": "Test", "api_key": SENTINEL}]}).encode()
    profiles_store.PROFILES_FILE.write_bytes(original)
    p = profiles_store.load_profiles()[0]
    assert p["api_key"] == SENTINEL
    assert SENTINEL not in profiles_store.PROFILES_FILE.read_text()
    snapshot = profiles_store.PROFILES_FILE.with_suffix(".json.pre-secrets.dpapi")
    assert SENTINEL.encode() not in snapshot.read_bytes()
    assert secret_store.unprotect(snapshot.read_bytes()) == original
    assert SENTINEL not in profiles_store._backup_path().read_text()


def test_failed_migration_preserves_legacy_file(monkeypatch):
    original = json.dumps({"profiles": [{"id": "legacy", "api_key": SENTINEL}]}).encode()
    profiles_store.PROFILES_FILE.write_bytes(original)
    monkeypatch.setattr(secret_store, "protect", lambda data: (_ for _ in ()).throw(RuntimeError("vault unavailable")))
    with pytest.raises(RuntimeError):
        profiles_store.load_profiles()
    assert profiles_store.PROFILES_FILE.read_bytes() == original


def test_archive_traversal_rejected_before_profile_changes(make_profile):
    p = make_profile()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format_version": 1, "profile": p, "conversations": []}))
        zf.writestr("voice_enrollment/../../escape.txt", "untrusted")
    with pytest.raises(ValueError, match="Unsafe"):
        backup.import_profile_backup_zip(buf.getvalue())
    assert len(profiles_store.load_profiles()) == 1


def test_import_cannot_overwrite_another_profiles_conversation(make_profile, make_conversation):
    a, b = make_profile(), make_profile()
    conv = make_conversation(a["id"])
    data = memory.export_profile_conversations(a["id"])
    with pytest.raises(ValueError, match="another profile"):
        memory.import_profile_conversations(b["id"], data)
    assert memory.get_conversation(conv["id"])["profile_id"] == a["id"]


def test_full_forget_removes_transcript_summaries_learning_and_handles(make_profile, make_conversation):
    p = make_profile()
    conv = make_conversation(p["id"])
    memory.insert_turn(conv["id"], "user", "Test fact")
    memory.upsert_summary(conv["id"], "Test fact", 1)
    memory.upsert_vocab_mistake(conv["id"], "catch up", "test")
    memory.set_resumption(conv["id"], "old-handle", conv["config"])
    memory.save_memory(p["id"], "conversation", "Test fact")
    before = memory.privacy_epoch(p["id"])
    memory.erase_profile_memory(p["id"])
    assert not memory.list_conversations(p["id"])
    assert not memory.get_turns(conv["id"])
    assert memory.get_summary(conv["id"]) is None
    assert not memory.get_vocab_mistakes(conv["id"])
    assert not memory.list_memories(p["id"])
    assert memory.privacy_epoch(p["id"]) > before


def test_late_summary_cannot_resurrect_forgotten_data(make_profile, make_conversation, monkeypatch):
    p = make_profile(api_key=SENTINEL)
    conv = make_conversation(p["id"])
    memory.insert_turn(conv["id"], "user", "Test observation")

    def generate(**kwargs):
        memory.erase_profile_memory(p["id"])
        return SimpleNamespace(text=json.dumps({"summary": "Test observation", "vocab": [], "lesson_note": ""}))

    monkeypatch.setattr(
        summarization, "get_client_for_key", lambda key: SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    )
    summarization.summarize_conversation(conv["id"], "Test", SENTINEL)
    assert memory.get_summary(conv["id"]) is None


def test_localhost_requires_launcher_and_same_origin():
    client = TestClient(main.app, base_url="http://127.0.0.1:8000")
    assert client.get("/api/profiles").status_code == 403
    assert client.get("/", params={"launch": LAUNCH_TOKEN}).status_code == 200
    assert client.get("/api/profiles").status_code == 200
    assert client.get("/api/profiles", headers={"Origin": "https://attacker.invalid"}).status_code == 403
    assert client.get("/api/profiles", headers={"Host": "attacker.invalid"}).status_code == 403


def test_provider_errors_do_not_return_or_log_raw_credentials(capsys):
    error = live_session._connect_failure_payload(ValueError(SENTINEL), SENTINEL)
    assert SENTINEL not in json.dumps(error)
    live_session.print(SENTINEL)
    assert SENTINEL not in capsys.readouterr().out


def test_bad_restore_rolls_back_profile_and_conversations(make_profile, make_conversation):
    p = make_profile(name="Original", api_key=SENTINEL)
    conv = make_conversation(p["id"])
    memory.insert_turn(conv["id"], "user", "Original observation")
    manifest = {
        "format_version": 2,
        "profile": {**p, "name": "Untrusted overwrite"},
        "conversations": memory.export_profile_conversations(p["id"]),
    }
    manifest["conversations"][0]["turns"] = [{"role": "user", "text": "broken: missing ts"}]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(ValueError, match="previous local data restored"):
        backup.import_profile_backup_zip(buf.getvalue())
    assert profiles_store.get_profile_by_id(p["id"])["name"] == "Original"
    assert profiles_store.get_profile_by_id(p["id"])["api_key"] == SENTINEL
    assert memory.get_turns(conv["id"])[0]["text"] == "Original observation"
