"""Explicit rollback of profile metadata/key migration, without plaintext files."""

import argparse
import json
from pathlib import Path

from . import backup, profiles_store, secret_store


def restore_snapshot(path: Path):
    path = path.resolve()
    if not path.is_relative_to(profiles_store.DATA_DIR.resolve()) or not path.name.endswith(
        (".pre-secrets.dpapi", ".pre-import.dpapi")
    ):
        raise ValueError("Choose a migration snapshot in this app's data directory")
    decrypted = secret_store.unprotect(path.read_bytes())
    if path.name.endswith(".pre-import.dpapi"):
        backup.import_profile_backup_zip(decrypted)
    else:
        profiles_store.save_profiles(json.loads(decrypted)["profiles"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore encrypted profile migration snapshot; close the app first")
    parser.add_argument("snapshot", type=Path)
    restore_snapshot(parser.parse_args().snapshot)
