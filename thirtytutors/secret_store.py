"""Current-Windows-user DPAPI vault; fail closed on unsupported systems.

No raw keys in JSON/SQLite/portable backups. Encrypted files are user/machine-bound.
"""

import hashlib
import os
import sys
from pathlib import Path

SECRET_FIELDS = ("api_key", "langfuse_public_key", "langfuse_secret_key")


def protect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Secure key storage requires Windows DPAPI.")
    import win32crypt

    return win32crypt.CryptProtectData(data, "Companion Lite", None, None, None, 1)


def unprotect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Secure key storage requires Windows DPAPI.")
    import win32crypt

    return win32crypt.CryptUnprotectData(data, None, None, None, 1)[1]


def _path(directory: Path, profile_id: str, field: str) -> Path:
    if field not in SECRET_FIELDS:
        raise ValueError("Unsupported secret field")
    name = hashlib.sha256(f"{profile_id}:{field}".encode()).hexdigest()
    return directory / "secrets" / (name + ".dpapi")


def put(directory: Path, profile_id: str, field: str, value: str | None):
    path = _path(directory, profile_id, field)
    if not value:
        path.unlink(missing_ok=True)
        return
    encrypted = protect(value.encode("utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(encrypted)
    os.replace(tmp, path)


def get(directory: Path, profile_id: str, field: str) -> str | None:
    path = _path(directory, profile_id, field)
    if not path.exists():
        return None
    try:
        return unprotect(path.read_bytes()).decode("utf-8")
    except Exception:
        # Never fall back to plaintext or include DPAPI/credential details in errors.
        raise RuntimeError("Cannot unlock this profile's Windows credentials. Re-enter its API key.") from None


def public_profile(profile: dict) -> dict:
    result = {k: v for k, v in profile.items() if k not in SECRET_FIELDS}
    result["api_key"] = None
    result["has_api_key"] = bool(profile.get("api_key"))
    return result
