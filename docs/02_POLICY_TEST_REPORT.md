# M2 — companion policy and bilingual conversation

Automated checks: 237 passed, 0 failed, 0 skipped; 73% coverage. Ruff check/format
and node --check pass. This certifies policy assembly and mocked relay behavior,
not the actual model's conversational compliance or speech quality.

Validated ConversationPolicy separates Friend/Teacher, correction intensity,
reply preference, difficulty, requested pace and memory policy. Removed mandatory
five-word/quiz/repetition prompt; default profile languages Vietnamese/English.
Reused roleplay scenario registry, excluding the strict default tutor persona.

Switching policy mid-response flushes pending transcripts, clears replay buffer
and provider resumption, persists config and reconnects the provider behind the same
browser socket. UI waits for successful session_status with the new mode. Mocked
test switches during an incomplete response: two preserved turns, no duplicates,
new Teacher prompt, old session not resumed, recent observed context reseeded.

## Live QA matrix

All twelve cases below are INCONCLUSIVE: no real Gemini key/microphone acceptance
run has occurred. No personal transcript/audio or fabricated model response is used.
Automated assertions cover invariants where indicated; they are not live PASS.

| # | Scenario | Automated evidence / remaining live check |
|---|---|---|
| 1 | Friend: Hi, how was your day? | Friendly policy; actual response pending |
| 2 | Explain catch up in Vietnamese | Explicit language command policy; response pending |
| 3 | Yesterday tôi đi gặp khách hàng | Mixed-language context survives mocked mode change |
| 4 | Correct my last sentence | Evidence-only correction policy; response pending |
| 5 | Ordinary grammar error in Friend | No mandatory repetition/quiz in assembled prompt |
| 6 | Switch Teacher, max two errors | Mid-response mocked switch + limit policy tests |
| 7 | Speak more slowly | Prompt request only, no guaranteed audio rate setting |
| 8 | Interrupt speech | Stop scheduled Web Audio sources; actual mic/audio pending |
| 9 | Drop/recover network | Existing mocked reconnect/replay regression; real network pending |
| 10 | Restart/persist | Existing SQLite persistence tests; native interaction pending |
| 11 | Erase memory | M3 work; not passed here |
| 12 | Clean Windows installation | M5 work; not passed here |

Provider notes checked 2026-10-19: [Live capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
describes raw PCM16 input at 16 kHz/output at 24 kHz and lists 3.1 Flash Live as
legacy preview. The inherited model remains configurable in constants, not certified
available for a particular key. [Voice documentation](https://ai.google.dev/gemini-api/docs/speech-generation)
provides provider voice names. Local avatar/WAV availability does not gate the picker.
Actual Live voice availability, bilingual quality and SDK compatibility require opt-in
live verification. Do not infer pronunciation accuracy from transcription.
