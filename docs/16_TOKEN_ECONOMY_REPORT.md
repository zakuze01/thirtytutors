# Preview 12 — compact prompts and measured chat-token usage

The user approved prompt/response optimization and token measurement, excluding
Deepgram. This change preserves the six-exchange RAM window and all confirmed
personal-card facts. No provider, API-key routing or paid-fallback policy changes.

The default policy prompt is consolidated without removing Vietnamese/English
switching, uncertain-transcription handling, child-friendly humor, correction
opt-in, evidence requirements or the ability to stop practice. Friend persona
examples shrink from seven to three. Default Friend replies now aim for one or
two sentences, 15–25 words across both languages; Teacher aims for one or two
sentences, 25–40 words. Explicit requests for detail/story/review may expand.
These are model instructions, not guaranteed output lengths or a post-hoc cut.
The existing token ceilings remain: shrinking the Groq reasoning/JSON budget
without live measurements can truncate valid replies and waste a billed call.
No automatic retry of a truncated or failed reply is added.

Identical default settings, measuring `ConversationPolicy.instruction()`:

| Mode | Before, characters | After, characters | Reduction |
| --- | ---: | ---: | ---: |
| Friend | 7,599 | 3,772 | 50.36% |
| Teacher | 4,891 | 2,882 | 41.08% |

These are character measurements, not tokenizer counts or billing savings.
Identity/card JSON serialization removes unnecessary separators but never
rewrites, drops, infers or truncates the user's confirmed facts. Static persona
and card prefixes remain stable between turns. No timestamps, counters, random
examples, cache-warming calls or extra summarization calls enter the prompt.
DeepSeek's existing automatic prefix cache may help; this change does not claim
to force a hit or manufacture cache savings.

Chat providers now read numeric `usage` from Groq/DeepSeek responses. Input and
output counts must both be valid nonnegative integers. Missing usage is unknown,
not zero. Cache hits remain a subset of input, never added to input totals again;
unknown cache and reported zero remain distinct. Invalid/inconsistent cache or
reasoning values become unknown. Output counts may include provider reasoning.
Counters are retained even when a valid API response is truncated or TTS later
fails, because the chat request may already be billed. A storage failure does
not fail or replay that request. Task-local counters prevent simultaneous or
cancelled voice tasks from reporting each other's counts.

SQLite retains at most 500 anonymous numeric chat records across the machine:
timestamp, fixed provider label, input/output/cache/reasoning counts. No profile
ID, model text, transcript, prompt, key, audio, request ID or raw provider payload
is saved. These counters are not part of personal-profile ZIP exports and do not
enter AI context. The local-token endpoints use the existing launch-token and
Host/Origin protections. The UI exposes the last reported call, bounded totals
and a clear-statistics button that does not alter profiles or personal cards.
The UI clearly excludes Gemini Live, speech recognition and synthesis from this
chat-only accounting. Unknown cache calls are counted separately from calls that
report cache. This is not a lifetime total, credit balance or billing statement.

Verification:

- 351 Python tests pass, zero failures/skips, 78% statement coverage, 49.70s.
  New accounting module has 100% statement coverage. Coverage is not proof of
  live provider/model behavior.
- 20 microphone/PCM/VAD Node tests pass; JS syntax, Ruff and diff checks pass.
- Tests cover numeric-only persistence, rejecting malformed counters, unknown
  versus zero, cache accounting, retention, task isolation, storage failure,
  counting a truncated paid reply without retry, stable system prefixes, TTS
  failure, authenticated REST access and clearing only token counters.
- Isolated browser checks pass totals, unknown/zero rendering, clear statistics,
  personal-card preservation and scope disclosure; no physical mic/cloud used.

App version `1.2.1+companionlite.12`, policy revision 9. Real token savings,
cache-hit rates, humor and spoken response lengths remain to be measured using
the user's live provider. No paid cloud evaluation or public release performed.
Windows build, migration and in-place update evidence follows verification.
