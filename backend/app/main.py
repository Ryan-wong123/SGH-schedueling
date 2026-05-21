from __future__ import annotations

from pathlib import Path
import sys
from tempfile import gettempdir

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


def _frontend_dist_dir() -> Path | None:
    bundled_root = getattr(sys, "_MEIPASS", None)
    candidates = []
    if bundled_root:
        candidates.append(Path(bundled_root) / "frontend_dist")
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")

    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    return None


def create_app() -> FastAPI:
    app = FastAPI(title="GLF Assessment Scheduler")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.downloads = {}
    output_dir = Path(gettempdir()) / "glf-assessment-scheduler"
    output_dir.mkdir(parents=True, exist_ok=True)
    app.state.output_dir = output_dir
    app.include_router(router)

    frontend_dist = _frontend_dist_dir()
    if frontend_dist is not None:
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def serve_frontend(path: str):
            requested_file = frontend_dist / path
            if path and requested_file.is_file():
                return FileResponse(requested_file)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
