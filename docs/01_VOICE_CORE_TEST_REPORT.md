# M1 — voice-only core

Implementation and offline regression PASS; live speech acceptance INCONCLUSIVE.

- 224 tests passed, 0 failed, 0 skipped, 72% coverage (m1-pytest.log).
- Ruff check and format check pass for application/tests; JavaScript node --check pass.
- New native pywebview smoke with empty isolated storage loaded UI, voices/models,
  profiles and favicon and shut down cleanly. Process returned after 12.27 seconds
  with an automatic 12-second close timer. This measures test process lifetime, not
  cold startup or response latency.
- No avatar/marketing requests or downloads in that smoke. 3D vendor/model files
  removed from package, mandatory torch/librosa/scipy removed, no CLI installer,
  no startup speaker warmup, no upstream updater. Automated deny-import test proves
  main/CLI import without the ML stack. Existing speaker compatibility module/tests
  remain deferred; P0 UI offers no hands-free or enrollment.
- Existing Gemini relay, AudioWorklet, memory, profiles and retry retained. New plain
  UI uses upstream PCM16 conversion, sample rates and playback fades, supports PTT,
  explicit connection, stop audio, transcript, provider voice selection independent
  of local assets. Mic acquisition is user-triggered; tracks stop on release/blur.
- Before: native first run downloaded 265.6+7.9+3.6 MB asset archives. After: 0 bytes
  of 3D/marketing downloads in empty-profile smoke. Source deletion is not a measured
  installer/RAM/latency improvement.
- Gemini microphone/audio, interruption, network recovery, voice quality and p50/p95
  still require an authorized test key and device session; no synthetic PASS.
- M2 policy, M3 privacy/migration and M4 full settings remain required; not a release.
