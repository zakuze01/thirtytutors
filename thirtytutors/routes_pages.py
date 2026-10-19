"""Single voice-first UI, with redirects for older desktop/profile links."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter()


@router.get("/")
async def serve_learning_page():
    return FileResponse(Path(__file__).parent / "static" / "companion.html")


@router.get("/landing")
@router.get("/profiles")
@router.get("/get-started")
async def legacy_page():
    return RedirectResponse("/")
