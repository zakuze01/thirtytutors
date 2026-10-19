# Preview 9 — DeepSeek chat before Gemini

The user accepted DeepSeek as the first paid fallback. The existing manual-click
cost boundary is retained; there is no automatic paid request. Deepgram was
cancelled and is not added. No Deepgram key or endpoint exists in this change.

The new deepseek_local choice uses Groq Whisper STT, DeepSeek JSON chat, and the
same offline Vietnamese/English CLI/player. It requires Groq and DeepSeek keys,
with no Gemini key. Existing encrypted DeepSeek storage is reused. Each provider
receives only its own credential; the DeepSeek key is never sent to Groq.
DeepSeek's JSON mode returns validated vi/en segments for local reading; thinking
is disabled and max_tokens is 1024. Invalid/truncated JSON is rejected without
speech. Privacy epochs, policy, memory and cancellation guards are reused.

Quota errors now identify speech/chat and provider. Only a Groq **chat** limit
shows the DeepSeek paid-switch button. A speech limit stops capture with a clear
message that DeepSeek cannot replace STT. A DeepSeek limit does not recursively
offer the same fallback. No retry loop calls paid services after quota pause.
Switching checks the saved DeepSeek-key flag and the active profile/conversation
again after awaiting it; user changes invalidate a pending switch. No failed
utterance is replayed, no mic rearm occurs and no Gemini service is contacted.
Selecting the mode explicitly in Settings is also supported and shows data flow
and the paid label. Gemini TTS controls are hidden in this offline mode.

Verification includes fixed-endpoint credential-isolation requests, distinct
speech/chat quota errors, missing-key no-outbound-call behavior, and a protected
websocket producing offline audio with no Gemini key. The initial websocket test
used TestClient's testserver host and was correctly rejected by localhost access
control; the fixture was corrected to an explicit authenticated localhost URL.
Production access control was not changed.

Mocked browser against isolated real local API: speech quota hides the paid
button and even an attempted click leaves Groq selected. Chat quota shows it;
before clicking Groq stays selected. After clicking, deepseek_local is persisted,
mic stays off, DeepSeek controls appear and Gemini TTS controls remain hidden.
All provider calls in automated tests use synthetic keys and mock transport.
No real Groq/DeepSeek cloud request or speech-quality/latency claim is made.

Final test/build evidence is recorded below after checks. Real recognition and
conversation require the user's keys entered in-app. No public release/upload.

Primary API reference: [DeepSeek JSON mode](https://api-docs.deepseek.com/guides/json_mode/).
