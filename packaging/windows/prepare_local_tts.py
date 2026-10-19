"""Stage unmodified eSpeak NG CLI and corresponding source as a separate tool."""

import hashlib
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cache = root / "build/offline-downloads"
cache.mkdir(parents=True, exist_ok=True)
assets = {
    "espeak-ng.msi": (
        "https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi",
        "7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9",
    ),
    "espeak-ng-1.52.0-source.tar.gz": (
        "https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz",
        "bb4338102ff3b49a81423da8a1a158b420124b055b60fa76cfb4b18677130a23",
    ),
}
for name, (url, digest) in assets.items():
    path = cache / name
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit("Offline speech asset hash mismatch: " + name)
extracted = cache / "extracted"
if not (extracted / "eSpeak NG/espeak-ng.exe").exists():
    result = subprocess.run(
        ["msiexec.exe", "/a", str(cache / "espeak-ng.msi"), "/qn", "TARGETDIR=" + str(extracted)],
        timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise SystemExit("Offline speech extraction failed")
output = root / "build/offline-tts"
shutil.copytree(extracted / "eSpeak NG", output, dirs_exist_ok=True)
source = cache / "espeak-ng-1.52.0-source.tar.gz"
shutil.copy2(source, output / source.name)
with tarfile.open(source) as archive:
    for name in ("COPYING", "COPYING.APACHE", "COPYING.BSD2", "COPYING.UCD", "README.md"):
        member = archive.getmember("espeak-ng-1.52.0/" + name)
        with archive.extractfile(member) as incoming:
            (output / name).write_bytes(incoming.read())
(output / "COMPANION-NOTICE.txt").write_text(
    "Unmodified eSpeak NG 1.52.0, a separate GPL-3.0-or-later command-line program.\n"
    "Copyright: see README and source files. License: COPYING and COPYING.*. Complete corresponding\n"
    "source, build instructions and scripts: espeak-ng-1.52.0-source.tar.gz.\n"
    "Invoked via standard stdin/WAV stdout; no DLL linking from Companion Lite.\n"
    "Upstream: https://github.com/espeak-ng/espeak-ng/releases/tag/1.52.0\n",
    encoding="utf-8",
)
print("Staged offline Vietnamese/English CLI, license and full corresponding source.")
