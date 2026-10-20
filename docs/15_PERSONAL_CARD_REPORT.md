# Preview 11 — personal card and bounded session memory

The user explicitly replaces full conversation-history memory with a concise
personal profile. New voice transcripts are no longer persisted or summarized.
Existing transcripts, summaries, vocabulary and legacy confirmed memories remain
available for local viewing/export/deletion; none seed a new voice session.
No automatic mining or migration of old conversations is performed.

The personal card has six categories: identity, self-described personality,
current needs, relatives, interests, and special requirements/communication style.
Each category holds at most 400 characters, saved only through explicit user
confirmation. Values are Windows current-user DPAPI ciphertext in SQLite. Cards
can be inspected, edited or forgotten individually. Temporary needs default to
30 days in the UI, with one/seven/thirty-day or indefinite retention available.
Expired values remain visible for review but are excluded from provider context.
Edits/deletes invalidate session epochs and close active sockets without deleting
archived summaries. Full profile erasure includes the card.

Hybrid providers retain at most twelve text rows (six exchanges), at most 400
characters per row, in socket-local RAM. They never seed that buffer from disk.
Card expiry also drops RAM that might quote expired facts. Closing a socket
clears its buffer. Gemini Live never saves or restores provider resumption
handles, never writes transcript turns and never schedules paid summarization.
It renews the provider connection after six completed exchanges, supplying only
the current card and up to twelve recent RAM rows. There can therefore be up to
six seeded plus six newly spoken exchanges inside one provider connection.
Live transcription assembly is capped at 4,000 characters per role per turn.
The system memory section is capped at 10,000 characters. It is bounded rather
than growing with the age of the user's archive.

Planned context renewal pauses audio forwarding and displays a short wait
message. A continuously enabled microphone stays on the same capture stream;
it is not automatically reopened or requested again. Speech during that brief
renewal pause is not sent. Real network-fault recovery retains existing mic
safety behavior. An expiring Live card closes the browser socket so stale
provider context cannot keep being used; the user may need to enable the mic
again following that privacy reset.

Explicit “nhớ giúp tôi”, “nhớ cho tôi”, “hãy nhớ”, or “remember that” commands
produce an ephemeral review suggestion. The user checks the recognition, chooses
a category and presses Save. Ordinary statements do not become facts. No model
call is added for extracting personality or memory. Voice requests to change or
forget information direct the user to the card controls; the model is told not
to falsely claim it has saved/deleted facts. Actual model compliance still needs
user listening acceptance.

The checkbox now consents to sending the personal card to the selected provider.
It does not disable the short working context of the current conversation.
When disabled, the server does not even unlock the card. The UI shows at most
twelve recent transcript rows; archived transcripts require an explicit viewer
button and are never loaded into live context. Reconnecting starts fresh RAM.

Portable ZIP backups include readable personal-card facts, matching the existing
readable archive format; the UI now warns to keep exports private. API keys
remain excluded/redacted. Restores validate cards before mutation, encrypt them
on the receiving Windows account, and include the card in encrypted recovery
and rollback. Legacy backups remain readable and preserve an existing card.

Verification before packaging:

- 335 Python checks pass, zero failures/skips; 78% statement coverage, 42.09s.
- 20 existing microphone/PCM/VAD Node checks pass; JS syntax and Ruff pass.
- New tests cover ciphertext-at-rest, category/length/expiry validation, profile
  isolation, archive preservation, stale-session rejection, backup round-trip,
  rejected malformed backup and rollback, memory-off without decryption, no
  transcript persistence, bounded RAM, expiry on both voice paths and six-turn
  Live context renewal. All provider traffic is mocked; no real keys are used.
- Isolated browser QA passes card CRUD, expiry default, review-before-save,
  persistence across page reload, twelve-row UI cap, no disk transcripts and no
  automatic archive restoration. Synthetic mic QA confirms planned Live renewal
  reuses the already-open continuous microphone and blocks audio during the
  pause. No real microphone/audio/provider request is involved in these checks.

App version: `1.2.1+companionlite.11`; policy revision: 8. No paid cloud listening
test, clean Windows 10/11 acceptance or public release is claimed. Windows build
and in-place update evidence will be appended after verification.
