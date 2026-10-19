# M5 — Windows packaging and local QA

Private QA preview. V1 and clean Windows 10/11 acceptance are not complete.

## Build and automated verification

- Source packaging: 34d3364, 8a5b48e, 3075450 and 4d66651; fork branch
  `companion-lite/m0-audit`. Upstream was not modified.
- Host Windows 11 build 26100, x64; Python 3.13.4; google-genai 1.70.0;
  PyInstaller 6.22.3; NSIS 3.12. Clean `.venv-build` has no system-site inheritance.
- `pip check`: no broken requirements. Locked build dependencies committed.
- Final pytest: **250 passed, 0 failed, 0 skipped, 74% coverage**, 32.55 seconds.
  `ruff check .` and `ruff format --check .` passed (82 Python files formatted).
- PyInstaller onedir and NSIS compilation succeeded. Final NSIS output has no
  warnings. SDK tests and pytest are excluded from the frozen app, along with ML,
  avatar/rendering stacks and tracing. License inventory/notices are bundled.
- No live API request was made. Opt-in runner help/compilation were checked;
  provider transport, model access and actual voice remain INCONCLUSIVE.

The first frozen build started successfully. NSIS warnings exposed incorrect
uninstall-command quoting; fixed before final install. A later running-app uninstall
test exposed a real packaging defect: registry removal despite locked files. Fixed
by rejecting an install over a locked executable and checking removal errors before
touching registration. Final running-app install and uninstall both return exit 2,
preserving executable and registration (`m5-locked-installer.json`).

One restricted pytest run had 250 fixture setup errors because its default temp
directory was inaccessible. The exact failed log is preserved; successful final
run uses a dedicated QA temp directory in the current-user Windows context.

## Artifact and local installation

`dist/CompanionLite-Preview-Setup.exe`: **34,035,494 bytes**.

SHA256: `b18e6f655d2f7a263a5e266f5e104011f581f329f6b0db7a349cd4c9c3bd9d8e`

Installed application files: **92,605,755 bytes** (logical file lengths, not
filesystem allocation); this includes uninstaller and Windows instructions.
Installer runs per-user with `RequestExecutionLevel user`, fixed location
`%LOCALAPPDATA%\Programs\CompanionLite`. Current host already has WebView2.
No pre-existing installation was present before the initial QA install.

Installed EXE loads the native WebView2/local FastAPI page, title Companion Lite,
with microphone off. Initial build smoke and subsequent installed smoke returned
exit 0. Single observed page-loaded times are in the JSON logs; they are not a
cold/warm distribution or time-to-first-audible-response measurement.

Final installed smoke loaded in 5.855 seconds, mic off, and self-closed normally
after its 160-second test window. After closing, silent uninstall removed the EXE,
internal files, uninstaller and registration, preserving a synthetic marker in the
default data directory. Only that marker was then cleaned up. Actual user history
was never used. `m5-final-uninstall.json` captures the assertions. The interactive
delete-data option remains untested.

Idle measurement began 147.13 seconds after process launch, over two minutes after
the page loaded: seven app/WebView2 processes, **542,650,368 bytes working set
(517.51 MiB)**, **791,494,656 private bytes (754.83 MiB)**. CPU over a ten-second
sample was **0.088% of machine capacity**, normalized over 16 logical processors.
Working sets are summed, including potentially shared pages, not unique physical
RAM. No provider or mic was active. GPU was not measured. Exact process data is
in `m5-final-idle-performance.json`. This is one local sample, not a comparative
benchmark. WebView2 is still a substantial runtime cost after removing 3D.

An earlier 102.51-second sample was rejected for not meeting the two-minute
requirement. Its failed CloseMainWindow request led to testing the running-app
installer guard, then adding the bounded native self-closing smoke.

## Remaining gates

- Current host is a development machine. Windows 10, clean Windows 11, missing
  WebView2, interactive erase prompt, protected Program Files and native OS DPI
  scenarios are not exercised. Do not infer those from this per-user install.
- Physical mic/speaker selection, live interruption/reconnect, Vietnamese-English
  quality, twelve manual scenarios and 10–20 real audio latency turns are pending.
- No comparable original idle RAM/CPU/GPU measurement exists; GPU is pending.
  No efficiency percentage or latency guarantee is claimed.
- DLL redistribution notices and owner review remain required before sharing.
  Unsigned private preview may trigger SmartScreen. No public release/upload.
- Windows CI workflow exists but has not run on GitHub here. Local execution
  evidence is independent from that unexecuted workflow.

See `QA_REPORT.md`, `README_WINDOWS.md`, final build manifest and checksum.
