# Dependency decisions before removal

| Component / verified call path | Decision | Reason / migration |
| --- | --- | --- |
| desktop_entry -> desktop -> main | KEEP | pywebview shell, loopback uvicorn, bounded shutdown |
| main -> live_session -> google.genai Live | KEEP | Bidirectional speech, resumption, retry |
| audio.js -> pcm-processor -> websocket.js | KEEP | 16 kHz mono PCM in, 24 kHz playback out |
| standalone AudioContext/playbackBus in audio.js | KEEP | Existing path independent of avatar sink |
| memory, summarization, profiles_store, backup | KEEP / harden | SQLite persistence, summaries, vocabulary, migration |
| scenarios | KEEP / adapt policy | Reuse roleplay text; remove forced word/quiz loop |
| FastAPI, uvicorn, google-genai, websockets, numpy, pywebview | KEEP | Live relay and desktop runtime |
| platformdirs, Jinja2, protobuf, googleapis-common-protos | KEEP / audit transitive | Storage, templates, provider runtime |
| python-docx, rich, markdown, python-multipart, pywin32 | KEEP if used | Existing export, console, release notes, upload, Windows integration |
| Three.js, TalkingHead, HeadAudio, Draco, model-en-mixed.bin | REMOVE | Rendering, geometry, visemes; vendor tree in package-data |
| avatarDrawer, avatarPreview, avatar selection/photos | REMOVE / replace voice picker | Voice provider list must not depend on GLB or WAV |
| landing marketing/tutorial videos, update bell/assets routes | REMOVE | No first-run asset download or upstream updater |
| cli._install_extras -> pip webrtcvad-wheels/resemblyzer | REMOVE | Forced bootstrap contradicts PTT-only P0 |
| main lifespan -> speech_detection.warm_up -> backend.get_model -> Resemblyzer | REMOVE from P0 startup | Existing lazy import is not enough while startup calls it |
| speech_detection verifier/enrollment/audio_utils | DEFER | Keep compatibility tests initially; no P0 enrollment/UI or runtime invocation |
| torch, librosa, scipy | REMOVE from mandatory deps after tests | Speaker backend dependencies, not Gemini streaming; verify import graph and first run |
| webrtcvad/resemblyzer | DEFER optional P1 | Never silently install; no claim of speaker filtering in P0 |
| observability / Langfuse | DISABLE in Lite runtime | No remote tracing of private conversations |
| .github/workflows/ci-cd.yml publish + tag trigger | REMOVE in M0 | Prevent accidental package-name publication |
| packaging/windows files mentioned in .gitignore | REBUILD in M5 | Not tracked/present in this checkout |

Tracked source: 210 files; thirtytutors tree: 26,810,440 bytes before changes,
excluding separately downloaded assets. This is source size, not installed footprint.
Dependency versions and license metadata: docs/test-logs/dependency-license-inventory.json.
