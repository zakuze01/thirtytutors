# Preview 2 — playful first English conversation

User clarification: conversation should move naturally between Vietnamese and
English like a patient, humorous friend helping a Vietnamese beginner acquire
first spoken English, with the simplicity of early language learning.

## Changes

- Friend responds to meaning first, accepts Vietnamese/mixed/one-word replies,
  and does not require an English answer to continue. Occasional gentle humor
  is family-friendly and never mocks mistakes. Jokes are not mandatory each turn.
- Balanced language policy can switch within a turn, using a Vietnamese bridge
  and a small meaningful English phrase. It does not translate every sentence or
  enforce a language ratio. Explicit language-only requests take precedence.
- Beginner scaffolding uses short concrete phrases, familiar everyday topics,
  natural recasts, optional simple choices and pauses. It does not assume age or
  require a baby voice. Higher levels retain their own sentence/vocabulary level.
- Familiar vocabulary may recur naturally in new playful contexts instead of
  being excluded because it was previously learned. No forced repetition/quiz.
- New defaults: Friend, balanced languages, beginner. UI labels: Bạn bè,
  Việt–Anh tự nhiên, Mới tập nói. Existing saved configurations are preserved;
  choose these values and save/reconnect to apply them to an existing conversation.
- Preview version `1.2.1+companionlite.2`; streaming protocol, DPAPI and data
  schema unchanged. Previous installer/manifest retained locally under
  `dist/previous-companionlite1/`.
- Provider resumption identity now includes a policy revision. Upgrading from an
  old prompt discards its provider handle and reseeds permitted observed context
  without deleting local history or overwriting saved settings. Ordinary reconnect
  with the same revision still resumes normally.

## Verification

Full suite: **254 passed, 0 failed, 0 skipped**, 74% coverage, 31.25 seconds.
Lint/format and JavaScript syntax checks passed. Added policy regression coverage
for bilingual first-language scaffolding, optional respectful humor, and retained
English-first/intermediate preferences still allowing Vietnamese bridges.
Added regression for dropping an old prompt's handle while retaining the observed
turn exactly once; existing same-policy resumption and mid-response mode tests pass.
These assertions check assembled instructions, not generated model behavior.

Windows rebuild/native smoke evidence is recorded in `test-logs/bilingual2-*`.
No existing installed app or private profile is overwritten during QA: native
smoke runs the new onedir build with separate synthetic storage. The installer
is provided for explicit owner installation after closing the current app.

## Live acceptance still required

No real Gemini request or mic was used for this change. In particular, humor,
spoken language switching, understandable pacing and the learning experience are
not certified by prompt tests. Examples in instructions are illustrative, not
captured successful responses. Suggested targeted live scenarios:

1. Say 'Con mèo đói' — short relevant Vietnamese response and a tiny English phrase,
   perhaps playful cat humor; no grammar lecture or demand to repeat.
2. Say 'Mình want water' — understand, naturally model 'I want water', continue.
3. Reply with one word such as 'đỏ' — expand gently without treating it as failure.
4. Ask 'chỉ nói tiếng Việt' and then 'tiếp tục tiếng Anh' — follow both requests
   without resetting context or enforcing the default preference.
5. Ask for correction explicitly, then switch Teacher — verify distinct behavior
   and retained topic. Retry/reconnect must preserve the selected policy.

All five scenarios currently INCONCLUSIVE; the previous V1 acceptance gaps remain.
