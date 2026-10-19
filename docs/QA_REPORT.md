# Companion Lite QA status — 2026-10-19

**V1 acceptance is INCOMPLETE. Private local QA preview only.**

Preview 5 repairs quiet/fragmented speech onset and adds local microphone signal
diagnostics: 298 Python tests and 9 Node tests pass, 76% coverage. Physical Realtek
capture and incorrect-language transcription still require live validation. See
`09_MICROPHONE_FIX_REPORT.md`.

Preview 4 adds optional DeepSeek + Gemini voice and the reviewed banter examples:
297 Python tests pass (76% coverage) and 5 Node PCM/VAD tests pass. The new path
has synthetic HTTP/provider and mocked browser evidence; real-key cloud speech
and latency remain INCONCLUSIVE. See `08_DEEPSEEK_VOICE_REPORT.md`.

Preview 3 adds cheeky humor, opt-in repeat practice and continuous microphone with
barge-in: 262 Python tests and 5 Node PCM/VAD tests pass. See
`07_CONTINUOUS_VOICE_REPORT.md`. Real mic/echo/provider acceptance remains pending.

Latest preview 2 adjusts Friend Mode for playful beginner Vietnamese–English
conversation: 254 tests passed, 74% coverage; see `06_BILINGUAL_PLAY_REPORT.md`.
The milestone table below is the historical initial-preview evidence.
Source: zakuze01/thirtytutors, branch `companion-lite/m0-audit`.
Upstream reference `2d37a142d0552ac44ac69b54d0d78ddbf7c49c04` is unchanged.
No PyPI publication, GitHub Release or installer upload has been performed.

## Milestone evidence

| Milestone | Implementation commit | Executed evidence | Acceptance limit |
|---|---|---|---|
| M0 | c6eeb2f | 219 tests passed, baseline lint/format, original native shell and asset downloads observed | Real speech/performance baseline unavailable |
| M1 | 3fecd4e | 224 tests passed; native shell; no startup model/download paths | Real Gemini voice round-trip pending |
| M2 | 5797d22 | 237 tests passed; mocked mid-response mode switch retains context, no duplicate turns | 12 live scenarios remain INCONCLUSIVE |
| M3 | aedadad | 247 tests passed; actual Windows DPAPI, migration/rollback, export/erase and local-origin tests | Same-user DPAPI is not protection from malicious code running as that user |
| M4 | 41f03b9 | 250 tests passed; browser mocked audio/socket/permission, keyboard/layout checks, native shell | Physical devices and native OS DPI pending |
| M5 | 34d3364 plus fixes through 4d66651 | 250 final tests passed, PyInstaller/NSIS, Windows 11 install/start/uninstall, locked-file guard and two-minute idle sample | Clean Windows 10/11 and live acceptance pending |

Counts are passed tests, with zero failed/skipped in those successful runs.
See each milestone report and `test-logs/` for exact outputs. A later sandboxed
pytest attempt could not access its default temporary directory (250 setup errors,
not test assertion failures); retained as `m5-sandbox-temp-error.log`. Final
rerun uses a dedicated QA temporary directory and current-user Windows context:
250 passed, zero failed/skipped, 74% coverage, 32.55 seconds. Lint and format pass.

## What was exercised

Existing speech-to-speech architecture, PCM worklet and replay/reconnect logic
were reused. Mocked provider/browser tests establish routing and state invariants;
they do not establish intelligible speech, multilingual understanding or latency.
Memory tests use isolated profiles/SQLite and synthetic keys. No real API key,
personal conversation or raw audio has been placed in this repository.

Browser UI evidence: startup never requests mic; PTT stops tracks on release,
blur and disconnect; permission arriving after release is discarded; denied
permission leaves mic off; Stop clears queued playback; offline settings persist;
explicit memories save/show; keyboard focus is visible; no console errors in the
exercised flows. Browser transport/microphone were synthetic. Screenshots and
limitations: `04_UI_TEST_REPORT.md` and `test-logs/m4-ui.png`.

Frozen onedir and installed EXE both loaded the real local FastAPI page in native
WebView2 and auto-closed with exit code 0; title Companion Lite and mic off were
read from the loaded DOM. Initial single-run page-loaded times were 5.568 s and
5.885 s respectively; the final installed build loaded in 5.855 s. These are single
smoke measurements, not cold/warm p50/p95. Final closed-app uninstall removes the
program and preserves synthetic default data; running-app install/uninstall are
rejected with exit 2 while preserving registration. Interactive erase is pending.

## Before/after measurements and missing measurements

| Metric | Original baseline | Companion Lite |
|---|---|---|
| First-run legacy asset downloads | avatars 265.6 MB, voices 7.9 MB, photos 3.6 MB observed | Removed downloader/startup paths; no 3D requests in exercised browser/native smoke |
| Native smoke process lifetime with 12-second close timer | 39.08 s, blocked by download | Source shell 12.21 s; frozen page-loaded timings above measure a different event |
| Static assets | Vendor/avatar/media UI audited in dependency map | 5 files, 287,875 bytes at M4 audit |
| Installer/disk | No comparable original installer built | Exact final bytes/hashes in build_manifest.json and M5 report |
| Idle RAM/CPU/GPU | No comparable two-minute original run | App+WebView2 summed working set 517.51 MiB; ten-second CPU sample 0.088% machine; GPU pending; see M5 report |
| Stop mic -> first audible response, 10–20 turns, p50/p95 | Not measured | Not measured: live key, actual devices and stable network run required |

No performance improvement percentage or release latency guarantee is claimed.
No real-network duplicate rate has been measured. Mocked regression tests have
zero duplicate turns in their defined reconnect/mode-change scenarios.

## Required before V1 acceptance or any distribution

1. Run all twelve spec scenarios with actual Gemini Live, record available model,
   google-genai version, devices/network and sanitized observations. Verify current
   model access for the owner's key; configurable inherited preview IDs are not
   certified available. Do not send API keys in chat or reports.
2. Test physical PTT, selected mic/speaker, interruption/mute/preview, bilingual
   replies, mode change, network disconnect/retry and persistent context after restart.
3. Validate native Windows 125/150/200% scaling, keyboard and microphone permissions.
4. Install, use and uninstall on clean Windows 10 and Windows 11 x64, including
   missing WebView2, non-admin, protected install files and upgrade/migration paths.
5. Complete comparable cold/warm startup, two-minute RAM/CPU/GPU and at least 10–20
   live response latency turns. Review transitive bundled DLL notices/license terms.
6. Owner reviews behavioral policy, privacy/migration/erase semantics, unsigned
   installer/SmartScreen experience and remaining acceptance evidence before sharing.

The opt-in provider smoke runner is `qa/live_provider_smoke.py`. It requires an
explicit `--allow-paid-api`, a currently available `--model`, and the environment
variable `COMPANION_GEMINI_API_KEY`. It only checks provider text-to-audio transport,
without saving PCM/transcript; it cannot replace the spoken manual scenarios.
No live API request has been made by the automated suite or this runner here.

Build artifacts stay in local ignored `dist/`; manifest and SHA256SUMS identify
the preview. CI Windows build is manual-dispatch only, has read-only repository
permissions, and does not publish or upload installer artifacts. CI itself has not
been run on GitHub in this session.
