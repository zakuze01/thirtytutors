# Preview 5 — quiet/fragmented speech onset and microphone diagnostics

Reported: continuous listening misses speech; push-to-talk displays Spanish text
although the requested conversation is Vietnamese/English. The user confirmed
using the Realtek 3.5 mm microphone. The installed controller hash matched preview
4. Windows microphone/device/desktop permissions were already enabled. Earlier
UI inspection showed Realtek as default input and GS3 as default output.

## Findings and changes

The previous energy gate required 120 ms of uninterrupted above-threshold energy.
An 8 ms unvoiced/quiet packet reset all onset progress. This deterministically
misses a simulated voiced/unvoiced syllable pattern, even when the voice peaks are
above threshold. This is a confirmed algorithm failure; it is not proof that it
was the only cause on the user's physical microphone.

The gate now requires 120 ms of above-threshold audio in a rolling 240 ms window,
with the current packet voiced. Short consonant gaps no longer reset onset.
Release hysteresis tolerates dips down to 60% of the onset threshold. Default
threshold is reduced from 0.014 to 0.007; explicit choices are 0.014/0.007/0.0035.
Sparse short clicks remain below the speech-window requirement. The same local
energy limitations apply: TV, other people or noise can trigger it; this does not
classify speakers or words. The 800 ms pause and 30 s maximum remain bounded.

The UI shows a local PCM level meter, RMS in dBFS, detected/sending state and actual
track device label. Meter values average packets over approximately 100 ms and
are never persisted. Startup/stop/permission failure reset the display. Switching
windows still stops capture, but now gives the reason and tells the user how to
restart it. No background microphone permission or automatic rearming was added.

There is no hardcoded Spanish conversation in push-to-talk or continuous input.
Both modes forward mono PCM16 microphone audio, and the Live UI displays Gemini's
input transcription. The image alone cannot establish what the original spoken
words were. If the user said Vietnamese/English, the Spanish line is an incorrect
transcription, not proof the microphone records in Spanish. Existing wrong text
can influence later conversation context; starting a new conversation is a safe
way to test without deleting history.

Policy revision 5 hints that Vietnamese/English are expected, says not to translate
speech into a third language, and asks for clarification before acting on uncertain
or unexpected-language speech. This is model guidance, **not a deterministic fix
or API language lock for Live transcription**. The installed Google SDK's generic
AudioTranscriptionConfig has no language selector. No unsupported parameter was
added and no fake corrected transcript is substituted. Google's [Live capabilities
guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities) documents input
transcription and raw PCM transport. Its separate [Transcribe Live
model](https://ai.google.dev/gemini-api/docs/live-api/live-transcribe) supports
language hints, but changing the conversation to that separate pipeline is outside
this microphone patch.

## Executed evidence

- Python: **298 passed**, zero failures/skips, **76% coverage**, 43.12 s.
- Node: **9 passed**, covering quiet input, syllable gaps, sparse clicks, release
  hysteresis, playback threshold, silence and maximum duration.
- Browser with fake microphone/AudioContext/socket against isolated localhost
  REST: silence opens zero turns; quiet fragmented PCM opens/ends one turn using
  one mic stream. Meter reports approximately -46 dBFS and the synthetic track
  label. Blur stops all tracks, resets the meter and explains the stop.
- Lint/format/JavaScript syntax pass. Evidence in `test-logs/preview5-*`.

No real voice was recorded for these tests, no raw audio was saved, and no paid
provider call was made. Realtek speech capture, echo, Vietnamese/English recognition
and actual conversational quality remain **INCONCLUSIVE** until a physical test.
This patch does not claim the Spanish-transcript issue is resolved.
