# Companion Lite

Personal Windows voice companion and English practice fork of ThirtyTutors,
using the existing Python/FastAPI/pywebview and Gemini Live speech-to-speech core.
Friend and Teacher modes support Vietnamese–English conversation. The 3D avatar,
asset downloader and upstream auto-update paths have been removed.

This is a private QA preview. Automated and mocked tests do not establish live
voice quality or clean Windows acceptance. See [Windows instructions](README_WINDOWS.md),
[QA report](docs/QA_REPORT.md), and [release notes](RELEASE_NOTES.md).

Development repository: https://github.com/zakuze01/thirtytutors

Original project: https://github.com/wiss84/thirtytutors

LICENSE remains PolyForm Noncommercial 1.0.0. Personal/noncommercial use only.

Required Notice: Copyright 2026 Wissam Metawee (https://github.com/wiss84/thirtytutors)

Build and testing instructions are in README_WINDOWS.md. No workflow publishes to
PyPI or GitHub Releases. Gemini requires the user's own API key and sends audio
and selected context to Google; local storage is not an offline AI service.
