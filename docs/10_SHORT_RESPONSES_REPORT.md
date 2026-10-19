# Preview 6 — shorter spoken turns and measurable response waiting

User feedback: speech is too long and response starts slowly. The installed app
was using Gemini Live, not the optional sequential DeepSeek/Gemini pipeline.

## Changes and limits

Policy revision 6 asks ordinary Friend replies to use 15–35 words total across
Vietnamese and English, typically one or two short sentences. Teacher replies aim
for 40–60 words. Humor shares the same budget; questions are optional. Responses
should address the immediate point, avoid repeated translations, extra examples
and recaps, then stop and wait. Explicit requests for details, stories or session
reviews can expand the reply. These are model instructions, not a deterministic
word-count guarantee. Output is not cropped mid-sentence. Old-prompt Live handles
are invalidated by the existing policy revision mechanism.

Local speech endpoint silence changes from 800 to 600 ms by default. This removes
200 ms of application-controlled waiting after speech falls below the release
threshold; it is not a measured 200 ms improvement in total cloud latency. A
Nhịp đáp control offers 600/800/1200 ms, labeled Nhanh/Thoải mái/Chờ tôi nói chậm.
The selection is stored locally in the browser and can change while capture is
active. It does not change provider, key, quota, microphone or recorded content.
Longer pauses are available because a short endpoint can interrupt someone who
pauses while forming a sentence.

Gemini 3.1 Live is explicitly configured for MINIMAL thinking. Google's [model
documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-live-preview)
already documents this as its low-latency default, so the explicit setting is not
claimed as a new speedup. SDK 1.70 supports this field. There is no low token
cutoff that might truncate speech and no silent model/provider switch.

The Live relay already forwards audio chunks immediately; it does not wait for
the complete response or transcript. The optional hybrid provider still performs
transcription, response and speech sequentially and is not represented as equally
fast. No synthetic or provider speed benchmark is represented as real latency.

A local Giọng trả lời sau … giây indicator measures from sending turn_complete
to scheduling the first accepted audio chunk, including scheduled playback queue
delay. It excludes the preceding silence window and cannot measure the physical
speaker or network/provider stages separately. Only the first scheduled audio
chunk updates it; later chunks do not overwrite it. New input/cancellation resets
the pending timer. The number is local and not persisted or uploaded.

## Verification

- **298 Python tests pass**, zero failures/skips, **76% coverage**, 40.79 s.
- **10 Node PCM/VAD tests pass**, including exact 600 ms endpoint and 1200 ms
  patient pause, onset gaps, quiet signal, clicks and barge-in threshold.
- Mocked browser against isolated local REST: no turn completion before 600 ms;
  one at 600 ms; patient mode retains 800 ms silence and completes at 1200 ms.
  Synthetic first audio updates the timer once, later packets leave it unchanged,
  and Escape stops capture. 1200 ms selection survives page reload; startup mic
  calls remain zero. This uses fake audio/socket, not a paid service.
- Explicit config inspection: MINIMAL thinking and no hard output token cutoff.
- Ruff lint/format and JavaScript syntax pass.

Real response length compliance, end-to-end latency and user perception still
require actual conversation. No claim that Gemini/API/network latency is fixed.
No public release or artifact upload is performed.
