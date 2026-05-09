from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="GLF Assessment Scheduler")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.downloads = {}
    output_dir = Path(gettempdir()) / "glf-assessment-scheduler"
    output_dir.mkdir(parents=True, exist_ok=True)
    app.state.output_dir = output_dir
    app.include_router(router)
    return app


app = create_app()
