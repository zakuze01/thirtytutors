# Preview 5 — quiet/fragmented speech onset and microphone diagnostics

Reported: continuous listening misses speech; push-to-talk displays Spanish text
although the requested conversation is Vietnamese/English. The user confirmed
using the Realtek 3.5 mm microphone. The installed controller hash matched preview
4. Windows microphone/device/desktop permissions were already enabled. Earlier
UI inspection showed Realtek as default input and GS3 as default output.

After restarting, actual application Settings showed its saved input was
**Communications - Microphone (GS3)**, overriding the Windows default. This is a
confirmed device-selection mismatch with the user's stated Realtek microphone.
The profile was changed to the explicit **Microphone (Realtek(R) Audio)** device
and saved through the UI. The local WebView2 microphone permission was also
accepted under the user's request. The wrong input could contribute to missed or
incorrect transcription; acoustic and recognition quality still need a spoken test.

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

The automated/synthetic tests recorded no real voice, saved no raw audio, and made
no paid provider call. Separately, interactive setup reconnected the installed app
to Gemini under the user's existing voice request. After saving the explicit
Realtek device and enabling continuous capture, the native UI reported the actual
Realtek track, microphone on, detected speech being sent, and PCM levels around
-22 to -17 dBFS. Physical input and local turn onset are therefore observed working;
this does not verify recognition of particular words. Echo, Vietnamese/English
recognition and conversational quality remain **INCONCLUSIVE**.
This patch does not claim the Spanish-transcript issue is resolved.

## Windows build and in-place update

Build source `4c6dfa65ace7f243d15f94f3ce226cfd06f3c34d` was clean at manifest
generation. PyInstaller/NSIS succeeded. Installer: 34,071,726 bytes, SHA-256
`edeeaaeabfe665cc19198f5cf02578a77bc1eab3651ab764635f5e32e1a53c30`.
The frozen UI loaded in 4.82 seconds with mic off and exited 0 in isolated storage.
Credential-pattern/forbidden-asset scan passed.

The existing installed app was closed normally, allowing graceful shutdown to
finish. Before update, a local current-user DPAPI-encrypted rollback was created.
The per-user installer exited 0. All 5 application data files (108,614 bytes total)
matched pre-update hashes byte-for-byte before reopening. Installed HTML,
controller and speech gate matched the tested source. Profile/history were visible
after restart. One agent-started hidden duplicate with no user session was cleaned
up; the installed application was reopened visibly using Computer Use. No data
snapshot, real credentials, profile identifiers or transcripts were committed or
uploaded. Evidence contains only counts, synthetic QA and build metadata.
