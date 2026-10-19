# Preview 3 — cheeky practice, continuous listening and barge-in

User-requested addition: cheekier humor, asking for another attempt after an error,
and conversation without holding a microphone button for each turn.

## Behavior and settings

Validated `humor_style` (gentle/cheeky) and `practice_style`
(natural/repeat_until_clear) persist with conversation config and travel through
the existing controlled provider reconnect. Cheeky is the default humor style;
natural conversation remains the default practice style. The repeat setting is
explicitly selected in the main UI. Corrections Off overrides it.

Repeat policy selects one observed short target, models it, waits for another turn,
and holds the same target until understandable wording is observed. It simplifies
after repeated difficulty and honors skip/stop/topic change. It never fabricates a
successful attempt or a pronunciation score from transcripts. These are model
instructions, not a deterministic phonetic grader; actual behavior is unverified live.
Humor can use Vietnamese banter/wordplay/running jokes about a situation, without
shaming the learner. Policy revision 3 drops old-prompt provider handles on upgrade.

## Continuous mic and interruption

An explicit Bật nghe liên tục button opens the selected mic once. It is unsaved,
off at startup, and never rearmed by connection/focus restoration. Tắt mic stops
tracks. Escape stops both tracks and playback. Blur, Settings, memory modal,
provider/browser reconnect, socket error, permission failure and device loss stop
capture. Late permission completion is discarded after cancellation.

`speech-gate.js` detects PCM energy locally: 120 ms onset, bounded 320 ms pre-roll,
800 ms end silence, 30-second maximum turn. User sensitivity is configurable;
threshold increases during playback. It is not speaker recognition or semantic
speech classification: other voices, TV or noise can trigger it. Browser echo
cancellation/noise suppression are requested, not certified effective. Headphones
are advised if playback causes false activation. No raw audio is saved; only a
small rolling pre-buffer is retained in memory, with detected speech/padding sent
to Gemini. No torch/resemblyzer enrollment or model installation is needed.

Local speech start clears queued playback and invalidates pending async playback
work. The existing manual activity/audio protocol is reused. Provider config sets
START_OF_ACTIVITY_INTERRUPTS explicitly. Server commits the interrupted observed
reply separately, ignores late model output/turn completion while user input is
open, keeps input transcription, and avoids duplicate activity boundaries. If old
packets arrive after mic release, output remains suppressed until the old generation's
interruption/completion boundary, preventing playback from restarting with stale audio.

Protocol reference checked 2026-10-19: Google's
[Live capabilities guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
documents manual activityStart/activityEnd with automatic VAD disabled, clearing
playback on interruption, and at least 500 ms silence/pre-roll for client VAD.
The implementation uses 800 ms and 320 ms respectively. Provider/model availability
and acoustic behavior still need real-key/device validation.

## Executed verification

- Python: **262 passed, 0 failed, 0 skipped**, 74% coverage, final run 27.28 s.
- Node: **5 passed, 0 failed**, deterministic PCM tests for silence/click rejection,
  bounded pre-roll, multi-turn/pause boundaries, elevated playback threshold,
  maximum duration and frame-size independence.
- Ruff check/format and JS syntax checks pass. Windows/manual CI now includes Node
  tests; remote CI has not been run here.
- Mocked real FastAPI websocket integration: user barge-in during old model reply,
  stale model audio/transcript discarded even after mic release, old/new observed turns separate, exactly
  one start/end despite duplicate boundaries. Provider/audio are synthetic.
- Browser with fake microphone/AudioContext/WebSocket: startup mic calls 0;
  silence sends no audio; two automatic turns require one initial mic activation;
  400 ms pause keeps the turn open; queued playback 1 -> 0 on speech; tracks stay
  live between turns and end on explicit stop. Late permission, denial, blur,
  reconnect/drop and Escape leave mic off. Space key release does not disable
  continuous listening. New style settings persist via the real local REST API.
- A pending playback resume canceled by Stop cannot recreate an audio source
  (queued sources remain 0). No console errors/warnings in exercised flows.
- No horizontal overflow at emulated 500 or 1440 CSS pixels. This is not native OS DPI QA.

Exact outputs are `test-logs/preview3-*`; `tests/browser_voice_mock.js` is QA-only
injection and never loaded by the product. It replaces mic/audio/provider fully;
there is no claim of physical mic, real echo cancellation, audible interruption,
speech recognition or humorous generated responses having passed.

Windows frozen smoke/build results and artifact manifest are recorded alongside
these logs. No existing owner installation/profile is overwritten during QA.
V1 clean Windows, physical devices, twelve live scenarios and latency gates remain.
