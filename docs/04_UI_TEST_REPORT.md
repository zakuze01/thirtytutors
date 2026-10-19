# M4 — voice-first UI/settings

Automated: 250 passed, 0 failed, 0 skipped; 75% coverage. `ruff check .` and
`ruff format --check .` pass (76 files formatted); JS syntax check passes.
Native pywebview smoke opens/closes with the reserved loopback socket and authenticated
bootstrap; process lifetime 12.21 seconds with a 12-second close timer. This is not
a startup latency measurement. See m4-native-smoke.log and m4-ui.png.

Browser QA used an isolated synthetic profile on loopback; `tests/browser_mock.js`
was injected before reload. It substitutes WebSocket and microphone with a generated
MediaStream, so no real microphone/Google calls took place. Observed checks:

| Check | Result |
|---|---|
| Initial page microphone requests | PASS: 0 |
| Profile creation, new conversation/history | PASS, local REST |
| Save Teacher while disconnected | PASS, REST config persisted teacher/memory off |
| Add user-confirmed Conversation memory | PASS, displayed saved synthetic topic |
| PTT synthetic input | PASS: start_turn, PCM chunks, turn_complete |
| Mic indication/track release | PASS: on while held, off after release; all tracks ended |
| Permission resolves after release | PASS: tracks stopped, no turn started |
| Permission denied | PASS: mic stays off, understandable error |
| Stop audio | PASS: 1 queued silent PCM source -> 0 |
| Console | PASS: no errors in exercised flows |
| Keyboard Tab focus | PASS: focus-visible, solid 3px outline |
| Responsive layout | PASS: no horizontal overflow at 1440/720/effective 500 CSS px |
| Network inventory | PASS: local page/assets/REST only, no avatar/marketing requests |

Native Windows 125/150/200% display scaling, real device permissions/audio, and
model conversational quality remain INCONCLUSIVE. Viewport resizing is not native
OS DPI validation. Mocked transport is not live Gemini acceptance.

Added profile editing/key replacement without echoing the stored key, microphone
and speaker selection (speaker output depends on WebView2 support), memory CRUD,
local export/import/erase, transcript toggle, mute, online preview/review actions
initiated explicitly by the user. New profiles opt out of sending saved memory until
checked. History remains local and visible. Exact cloud speed is not promised.

Scheduled waveform animation stops at idle and respects reduced-motion preference.
Primary text contrast is 11.32:1, secondary 5.67:1, mic label 6.54:1 against their
declared backgrounds (WCAG relative-luminance calculation). Buttons/focus are large
and keyboard-visible; this is not a complete assistive-technology audit.

Final asset audit removed previously overlooked root tutorial videos and voice
backgrounds. Static bundle now contains five files, 287,875 bytes at measurement;
Windows icon and PCM worklet retained. Native shell reserves its own socket before
opening the URL, rejects external binds, and refuses an occupied explicit port.
