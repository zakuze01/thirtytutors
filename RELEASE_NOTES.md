# Companion Lite private QA preview

Derived from ThirtyTutors 1.2.1 at 2d37a142d0552ac44ac69b54d0d78ddbf7c49c04.
M0–M4 implementation is committed and tested; V1 release acceptance is incomplete.

- Removed 3D renderer/vendor, avatars, marketing media, forced speaker bootstrap and
  upstream update/download paths. Kept the Gemini streaming relay and local memory.
- Friend/Teacher policies, Vietnamese-English preferences, bounded correction policy
  and controlled mode reconnect. Provider behavior still requires live acceptance.
- Windows DPAPI credentials, secret-free exports, local access capability/Origin checks,
  separate app storage, recoverable migration and scoped memory erasure.
- Voice-first plain web UI, explicit PTT/mic indication, stop/mute/transcripts,
  settings, voice selector, local history/memory/backup controls.
- Windows onedir/NSIS packaging is under validation. No public publication authorized.

Outstanding: real Gemini audio/bilingual/interrupt/network QA; 10–20 live latency
turns; native DPI and clean Windows 10/11 install/uninstall/mic acceptance. No claim
of reduced network latency, measured learning progress or a fully offline AI.
