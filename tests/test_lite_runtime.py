"""P0 boundaries: no 3D assets, auto-installer or speaker warmup."""

import asyncio
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from thirtytutors import main, speech_detection, updater
from thirtytutors.local_access import LAUNCH_TOKEN

ROOT = Path(__file__).parents[1]


def test_p0_distribution_has_no_3d_vendor_or_heavy_requirement():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not {"torch", "scipy", "librosa", "resemblyzer", "webrtcvad"}.intersection(config["project"]["dependencies"])
    static = ROOT / "thirtytutors" / "static"
    assert not (static / "vendor").exists()
    assert not list(static.rglob("*.glb"))
    assert not list(static.rglob("*.wav"))
    for file in static.glob("companion.*"):
        text = file.read_text(encoding="utf-8")
        assert all(term not in text for term in ("TalkingHead", "/avatar", "/marketing", "/photos", ".glb"))


def test_import_does_not_load_speaker_ml_stack():
    script = """
import importlib.abc, sys
class DenyML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','librosa','scipy','resemblyzer','webrtcvad'}:
            raise AssertionError('P0 imports ML stack: ' + fullname)
sys.meta_path.insert(0, DenyML())
import thirtytutors.main
import thirtytutors.cli
"""
    subprocess.run([sys.executable, "-c", script], check=True, cwd=ROOT, capture_output=True, timeout=30)


def test_startup_does_not_warm_up_speaker_model(monkeypatch):
    def forbidden():
        raise AssertionError("Speaker warmup must never run in P0")

    monkeypatch.setattr(speech_detection, "warm_up", forbidden)

    async def exercise():
        async with main.app.router.lifespan_context(main.app):
            await asyncio.sleep(0.05)

    asyncio.run(exercise())


def test_ui_and_voice_picker_work_without_external_assets():
    client = TestClient(main.app, base_url="http://127.0.0.1:8000", headers={"X-Companion-Token": LAUNCH_TOKEN})
    assert client.get("/").status_code == 200
    assert client.get("/companion.js").status_code == 200
    voices = client.get("/api/voices").json()["voices"]
    assert any(v["name"] == "Kore" for v in voices)
    assert client.get("/avatar/test.glb").status_code == 404
    assert client.get("/marketing/speaking.mp4").status_code == 404


def test_upstream_install_and_download_paths_are_disabled():
    assert updater.run_pip_upgrade()[0] is False
    assert updater.check_app_update()["disabled"]
    for fn in (updater.download_and_extract_assets, updater.download_and_extract_marketing_assets):
        with pytest.raises(RuntimeError, match="disabled"):
            fn()
