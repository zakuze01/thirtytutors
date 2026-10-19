# Preview 4 — DeepSeek replies with Gemini listening and speech

User selected the hybrid voice option and acknowledged that both API keys are
required. Gemini Live remains the default. No automatic provider fallback occurs.

## Use

Install the current `dist/CompanionLite-Preview-Setup.exe`, open Cài đặt / Profile,
choose **DeepSeek trả lời + Gemini nghe/đọc**, and enter both keys there. Blank key
fields preserve saved credentials. Save, then choose Kết nối / Retry. Continuous
listening remains opt-in; Escape stops microphone and playback. Do not paste keys
into a conversation or send them to the developer.

DeepSeek Flash is the default response model; V4 Pro is another explicit choice.
Transcription uses Gemini 3.5 Flash-Lite. Speech uses Gemini 3.8 Flash-Lite TTS,
with Gemini 3.8 Flash TTS as an explicit alternative. Model access, quota and
billing depend on the user's accounts. This integration does not promise a free
tier or lower total cost than Live: it makes transcription, response and speech
requests sequentially. DeepSeek thinking is disabled and response generation is
limited to 512 tokens for short conversational turns.

## Routing and privacy

The existing voice controller selects `/ws/hybrid` from saved conversation config.
The relay accepts the same explicit start/audio/end protocol as push-to-talk and
local speech detection. Google receives microphone audio for transcription;
DeepSeek receives that transcript, the conversation policy and permitted context;
Google receives the exact DeepSeek reply as TTS input. There is no extra model
rewriting the reply before speech. Recognition and speech quality still require
live acceptance. The hybrid model cannot assess pronunciation from its transcript.

Both credentials use separate current-user Windows DPAPI files. Neither is
returned by profile APIs, written into profiles JSON or included in portable
backups. Export redacts known keys accidentally pasted into transcripts. Legacy
plaintext DeepSeek keys migrate with encrypted rollback. A backup import keeps
existing device credentials; profile deletion removes both vault entries.

Hybrid HTTP uses fixed HTTPS endpoints, header credentials, no redirects, no
environment proxy inheritance, bounded response sizes and timeouts. Errors shown
in the UI never contain raw provider response bodies. Google Interactions requests
set `store=false` and never use a previous interaction ID. This disables API
conversation-state storage; provider-level data retention remains governed by
each provider's terms, not by local memory controls.

Microphone PCM stays in RAM: 32-second server bound accommodates the local gate's
30-second maximum plus pre-roll. Speech output is verified as mono PCM16 WAV at
24 kHz before playback. No raw audio files are saved. Memory off prevents seeding
stored history, summary or explicit memories into new hybrid sessions; current
session turns remain available in RAM. Local transcript history continues to be
saved for the user's review and deletion. Explicit long-term memory and existing
summaries are reused only with consent. The hybrid path does not automatically
generate new rolling summaries; it sends at most 12 recent turns plus allowed
summary/confirmed memory.

## Interruption and failures

New speech cancels the previous async pipeline. Generation guards reject stale
results even if a transport ignores cancellation. Profile and conversation privacy
epochs prevent late results from being persisted, forwarded to another provider,
or played after memory erasure. Policy changes cancel pending work and clear
seeded turns when memory permission changes. Disconnect cancels pending work and
clears audio/context buffers. Empty transcripts do not invoke DeepSeek or TTS.

A TTS failure retains the visible text reply and shows an error; no audio success
is fabricated. Errors remain visible after the turn-complete message. Initial
configuration/key failures do not trigger automatic reconnect loops. Live and
hybrid sockets reject using the wrong saved provider.

## Slang

`friendly_slang.py` contains 28 family-friendly Vietnamese/English pairs from the
reviewed draft. Cheeky mode may use at most one phrase in a turn, often none.
Praise must follow observed effort/wording; retry phrases respect correction and
practice settings. Gendered family addresses are not enabled by default. “Gút job”
is explicitly a Vietnamese joke; the English model phrase remains “Good job”.
Policy revision 4 prevents resuming a Gemini Live handle with the old prompt.

## Evidence and acceptance limits

Automated regression and mocked browser results are recorded in `test-logs/preview4-*`.
Final regression: **297 passed, zero failed/skipped, 76% coverage, 42.32 s**;
5 Node VAD tests pass. Ruff lint/format and JavaScript syntax checks pass.
Hybrid provider module coverage is 94%. These figures do not imply live quality.
Provider tests use synthetic keys and HTTPX MockTransport. They verify exact
endpoint/header/model routing, transcription input, verbatim TTS input, WAV format,
key migration/export/delete, HTTP failures, malformed/oversized responses, input
bounds, interruption at all three stages, privacy erasure, shutdown, policy and
memory changes, and websocket greeting/review/preview behavior.

Browser QA uses fake microphone, AudioContext and WebSocket against isolated local
REST storage. It exercises provider selection/persistence, route selection,
continuous turns and Escape; it does not test physical audio or paid APIs.

Real Gemini/DeepSeek calls, physical microphone/echo, bilingual pronunciation,
end-to-end latency, model availability for the user's accounts and clean Windows
10/11 installation remain **INCONCLUSIVE**. This is a private QA preview, not
completed V1 acceptance. No PyPI publication, GitHub Release or installer upload.

## Official API references checked 2026-10-19

- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/): current model IDs, non-thinking requests and token limits.
- [Gemini audio understanding](https://ai.google.dev/gemini-api/docs/audio): inline audio and transcription.
- [Gemini speech generation](https://ai.google.dev/gemini-api/docs/speech-generation): Interactions TTS input, voice configuration and unary WAV output.
- [Gemini Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview): stateless `store=false` and REST output steps.
- [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite): transcription model capability.
