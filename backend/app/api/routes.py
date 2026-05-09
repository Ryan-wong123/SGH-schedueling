from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from starlette.background import BackgroundTask
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.services.allocation_service import allocate_assessments, summarize_records
from app.services.excel_reader import load_glf_workbook_from_bytes, load_roster_workbook_from_bytes
from app.services.glf_parser import parse_glf_progress
from app.services.roster_parser import parse_roster
from app.services.workbook_writer import add_generated_allocation_sheet, save_workbook_to_bytes
from app.utils.errors import AppError

router = APIRouter()


def _cleanup_download(downloads: dict[str, Path], download_id: str, path: Path) -> None:
    downloads.pop(download_id, None)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _validate_xlsx(upload: UploadFile | None, label: str) -> None:
    if upload is None:
        raise AppError(f"Missing {label}.")
    if not upload.filename or Path(upload.filename).suffix.casefold() != ".xlsx":
        raise AppError(f"{label} must be an .xlsx file.")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/generate-allocation")
async def generate_allocation(
    request: Request,
    glf_workbook: UploadFile = File(...),
    roster_workbook: UploadFile = File(...),
    glf_password: str = Form(...),
):
    try:
        _validate_xlsx(glf_workbook, "GLF workbook")
        _validate_xlsx(roster_workbook, "Roster workbook")
        if not glf_password or not glf_password.strip():
            raise AppError("GLF workbook password is required.")

        glf_bytes = await glf_workbook.read()
        roster_bytes = await roster_workbook.read()
        glf = load_glf_workbook_from_bytes(glf_bytes, glf_password)
        roster = load_roster_workbook_from_bytes(roster_bytes)
        needs = parse_glf_progress(glf)
        roster_data = parse_roster(roster)
        records = allocate_assessments(needs, roster_data)
        add_generated_allocation_sheet(glf, records)
        output_bytes = save_workbook_to_bytes(glf)

        download_id = str(uuid4())
        downloads = request.app.state.downloads
        output_dir = request.app.state.output_dir
        output_path = output_dir / f"{download_id}.xlsx"
        output_path.write_bytes(output_bytes)
        downloads[download_id] = output_path

        return {
            "success": True,
            "summary": summarize_records(records),
            "records": [record.to_api_dict() for record in records[:500]],
            "download_id": download_id,
        }
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unexpected workbook processing failure.") from exc


@router.get("/api/download/{download_id}")
async def download_workbook(request: Request, download_id: str):
    path = request.app.state.downloads.get(download_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Generated workbook is no longer available.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="GLF_Assessment_Generated_Allocation.xlsx",
        background=BackgroundTask(_cleanup_download, request.app.state.downloads, download_id, path),
    )
