"""Record licenses from the actual build environment, including Python."""

import importlib.metadata as md
import json
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
output = root / "build/licenses"
output.mkdir(parents=True, exist_ok=True)
inventory = []
for dist in md.distributions():
    name = dist.metadata.get("Name", "unknown")
    files = []
    for file in dist.files or []:
        if any(word in str(file).lower() for word in ("license", "notice", "copying", "copyright")):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size < 2_000_000:
                target = output / name / str(file).replace("../", "").replace("..\\", "")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                files.append(str(target.relative_to(output)))
    inventory.append(
        {"name": name, "version": dist.version, "license_expression": dist.metadata.get("License-Expression"), "files": files}
    )
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, output / "PYTHON_LICENSE.txt")
(output / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
