Script ran on page and returned:

Additional observed checks: startup microphone calls = 0; no console errors or
warnings; emulated viewport 500 CSS px has no horizontal overflow; queued audio
after a pending resume was canceled = 0. Microphone and audio are mocked throughout.
```json
{"voice":{"silentMessages":0,"interrupted":{"queuedBefore":1,"queuedAfter":0,"sourceStopped":true,"active":true},"endsDuringPause":0,"afterFirst":{"recording":true,"continuous":true,"active":false,"starts":1,"ends":1},"final":{"recording":false,"continuous":false,"mic":"Micro đang tắt","starts":2,"ends":2,"track":"ended","pressed":"false"}},"permission":{"late":{"recording":false,"continuous":false,"track":"ended","mic":"Micro đang tắt"},"denied":{"recording":false,"continuous":false,"mic":"Micro đang tắt","error":"Error · Không mở được micro. Kiểm tra quyền micro trong Windows rồi thử lại."}},"lifecycle":{"spaceKeepsListening":true,"blur":{"recording":false,"continuous":false,"track":"ended"},"reconnect":{"recording":false,"continuous":false,"track":"ended"},"drop":{"recording":false,"continuous":false,"micCallsUnchanged":true,"track":"ended","connected":true},"escape":{"recording":false,"continuous":false,"track":"ended"}},"persisted":{"practice":"repeat_until_clear","humor":"cheeky"}}
```
