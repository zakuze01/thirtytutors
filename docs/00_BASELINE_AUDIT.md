# M0 — audit and baseline, 2026-10-19

Status: automated baseline PASS; desktop/live/performance acceptance remains INCONCLUSIVE.
This is an audit gate, not V1 release acceptance.

## Provenance and workspace

- Development origin: https://github.com/zakuze01/thirtytutors (provided by owner).
- Reference upstream: https://github.com/wiss84/thirtytutors; push URL disabled locally.
- Both main refs at audit: `2d37a142d0552ac44ac69b54d0d78ddbf7c49c04`.
- Source APP_VERSION: 1.2.1. Host Windows 11 build 26100, Python 3.13.4 x64.
- Specification read in full from D:/ThirtyTutors/THIRTYTUTORS_COMPANION_LITE_SPEC_V1.md.
- No upstream changes, uploads, release, tags, or PyPI publication performed.
- Fork CI publishing job and tag trigger removed before implementation; lint/test/build validation retained.

## Verified baseline

| Check | Result |
| --- | --- |
| pytest tests/ -v --cov --cov-report=term-missing | 219 passed, 0 failed, 0 skipped; 30.05 seconds; 67% total coverage |
| ruff check . | PASS |
| ruff format --check . | PASS, 61 files |
| Real microphone/Gemini/network interruption | INCONCLUSIVE, no authorized test key/device session configured |
| Native Windows shell open/automatic close | PASS process smoke; WebView2 loaded landing page, clean server exit, 39.08 seconds total |
| DPI, microphone, installer | INCONCLUSIVE; no installer present in tracked checkout |
| Cold/warm launch, idle RAM/CPU/GPU, first audio p50/p95 | NOT MEASURED; no performance claim |

Logs and exact dependency/license inventory are in `docs/test-logs/`. The unmodified
source was tested before changes to application code. Initial attempts failed because
coverage was missing in the host environment and import-time asset mkdir escaped the
test fixture into LocalAppData. The successful runner patches platformdirs before
source import, isolates storage, removes tracing credentials, disables unrelated pytest
plugins, and loads asyncio/cov explicitly. No real Gemini calls are made by unit tests.

The temporary venv inherits system packages to reuse the installed SDK/numpy. Its
pip-check reports unrelated pre-existing retina-face/tensorflow and selenium/typing
conflicts. This is a documented baseline environment, not a reproducible release
environment; M5 must use a fresh build venv and locked dependency inventory.

## Architecture and risks

See DEPENDENCY_MAP.md and ARCHITECTURE.md. The core streaming path already supports
PTT and standalone playback; no STT/LLM/TTS replacement is justified. Model options
currently have only one Live ID, so there is no effective alternate-model fallback.
An ID in source is not evidence that the provider currently serves it.

The original native first-run smoke used an empty isolated profile, no API key,
and scheduled window closure after 12 seconds. The landing page automatically
started downloading upstream assets: avatars.zip 265.6 MB, voices.zip 7.9 MB,
photos.zip 3.6 MB according to progress output. Shutdown waited for that task;
the process returned after 39.08 seconds. These are observed download counts,
not package/installer sizes. Files stay outside the repository in audit storage.
No voice/model call or microphone permission was exercised.

The source directly persists api_key in profiles.json and copies the profile into
backup manifests. Backup enrollment paths are joined to archive member names without
containment validation. Local HTTP/WS has no verified per-launch authorization gate;
loopback binding alone is insufficient. Track these findings in BASELINE_ISSUES.md.

## License

LICENSE was read in full and remains byte-for-byte unchanged. It is PolyForm
Noncommercial 1.0.0, with Required Notice: Copyright 2026 Wissam Metawee
(https://github.com/wiss84/thirtytutors). This project is personal/noncommercial.
Installed distribution metadata and license-file paths are captured, not assumed
from package names. Final bundled transitive/DLL notices still require M5 review.
Three.js declares MIT; several TalkingHead/HeadAudio files include MIT-style notices.
Their removal is planned. External avatar/marketing asset rights are not established
by the application LICENSE; they will not be downloaded or bundled in Lite.

## Gate decision

Proceed with offline M1 implementation because baseline unit/integration tests pass
and the existing streaming architecture is reusable. Do not mark any live speech,
privacy migration, native UX, installer, or V1 release acceptance as passed until its
own evidence exists. No public publication is authorized.
