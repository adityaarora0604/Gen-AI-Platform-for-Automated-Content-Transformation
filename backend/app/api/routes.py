"""HTTP API. Thin layer only: all business logic lives in the other modules. (Owner: Rishabh)"""
from typing import List

from fastapi import APIRouter, File, Query, Response, UploadFile
from pydantic import BaseModel

from app import jobs_store
from app.ai_service import client
from app.config import get_settings
from app.export.exporter import FORMATS, build_export
from app.generation.generator import run_transform
from app.ingestion.extractors import extract_text, validate_file
from app.prompt_templates.templates import HUMAN_REVIEW_NOTICE, OUTPUT_SPECS
from app.schemas import (
    AUDIENCES,
    AppError,
    DETAIL_LEVELS,
    LANGUAGES,
    OBJECTIVES,
    STYLES,
    TONES,
    TransformRequest,
    TransformResponse,
    UploadResponse,
)

router = APIRouter(prefix="/api")


class ExportItem(BaseModel):
    type: str
    label: str = ""
    content: str = ""


class ExportRequest(BaseModel):
    job_id: str = "edited"
    mode: str = "ai"
    format: str = "md"
    outputs: List[ExportItem]


@router.get("/health")
def health():
    s = get_settings()
    configured = s.llm_provider == "demo" or (s.llm_provider == "anthropic" and bool(s.anthropic_api_key))
    return {
        "status": "ok",
        "provider": s.llm_provider,
        "mode": "demo" if s.llm_provider == "demo" else "ai",
        "llm_configured": configured,
        "max_upload_mb": s.max_upload_mb,
        "human_review_notice": HUMAN_REVIEW_NOTICE,
    }


@router.get("/options")
def options():
    return {
        "output_types": [{"value": k, "label": v["label"]} for k, v in OUTPUT_SPECS.items()],
        "audiences": AUDIENCES,
        "tones": TONES,
        "languages": LANGUAGES,
        "detail_levels": DETAIL_LEVELS,
        "objectives": OBJECTIVES,
        "styles": STYLES,
        "export_formats": list(FORMATS),
    }


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)  # read one byte over the limit to detect oversize files
    validate_file(file.filename or "", data)
    text, file_type, truncated = extract_text(file.filename, data)
    return UploadResponse(
        filename=file.filename, file_type=file_type, char_count=len(text), text=text, truncated=truncated
    )


@router.post("/transform", response_model=TransformResponse)
def transform(req: TransformRequest):
    return run_transform(req)


def _job_or_404(job_id: str) -> dict:
    job = jobs_store.get_job(job_id)
    if not job:
        raise AppError(f"Job '{job_id}' was not found.", 404)
    return job


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = _job_or_404(job_id)
    result = job.get("result") or {}
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "mode": job["mode"],
        "created_at": job["created_at"],
        "completed_at": job["completed_at"],
        "source_chars": job["source_chars"],
        "output_types": job["output_types"],
        "settings": job["settings"],
        "errors": result.get("errors", []),
        "metadata": result.get("metadata", {}),
    }


@router.get("/jobs/{job_id}/outputs")
def job_outputs(job_id: str):
    job = _job_or_404(job_id)
    if job["status"] == "running":
        raise AppError("The job is still running.", 409)
    return job["result"] or {}


@router.get("/jobs/{job_id}/export")
def job_export(job_id: str, format: str = Query("md")):
    job = _job_or_404(job_id)
    result = job.get("result") or {}
    outputs = [o for o in result.get("outputs", []) if o.get("status") == "completed"]
    data, filename, media = build_export(job_id, outputs, job["mode"], format)
    return Response(content=data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/export")
def export_edited(req: ExportRequest):
    """Export the (possibly user-edited) outputs sent by the frontend."""
    outputs = [o.model_dump() for o in req.outputs]
    data, filename, media = build_export(req.job_id, outputs, req.mode, req.format)
    return Response(content=data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
