# Companion Lite private QA preview

Preview 2 (`1.2.1+companionlite.2`): Friend Mode now supports playful beginner
Vietnamese–English scaffolding, short phrases, natural recasts and optional gentle
humor. New defaults are balanced languages and beginner; existing saved preferences
are retained. Familiar vocabulary can recur naturally without forced drills.
See docs/06_BILINGUAL_PLAY_REPORT.md for verification and live limitations.

Derived from ThirtyTutors 1.2.1 at 2d37a142d0552ac44ac69b54d0d78ddbf7c49c04.
M0–M5 implementation is committed with local QA evidence; V1 acceptance is incomplete.

- Removed 3D renderer/vendor, avatars, marketing media, forced speaker bootstrap and
  upstream update/download paths. Kept the Gemini streaming relay and local memory.
- Friend/Teacher policies, Vietnamese-English preferences, bounded correction policy
  and controlled mode reconnect. Provider behavior still requires live acceptance.
- Windows DPAPI credentials, secret-free exports, local access capability/Origin checks,
  separate app storage, recoverable migration and scoped memory erasure.
- Voice-first plain web UI, explicit PTT/mic indication, stop/mute/transcripts,
  settings, voice selector, local history/memory/backup controls.
- Windows onedir/NSIS installer built and locally tested on Windows 11, including
  rejecting install/uninstall while running. Clean Windows acceptance is pending.
  No public publication authorized.

Outstanding: real Gemini audio/bilingual/interrupt/network QA; 10–20 live latency
turns; native DPI and clean Windows 10/11 install/uninstall/mic acceptance. No claim
of reduced network latency, measured learning progress or a fully offline AI.
