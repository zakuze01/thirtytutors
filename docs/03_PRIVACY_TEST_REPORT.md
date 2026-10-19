# M3 — memory and privacy

Evidence: full regression 247 passed, 0 failed, 0 skipped, 75% coverage; final
focused privacy/profile/backup rerun 41 passed after data-directory/recovery changes.
The earlier SQLite ResourceWarnings were fixed by closing every new transaction;
the final full run has no warnings. DPAPI tests used real win32crypt on Windows.
Non-Windows CI uses an explicit test-only vault seam; production fails closed there.

- App data now lives in `%LOCALAPPDATA%/CompanionLite`, separate from upstream.
  Legacy ThirtyTutors ZIP backups are imported explicitly; no implicit moves/deletes
  from original storage. SQLite namespaces and all new memory queries include profile.
- Windows-user DPAPI encrypted key files; profiles JSON/bak have null secret values.
  Existing plaintext profiles are snapshotted as encrypted recovery files before
  migration. API responses and new portable exports exclude keys; exports also redact
  an exact profile key accidentally pasted in a transcript. No raw audio/enrollment
  is exported by Lite. A legacy ZIP's credentials migrate directly to DPAPI.
- Before overwriting an existing profile during import, an encrypted recovery archive
  is saved. Invalid import rollback restores profile/settings/key/history. Tests cover
  malformed nested turn data, zip traversal and cross-profile conversation collision.
- Explicit Conversation/Learning memory domains coexist with existing history,
  rolling summaries and vocabulary. Full erase removes conversations, turns, summaries,
  learning data, explicit memory and provider handles. Epoch checks prevent late
  summarization/pending transcript writes from resurrecting forgotten content.
- Local server binds loopback only. Per-process launcher capability establishes an
  HttpOnly SameSite=Strict cookie; HTTP/WS require capability, trusted Host and matching
  Origin when present. Access logging is disabled so launch tokens are not logged.
  CSP disallows external scripts/frames. Another process running as the same Windows
  user is outside this boundary; this is not a defense against a compromised account.
- Lite clears tracing credentials instead of using environment/profile telemetry.
  Private provider diagnostics are suppressed; UI errors are classified/generic.

Close the app before rollback: `python -m thirtytutors.profile_recovery SNAPSHOT`.
Only `.pre-secrets.dpapi` / `.pre-import.dpapi` within the app data directory are
accepted. Recovery requires the same Windows user/machine; portable backups require
re-entering a key on a different machine. Existing external legacy backups are not
rewritten/deleted; users control those files. Logical erasure is not forensic disk wiping.

Native GUI data workflows and restart acceptance still need M4/M5 smoke tests.
