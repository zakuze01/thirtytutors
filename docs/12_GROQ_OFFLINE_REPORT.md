# Preview 8 — Groq STT/chat and offline Vietnamese/English speech

User approved Groq hearing/replies with local speech, and explicitly chose a
warning followed by a manual paid-Gemini switch. The user has a Groq key and will
enter it directly in the app; no credential is requested in chat or source.

## Implementation and data flow

The existing bounded hybrid websocket/session, policy, cancellation, memory and
audio player are reused. Groq uses Whisper V3 Turbo (or V3) transcription,
not translation, with multilingual auto-detection. GPT OSS 20B (or 120B) returns
short validated vi/en speech segments. Only fixed Groq endpoints receive its
key. Requests disable environment proxies/redirects, bound time/response sizes,
and sanitize errors. Gemini/DeepSeek are never called in Groq mode. Raw PCM is
held in bounded RAM and uploaded to Groq; allowed text/memory context goes to
Groq. Existing profile-memory opt-out and erase generation guards remain active.

Offline speech is a separate unmodified eSpeak NG 1.52.0 CLI process using text
stdin and WAV stdout. Vietnamese/English segments select vi/en-us voices, then
PCM is converted to the existing mono PCM16/24kHz player. No raw audio files,
shell command interpolation, runtime downloads or heavyweight model stack.
Windows child consoles are hidden. Cancellation discards late audio and stops
future segments; an already running CLI finishes or reaches its 12s timeout.
There is also a 35s inter-segment rendering deadline and 120s output-audio bound.
The engine is intentionally a compact robotic voice, not neural/Gemini quality.

The official pinned MSI is administratively extracted into build/ only, not
installed into Windows speech/registry. The app invokes the independent CLI via
standard text/WAV pipes, not DLL linking. Installer includes the separate tool,
data, GPL and component notices, full corresponding upstream source archive with
its build scripts/instructions. No source/binary modifications to eSpeak NG.
Hashes: MSI `7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9`;
source `bb4338102ff3b49a81423da8a1a158b420124b055b60fa76cfb4b18677130a23`.

## Quota and paid switch

Only whitelisted numeric rate-limit headers are exposed. Remaining daily
requests and tokens/minute appear as snapshots for hearing/chat separately;
10% remaining shows an early warning when headers provide the required counts.
Audio-hour/day limits and every hidden account restriction cannot be inferred
from these headers. HTTP 429 can be temporary rate limiting, not necessarily a
fully exhausted daily allocation. The UI says limited/exhausted rather than
asserting an exact reset or available currency balance.

402/429 stops subsequent provider calls for that session, disables capture and
exposes a clearly priced manual switch. Nothing calls Google before that click.
The saved Gemini key is required. Selection is persisted for that conversation;
no failed utterance is replayed and the microphone stays off. If the conversation
changes while the click is pending, the paid transition is discarded. Retry
explicitly starts a new Groq session; there is no automatic paid fallback,
account upgrade, card submission or automatic microphone rearm.

Groq's free tier is an account condition, not a property guaranteed by its API
key. A paid-tier key may be billed from the first request. The app clearly states
it cannot verify the billing tier; quota snapshots are not spend monitoring.
Groq credentials join the existing DPAPI vault, public-profile masking,
migration, portable-backup redaction and deletion paths.

## Tests before packaging

- 315 Python tests pass, zero failures/skips, 77% coverage, 45.31s. New cases
  cover credential/backups, fixed-endpoint multipart transcription, structured
  bilingual replies, local PCM conversion, malformed responses, quota stop/no
  retries, missing offline engine, successful pipeline storage and cancellation.
- 20 Node microphone/VAD tests pass; JavaScript syntax and Ruff lint/format pass.
- Browser uses synthetic socket/mic against an isolated real local API. Zero
  startup microphone calls. Near-limit snapshot shows warning. Exhaustion stops
  capture, disables mic and makes zero new provider-init requests before a click.
  Clicking persists Gemini, keeps mic off, hides quota panel. Changing the active
  conversation during pending click makes zero paid config updates.
- Real eSpeak CLI synthesis, no network/playback: a two-segment sample produced
  214,922 PCM bytes (4.48s). Real offline-preview HTTP endpoint produced 291,418
  PCM bytes (6.071s); mocked browser player scheduled it with zero provider socket
  messages and no mic capture. This proves synthesis, not subjective voice quality.

No real Groq key was available to these tests. Actual Groq account quota,
Vietnamese/English recognition, live reply quality, latency, physical playback
and barge-in/echo behavior need in-app verification after key entry. Existing
clean-machine Windows 10/11 acceptance remains pending. Windows build/update
evidence is appended only after checks; no public release/upload is performed.

Primary references checked 2026-10-19:
[Groq STT](https://console.groq.com/docs/speech-to-text),
[models](https://console.groq.com/docs/models),
[quota headers](https://console.groq.com/docs/rate-limits),
[billing](https://console.groq.com/docs/billing-faqs),
[eSpeak NG release](https://github.com/espeak-ng/espeak-ng/releases/tag/1.52.0).

## Windows preview 8 evidence

Clean source `458d63c2d049b8c13dec7e8565691e77f641d690`; PyInstaller and NSIS
exited 0. Installer 60,798,180 bytes, SHA-256
`ba35a7440b09f4b6869f5cfbde9e107433556eaaa3b48379d403472c365369aa`.
Frozen UI loaded with mic off in 4.487s and exited 0. The exact bundled CLI/data
produced 205,400 PCM bytes (4.279s); source archive and GPL notice were present.
Credential and forbidden-asset scans passed. In-place install exited 0, all five
data files matched pre-update hashes, and EXE/static/engine/license/source files
matched the tested build. Native opening could not be confirmed: the automation
helper first failed to launch and the user stopped the retry with physical Escape.
No further native input was attempted after that stop. Real key entry remains
the user's action. Preview 9 supersedes the manual Gemini fallback described above
with a manual DeepSeek-chat/offline fallback only for chat quota.
