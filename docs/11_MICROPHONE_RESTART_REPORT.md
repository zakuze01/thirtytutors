# Preview 7 — microphone selection after restart

The installed preview 6 reproduced the user's report: the Live connection was
ready but continuous capture failed with a generic microphone error. Refreshing
devices requested WebView permission for the new loopback origin. After Allow
and reselecting the physical Realtek input, continuous capture opened and its
local meter showed live input (-36 dBFS in the accessibility capture). Capture
was stopped with Escape during development. No private transcript is evidence
for this report or included in Git.

The desktop listener deliberately uses a new ephemeral port per launch.
Saved browser device IDs are origin-specific, as specified in the
[Media Capture specification](https://w3c.github.io/mediacapture-main/#dom-mediadeviceinfo-deviceid).
Passing a previous origin's ID as an exact constraint can therefore fail before
permission is requested. This explains the observed recovery path; the old UI
discarded the actual exception name, so its precise original DOMException was
not recorded. Windows global microphone permissions were not changed this turn.

## Change

- Retry only a saved-ID NotFoundError/OverconstrainedError. Request a permission
  probe, immediately stop it without connecting it to any audio processing or
  provider, enumerate devices, and open the unique exact saved label.
- An absent/ambiguous label fails with instructions to select a device. Never
  silently relay a different/default microphone. Permission denial and busy
  devices are not retried. Permission remains under WebView/Windows control.
- Cancellation is checked after each await; all late streams are stopped.
  Blur, Escape, disconnect and explicit cancel still stop capture, with no rearm.
- Pending capture says Hủy mở mic and aria-pressed=false. It only says Tắt mic
  and aria-pressed=true after capture is active. First-time permission prompts
  can move focus; if focus loss cancels capture, the user must click again after
  Allow. The pending status explains this.
- Listing devices preserves the selected microphone by ID or unique exact label
  and clears old errors on success. The current capture's refreshed ID updates
  the selector; a future launch can recover again from the saved label.
- Permission, unavailable device and busy-device failures have separate messages;
  no browser exception details, identifiers or credentials are logged.

## Verification before packaging

- 298 Python tests pass, zero failures/skips, 76% coverage, 39.62 s.
- 20 Node tests pass: 10 VAD and 10 microphone cases covering stale IDs,
  missing/duplicate labels, denied/busy errors, and cancellation during every
  asynchronous capture stage, including late final streams.
- Isolated mocked browser: startup makes zero mic calls; stale ID opens the
  expected new ID in three calls, probe is stopped, UI shows active capture;
  Escape stops all tracks. Pending permission shows cancellation state and
  false pressed state; cancel followed by a late grant leaves capture off.
  Denial displays the permission-specific message without raw exception details.
- New JavaScript module is served by the authenticated static route.
- JavaScript syntax and Ruff checks pass. These checks use synthetic media and
  do not establish real speech recognition, echo cancellation or cloud latency.

## Windows verification

Clean build source: `cb3afe1c258aa8ca87484d4f03cd4d3589555849`.
PyInstaller and NSIS exited 0. Isolated frozen UI loaded with mic off in 5.215 s,
then exited 0. Installer size: 34,078,651 bytes; SHA-256:
`00ecc6835eb46cb217d6cfa5803003a506dbb7f1950ba2ce63a1b6b1bc5bc593`.
Forbidden asset/dependency and credential-pattern scans passed.

After normal application shutdown, a DPAPI encrypted local rollback was created.
In-place per-user installation exited 0. All five application data files matched
their pre-update hashes before restart. Installed EXE and all four relevant
static files matched the tested bundle/source.

The installed app was launched at a new loopback origin and connected to Gemini.
Its continuous-listening button now reached the permission prompt directly,
without manually refreshing the device list. The permission popup caused blur
and safely cancelled the pending request, as expected. After Allow and a second
explicit click, capture opened the saved physical Realtek input without opening
settings/reselecting devices. The UI showed Micro đang bật · nghe liên tục,
Tắt mic, Realtek's track label and a live changing input meter (-54 dBFS in one
accessibility capture; -46 dBFS in the corresponding screenshot). Escape was
used to stop capture after the check. This confirms actual device acquisition
after restart, not speech recognition accuracy or echo quality. A new-origin
permission prompt and second click after focus loss remain possible.

Only redacted test/build results are committed. No private data snapshot,
credential or transcript is included. No public release or installer upload was
performed. Clean-machine Windows 10/11 acceptance remains outstanding.
