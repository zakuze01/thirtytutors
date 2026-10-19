"""Portable local backups: no credentials, voice enrollment or raw audio."""

import io
import json
import re
import zipfile
from datetime import UTC, datetime

from . import memory, profiles_store, secret_store
from .constants import DATA_DIR
from .profiles_store import delete_profile, get_profile_by_id, upsert_profile
from .secret_store import SECRET_FIELDS, public_profile

AUTO_BACKUP_DIR = DATA_DIR / "backups" / "auto"


def build_profile_backup_zip(profile_id):
    profile = get_profile_by_id(profile_id)
    if profile is None:
        raise ValueError("Profile not found")
    manifest = {
        "format_version": 2,
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": {**public_profile(profile), **memory.get_profile_state(profile_id)},
        "conversations": memory.export_profile_conversations(profile_id),
        "memories": memory.list_memories(profile_id),
    }
    serialized = json.dumps(manifest, indent=2)
    for field in SECRET_FIELDS:
        if profile.get(field):
            serialized = serialized.replace(profile[field], "[redacted]")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", serialized)
    return buf.getvalue()


def _read_manifest(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(e.file_size for e in entries) > 64 * 1024 * 1024:
            raise ValueError("Backup exceeds safety limits")
        for entry in archive.namelist():
            if entry.startswith(("/", "\\")) or ":" in entry or ".." in entry.replace("\\", "/").split("/"):
                raise ValueError("Unsafe backup path")
        manifest = json.loads(archive.read("manifest.json"))
    if manifest.get("format_version") not in (1, 2):
        raise ValueError("Unsupported backup format")
    profile = manifest["profile"]
    pid = profile["id"]
    if not isinstance(pid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", pid):
        raise ValueError("Invalid profile namespace")
    conversations = manifest.get("conversations", [])
    if len({c["id"] for c in conversations}) != len(conversations):
        raise ValueError("Duplicate conversation ids")
    for conv in conversations:
        existing = memory.get_conversation(conv["id"])
        if existing and existing["profile_id"] != pid:
            raise ValueError("Conversation belongs to another profile")
        for key in ("id", "name", "config", "created_at", "updated_at"):
            if key not in conv:
                raise ValueError("Incomplete conversation")
        if not isinstance(conv["config"], dict):
            raise ValueError("Invalid conversation config")
    for item in manifest.get("memories", []):
        if (
            item.get("domain") not in ("conversation", "learning")
            or not isinstance(item.get("text"), str)
            or not item["text"].strip()
            or len(item["text"]) > 2000
        ):
            raise ValueError("Invalid memory")
    return manifest


def import_profile_backup_zip(data):
    manifest = _read_manifest(data)  # validate before changing profile/data
    profile = dict(manifest["profile"])
    pid = profile["id"]
    old_profile = get_profile_by_id(pid)
    old_state = memory.get_profile_state(pid)
    old_conversations = memory.export_profile_conversations(pid)
    old_memories = memory.list_memories(pid)
    if old_profile:
        snapshot = {
            "format_version": 2,
            "profile": {**old_profile, **old_state},
            "conversations": old_conversations,
            "memories": old_memories,
        }
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(snapshot))
        recovery = profiles_store.DATA_DIR / "recovery"
        recovery.mkdir(parents=True, exist_ok=True)
        filename = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f") + ".pre-import.dpapi"
        (recovery / filename).write_bytes(secret_store.protect(buf.getvalue()))
    for field in SECRET_FIELDS:
        profile[field] = profile.get(field) or (old_profile or {}).get(field)
    profile.pop("has_api_key", None)
    state = {
        key: profile.pop(key, None)
        for key in ("total_seconds_studied", "last_active_date", "current_streak", "seen_milestones", "last_auto_backup_at")
    }
    try:
        upsert_profile(profile)  # legacy plaintext keys go only to DPAPI
        memory.set_profile_state(pid, state)
        for item in manifest.get("memories", []):
            memory.save_memory(pid, item["domain"], item["text"], item["id"])
        memory.import_profile_conversations(pid, manifest.get("conversations", []))
    except Exception:
        # Multi-store rollback: in-memory snapshot has no persisted plaintext key.
        memory.erase_profile_memory(pid)
        for item in old_memories:
            memory.save_memory(pid, item["domain"], item["text"], item["id"])
        memory.import_profile_conversations(pid, old_conversations)
        if old_profile is not None:
            upsert_profile(old_profile)
            memory.set_profile_state(pid, old_state)
        else:
            delete_profile(pid)
            memory.delete_profile_state(pid)
        raise ValueError("Backup restore failed; previous local data restored") from None
    return pid


def _safe_filename_part(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " -_" else "_" for c in (name or "")).strip()
    return cleaned or "profile"


def maybe_run_auto_backup(profile_id: str) -> bool:
    """Checked once per app session (see routes_api.py's dedicated
    check-auto-backup endpoint, called once from init.js when the learning
    page establishes its profile) - if this profile has auto-backup turned
    on and its configured interval has elapsed since last_auto_backup_at,
    runs the exact same export build_profile_backup_zip does for the
    manual button, writes it under AUTO_BACKUP_DIR, and stamps
    last_auto_backup_at. Returns whether a backup actually ran, purely
    informational (the frontend doesn't currently act on it).

    The app only runs while its window is open, so this can't be a true
    OS-level schedule (Task Scheduler/cron/launchd) without real added
    complexity - a backup can end up up to one full extra interval late if
    the app isn't opened exactly on schedule. Acceptable for a personal
    local backup; the Settings UI states this plainly rather than
    overselling it as a precise schedule.
    """
    profile = get_profile_by_id(profile_id)
    if profile is None or not profile.get("auto_backup_enabled"):
        return False

    interval_days = profile.get("auto_backup_interval_days") or 7
    last_raw = memory.get_profile_state(profile_id).get("last_auto_backup_at")
    if last_raw:
        try:
            last = datetime.fromisoformat(last_raw)
            if (datetime.now(UTC) - last).days < interval_days:
                return False
        except ValueError:
            pass  # malformed stored timestamp (shouldn't happen) - treat as due rather than getting stuck never backing up

    AUTO_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    dest_path = AUTO_BACKUP_DIR / f"ThirtyTutors-{_safe_filename_part(profile.get('name'))}-{stamp}.zip"
    dest_path.write_bytes(build_profile_backup_zip(profile_id))

    memory.set_last_auto_backup_at(profile_id, datetime.now(UTC).isoformat())
    return True
