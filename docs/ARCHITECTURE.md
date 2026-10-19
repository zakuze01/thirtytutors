# Verified starting architecture

```text
desktop_entry / CLI -> desktop.run -> uvicorn (127.0.0.1) + pywebview
  -> main FastAPI -> routes_pages (Jinja2), routes_api, /ws/session
mic -> getUserMedia -> AudioWorklet /pcm-processor.js -> PCM16 16 kHz
  -> websocket start_turn/audio_chunk/turn_complete
  -> live_session activity_start/audio/ activity_end -> Gemini Live
Gemini events -> audio_chunk/transcript/status -> browser websocket.js
  -> audio.js PCM16 -> Web Audio 24 kHz -> playbackBus -> speakers
  -> optional avatarAudioSink / HeadAudio (to remove)
profile -> profiles.json; conversation/turns/summaries/learning -> memory.db
```

Live relay retains turn buffers, resumption handles, rolling summary reseeding,
GoAway/retry handling and student/tutor transcript persistence. Actual mode changes
will require a new provider session if system instructions cannot be updated.
Provider resumption must not silently retain an older mode's instruction.

Current startup initializes databases/migrations and schedules speaker model warmup.
main also creates and mounts avatar/voice/photo/marketing directories at import.
CLI installs optional speaker packages and downloads asset groups; updater polls
PyPI/GitHub and can pip-upgrade the upstream package. Those paths must be removed.

Target: retain the same streaming relay and persistence, introduce validated policy
data, explicit microphone controls, provider voice selection, safe secret storage,
and a single lightweight local UI. No new frontend framework or external server.
