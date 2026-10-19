# Companion Lite — Windows private QA preview

Personal, noncommercial fork of ThirtyTutors. This preview is not a completed V1
acceptance or a public release. See docs/QA_REPORT.md for evidence and open gates.

Windows 10/11 x64, Microsoft Edge WebView2 Evergreen Runtime and a microphone/speaker
are required. Run the installer as your normal user; it installs under
`%LOCALAPPDATA%\Programs\CompanionLite`. Unsigned builds can trigger SmartScreen.
Uninstall preserves data by default; its interactive prompt offers explicit deletion.

Open Companion Lite, enter a nickname and your own Gemini API key in Settings.
Choose voice, difficulty and devices, save, then choose Connect / Retry. Hold the
large mic button or Space to speak; release to stop capture. Stop audio/Escape clears
playback. Friend is the default; Teacher, correction and reply-language preferences
can change in the same conversation via controlled provider reconnect.

For playful first English practice, choose Bạn bè, Việt–Anh tự nhiên and Mới tập
nói. These are the defaults for new conversations/profiles in preview 2. Existing
saved preferences remain unchanged: select the new language/level explicitly and
save Settings, then reconnect. The companion uses short Vietnamese bridges and
small English phrases, with occasional gentle humor; actual speech quality still
requires live testing. This level does not assume the user's age.

Preview 3 adds Độ nhây > Nhây hài and Luyện nói > Luyện đến khi rõ. With corrections
enabled (Gentle or Active), AI models one short target and asks for retries until
the wording is understandable. Say 'bỏ qua' or 'dừng luyện' to leave practice.
Off disables corrections/retries. Actual assessment follows Gemini's observations,
not a guaranteed pronunciation score.

For hands-free conversation, connect then click Bật nghe liên tục once. The mic
stays on between turns; local sound detection opens a turn and 800 ms of silence
closes it. Speaking during playback stops queued AI audio. Click Tắt mic or press
Escape to stop capture (Escape also stops audio). Changing windows, opening Settings,
disconnect/reconnect and permission/device loss stop capture; explicitly enable it
again afterward. It never turns on at startup or reconnect by itself. Set Độ nhạy
nghe for the room. Nearby voices/noise can trigger this energy detector; it does
not identify speakers. Use headphones if speaker echo causes unwanted interruption.
No continuous recording is saved. Speech segments and a short local pre-roll are
sent to Google when detected. Real device/echo/barge-in quality still needs live QA.

The app does not promise exact speech-rate control or transcript-based pronunciation
scores. Real model/voice quality still needs live acceptance. Voice preview is online,
user initiated and uses your quota. No avatar, video or speaker-model downloads occur.

Transcript/history and memory are local in `%LOCALAPPDATA%\CompanionLite`. Streaming
audio and minimum selected context go to Google Gemini when connected. This is not
an offline AI. No raw audio is stored by default, no third-party analytics run, and
API keys are encrypted with current-user Windows DPAPI. Enable the memory checkbox
only if you consent to sending saved memory as context. You can edit/delete explicit
Conversation/Learning memories or erase all profile history/memory from the sidebar.
Exported backups are independent files; keep them private. New exports contain no key.

To migrate from ThirtyTutors, export that profile's ZIP in the original app, then
import it here. The original app directory is untouched. An existing target profile
gets an encrypted recovery snapshot before overwrite. Legacy plaintext keys migrate
to DPAPI; on another Windows account/machine enter a new key. With the app closed,
source installs can restore a recovery snapshot using
`python -m thirtytutors.profile_recovery ABSOLUTE_SNAPSHOT_PATH`.

If mic permission is denied, enable Windows Settings > Privacy & security > Microphone
and desktop app access, then retry. Select the intended device explicitly. Speaker
selection requires WebView2 support; otherwise use Windows sound settings. For Gemini
errors verify the key's API access/quota and the configured model. Retry keeps the
conversation; no latency or provider availability is guaranteed. Do not paste keys
into chat/transcripts or diagnostic reports.

Build locally: create a clean Python 3.13 x64 venv; install
`packaging/windows/requirements-build.lock.txt`, then `pip install -e . --no-deps`.
Run `python packaging/windows/prepare_licenses.py`, then
`python packaging/windows/prepare_local_tts.py` (downloads pinned official
eSpeak NG CLI/data and complete corresponding source into build/), then
`pyinstaller packaging/windows/CompanionLite.spec --noconfirm`.
Compile `packaging/windows/installer.nsi` with the NSIS compiler. No publication step
exists. Preserve build manifest/checksum and complete live/clean-Windows QA before
any distribution. Review bundled third-party/DLL terms before sharing.

LICENSE is PolyForm Noncommercial 1.0.0.
Required Notice: Copyright 2026 Wissam Metawee (https://github.com/wiss84/thirtytutors)
# DeepSeek + Gemini voice (preview 4)

Trong **Cài đặt / Profile**, chọn **DeepSeek trả lời + Gemini nghe/đọc**, nhập cả
Gemini API key và DeepSeek API key, rồi Lưu và Kết nối. Key để trống giữ bản đã lưu;
hai key được mã hóa riêng bằng Windows DPAPI. Google nhận âm thanh và lời đáp để
đọc; DeepSeek nhận transcript và ngữ cảnh bạn cho phép. Luồng ba bước có thể chậm
hơn Live và không bảo đảm miễn phí. Gemini Live vẫn là lựa chọn mặc định.
Xem `docs/08_DEEPSEEK_VOICE_REPORT.md` để biết giới hạn và bằng chứng kiểm thử.

# Groq + giọng offline (preview 8)

Cài đặt / Profile → **Groq nghe/trả lời + giọng offline** → nhập **Groq API key**
→ Lưu → Kết nối → bật mic. Không cần Gemini key cho chế độ này. Dùng nút **Thử
giọng offline · không gọi API** để nghe mẫu Việt–Anh trước. Giọng eSpeak NG có âm
sắc máy, không tương đương giọng Gemini. Phần nghe/trả lời vẫn cần mạng đến Groq.

Groq chỉ miễn phí trong hạn mức tài khoản Free; app không xác minh được gói tài
khoản. Key thuộc gói Developer có thể bị tính phí ngay. Snapshot quota từ header
API không phải số dư tiền và không dự báo được mọi giới hạn audio/giây/phút.
HTTP 429/402 dừng yêu cầu, tắt mic và hiện cảnh báo. Chỉ bấm **Chuyển sang Gemini ·
CÓ TÍNH PHÍ** nếu muốn dùng key Gemini đã lưu. Không tự chuyển, không tự gửi lại
lượt lỗi, không tự bật mic. Retry là thao tác thử Groq lại; app không nâng cấp gói.

**Cập nhật preview 9:** nút dự phòng trên được thay bằng **DeepSeek trả lời +
giọng offline · CÓ TÍNH PHÍ**, chỉ xuất hiện khi Groq hết quota **chat**. Cần lưu
DeepSeek key trong Cài đặt. Sau khi bấm, Groq vẫn nghe, DeepSeek trả lời, máy đọc
offline; không gọi Gemini. Nếu Groq hết quota **nghe**, app dừng và yêu cầu chờ
quota phục hồi; DeepSeek không thay được STT. Có thể chọn trực tiếp **Groq nghe +
DeepSeek trả lời (tính phí) + giọng offline**. Đổi nhà cung cấp vẫn giữ lịch sử,
nhưng không tự gửi lại lượt lỗi hay tự bật mic.

Groq key được mã hóa riêng bằng DPAPI và loại khỏi backup portable. Giọng offline
được tạo trong RAM bằng chương trình CLI độc lập eSpeak NG 1.52.0 (GPL-3.0-or-later).
License, thông báo và toàn bộ source tương ứng nằm trong `_internal/offline-tts/`
của bản cài. Đây là thành phần riêng; license nguồn Companion Lite giữ nguyên.
Xem `docs/12_GROQ_OFFLINE_REPORT.md` để biết giới hạn và kết quả kiểm thử.
