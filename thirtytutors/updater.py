"""Compatibility surface. Lite has no automatic update or asset downloads."""

from .constants import APP_VERSION


def installed_app_version():
    return APP_VERSION


def check_app_update():
    return {"update_available": False, "disabled": True, "installed_version": APP_VERSION}


def check_assets_update():
    return {"update_available": False, "disabled": True}


check_marketing_assets_update = check_assets_update


def run_pip_upgrade():
    return False, "Automatic updates are disabled in Companion Lite."


def download_and_extract_assets(*args, **kwargs):
    raise RuntimeError("Asset downloads are disabled in Companion Lite.")


download_and_extract_marketing_assets = download_and_extract_assets


def get_download_progress():
    return {"filename": None, "downloaded": 0, "total": None}


def relaunch_app():
    raise RuntimeError("Close and reopen Companion Lite manually.")


def close_this_window():
    return False


def check_whats_new():
    return {"available": False}


def mark_version_seen(version):
    pass


def render_release_notes_html(version):
    return None


def list_release_versions():
    return []
