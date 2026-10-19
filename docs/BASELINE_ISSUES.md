# Baseline findings (before application refactor)

1. Test collection writes asset directories to real LocalAppData before autouse
   fixtures run. Initial restricted run: 1 collection error / 214 collected items.
   Baseline workaround: patch platformdirs before import; full rerun 219 passed.
2. Host initially lacks pytest-cov/ruff. Installed in task venv; logs preserve failure.
3. API key is plaintext in profiles JSON and JSON backup manifest. M3 must migrate
   both primary/backup copies to OS secret storage and exclude exports.
4. Archive enrollment entry paths lack containment checks; profile id also controls
   storage paths. Harden import before accepting untrusted backups (M3).
5. No verified HTTP/WS per-launch secret/Origin validation. Review localhost threat
   model before exposing sensitive profile APIs in Lite (M3).
6. PTT keeps the microphone stream open after stop and eagerly requests it at page
   load. Change lifecycle/indicator in M1/M4; no silent mic activation.
7. Forced speaker bootstrap/startup warmup and upstream asset/package updater exist.
   Remove in M1; tests currently mock speaker backend and need no real ML model.
8. Packaging files mentioned by source comments are ignored/untracked. Reconstruct
   PyInstaller onedir + Inno Setup in M5, validate on Windows; no artifact yet.
9. Provider model IDs/voice options copied in source need current provider verification
   and opt-in live tests. Unit tests cannot certify model availability or speech quality.
10. Baseline test environment inherits unrelated global packages; two pip-check
    conflicts are recorded. Build environment must be fresh, without inheritance.
11. Native first-run landing automatically downloaded avatar/voice/photo bundles
    without a setup click. Window closed on a timer but process awaited downloading,
    returning at 39.08 seconds. See desktop-smoke.log; remove downloader in M1.
