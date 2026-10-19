import hashlib
import importlib.metadata as md
import json
import platform
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[2]
dist = root / "dist"
installer = dist / "CompanionLite-Preview-Setup.exe"
bundle = dist / "CompanionLite"
for file in bundle.rglob("*"):
    if file.is_file():
        name = file.name.lower()
        if name.endswith((".glb", ".mp4", ".wav")) or any(
            x in name for x in ("torch", "resemblyzer", "talkinghead", "headaudio")
        ):
            raise SystemExit("Forbidden bundle asset/dependency: " + name)
        if re.search(rb"AIza[0-9A-Za-z_-]{35}|\bsk-[0-9a-fA-F]{32,64}\b", file.read_bytes()):
            raise SystemExit("Potential credential detected; artifact withheld")
sha = hashlib.sha256(installer.read_bytes()).hexdigest()
manifest = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
    "build_date_utc": datetime.now(UTC).isoformat(),
    "python": platform.python_version(),
    "platform": platform.platform(),
    "sdk_version": md.version("google-genai"),
    "dependencies": {d.metadata["Name"]: d.version for d in md.distributions()},
    "installer": installer.name,
    "installer_sha256": sha,
    "installer_bytes": installer.stat().st_size,
    "bundle_bytes": sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file()),
    "secret_scan": "PASS (Google/DeepSeek key patterns and no runtime data bundled)",
    "acceptance": "PRIVATE QA PREVIEW — live Gemini/DeepSeek and clean Windows 10/11 acceptance outstanding",
}
(dist / "build_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(dist / "SHA256SUMS.txt").write_text(sha + "  " + installer.name + "\n", encoding="utf-8")
print(
    json.dumps(
        {k: manifest[k] for k in ("source_commit", "source_dirty", "installer_bytes", "bundle_bytes", "installer_sha256")},
        indent=2,
    )
)
