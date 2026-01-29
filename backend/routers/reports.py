"""Reports router - handles report generation from transcripts and surveys."""

import asyncio
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from middleware.auth import require_roles
from models.user import User, UserRole
from services.report_service import ReportService
from services.redis_store import RedisStore

router = APIRouter(prefix="/reports", tags=["reports"])

# Directory for storing uploads and generated reports
UPLOADS_DIR = Path("/tmp/chm_mediahub/uploads")
REPORTS_DIR = Path("/tmp/chm_mediahub/reports")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class ReportRequest(BaseModel):
    """Request to generate a report."""
    event_name: str
    event_date: str
    transcript_file_id: str
    survey_file_id: str


class ReportJobResponse(BaseModel):
    """Report generation job status."""
    id: str
    event_name: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    completed_at: datetime | None = None
    output_file: str | None = None
    error: str | None = None


class UploadedFile(BaseModel):
    """Uploaded file info."""
    id: str
    original_name: str
    file_type: str
    uploaded_at: datetime


@router.post("/upload", response_model=UploadedFile)
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),  # "transcript" or "survey"
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Upload a transcript or survey file."""
    if file_type not in ("transcript", "survey"):
        raise HTTPException(status_code=400, detail="file_type must be 'transcript' or 'survey'")

    # Validate file extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if file_type == "transcript" and ext not in (".txt", ".vtt", ".srt", ".docx"):
        raise HTTPException(
            status_code=400,
            detail="Transcript must be .txt, .vtt, .srt, or .docx"
        )

    if file_type == "survey" and ext not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail="Survey must be .csv, .xlsx, or .xls"
        )

    # Generate unique file ID and save
    file_id = str(uuid.uuid4())
    save_path = UPLOADS_DIR / f"{file_id}{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Store metadata in Redis
    file_info = {
        "id": file_id,
        "original_name": filename,
        "file_type": file_type,
        "path": str(save_path),
        "uploaded_at": datetime.now(),
        "uploaded_by": current_user.id,
    }
    await RedisStore.save_file(file_id, file_info)

    return UploadedFile(
        id=file_id,
        original_name=filename,
        file_type=file_type,
        uploaded_at=file_info["uploaded_at"],
    )


@router.get("/uploads", response_model=list[UploadedFile])
async def list_uploads(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """List uploaded files."""
    files = await RedisStore.list_files()
    return [
        UploadedFile(
            id=f["id"],
            original_name=f["original_name"],
            file_type=f["file_type"],
            uploaded_at=f["uploaded_at"],
        )
        for f in files
    ]


async def run_report_pipeline(job_id: str):
    """Background task to run the report generation pipeline."""
    job = await RedisStore.get_job(job_id)
    if not job:
        return

    # Update status to processing
    await RedisStore.update_job(job_id, {"status": "processing", "started_at": datetime.now()})

    # Run the pipeline
    result = await ReportService.run_pipeline(
        job_id=job_id,
        event_name=job["event_name"],
        event_date=job["event_date"],
        transcript_path=job["transcript_path"],
        survey_path=job["survey_path"],
    )

    # Update job with result
    updates = {
        "status": result["status"],
        "completed_at": datetime.now(),
    }

    if result["status"] == "completed":
        updates["output_file"] = result.get("output_path")
    else:
        updates["error"] = result.get("error", "Unknown error")

    await RedisStore.update_job(job_id, updates)


@router.post("/generate", response_model=ReportJobResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Start report generation job."""
    # Validate files exist in Redis
    transcript_file = await RedisStore.get_file(request.transcript_file_id)
    survey_file = await RedisStore.get_file(request.survey_file_id)

    if not transcript_file:
        raise HTTPException(status_code=404, detail="Transcript file not found")
    if not survey_file:
        raise HTTPException(status_code=404, detail="Survey file not found")

    if transcript_file["file_type"] != "transcript":
        raise HTTPException(status_code=400, detail="transcript_file_id must point to a transcript file")
    if survey_file["file_type"] != "survey":
        raise HTTPException(status_code=400, detail="survey_file_id must point to a survey file")

    # Validate files exist on disk
    valid, message = ReportService.validate_files(
        transcript_file["path"],
        survey_file["path"]
    )
    if not valid:
        raise HTTPException(status_code=400, detail=message)

    # Create job
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "event_name": request.event_name,
        "event_date": request.event_date,
        "transcript_path": transcript_file["path"],
        "survey_path": survey_file["path"],
        "status": "pending",
        "created_at": datetime.now(),
        "completed_at": None,
        "output_file": None,
        "error": None,
        "created_by": current_user.id,
    }

    # Save to Redis
    await RedisStore.save_job(job_id, job)

    # Start background task to run the pipeline
    background_tasks.add_task(run_report_pipeline, job_id)

    return ReportJobResponse(
        id=job["id"],
        event_name=job["event_name"],
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        output_file=job["output_file"],
        error=job["error"],
    )


@router.get("/jobs", response_model=list[ReportJobResponse])
async def list_jobs(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """List report generation jobs for the current user."""
    jobs = await RedisStore.list_jobs()
    # Filter to only show jobs created by the current user
    user_jobs = [j for j in jobs if j.get("created_by") == str(current_user.id)]
    return [
        ReportJobResponse(
            id=j["id"],
            event_name=j["event_name"],
            status=j["status"],
            created_at=j["created_at"],
            completed_at=j.get("completed_at"),
            output_file=j.get("output_file"),
            error=j.get("error"),
        )
        for j in user_jobs
    ]


@router.get("/jobs/{job_id}", response_model=ReportJobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Get a specific report job status."""
    job = await RedisStore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ReportJobResponse(
        id=job["id"],
        event_name=job["event_name"],
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        output_file=job.get("output_file"),
        error=job.get("error"),
    )


@router.get("/jobs/{job_id}/download")
async def download_report(
    job_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Download the generated report."""
    job = await RedisStore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report not yet completed")

    if not job.get("output_file") or not Path(job["output_file"]).exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(
        job["output_file"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{job['event_name']}_report.pptx",
    )


@router.get("/jobs/{job_id}/progress")
async def stream_progress(
    job_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """
    Stream real-time progress updates via Server-Sent Events (SSE).

    Connect to this endpoint to receive live updates as a report is generated.
    Updates are sent approximately every 500ms.

    Event format:
    ```
    data: {"stage": "executive", "stage_name": "Executive Summary", "progress": 30, ...}
    ```
    """
    job = await RedisStore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        """Generate SSE events with progress updates."""
        last_progress = None

        while True:
            # Get current progress from service (or Redis)
            progress = ReportService.get_progress(job_id)

            # Also try Redis progress store
            if not progress:
                progress = await RedisStore.get_progress(job_id)

            # If no progress data yet, send a pending state
            if not progress:
                current_job = await RedisStore.get_job(job_id) or {}
                progress = {
                    "job_id": job_id,
                    "stage": "pending",
                    "stage_name": "Queued",
                    "stage_description": "Waiting to start...",
                    "progress": 0,
                    "elapsed_seconds": 0,
                    "stages_completed": [],
                    "status": current_job.get("status", "pending"),
                    "error": current_job.get("error"),
                }

            # Only send if changed
            if progress != last_progress:
                yield f"data: {json.dumps(progress)}\n\n"
                last_progress = progress.copy() if progress else None

            # Check if job is complete or failed
            status = progress.get("status", "")
            if status in ("completed", "failed"):
                break

            # Also check job status in case progress wasn't updated
            current_job = await RedisStore.get_job(job_id) or {}
            if current_job.get("status") in ("completed", "failed"):
                # Send final state from job
                final_data = {
                    "job_id": job_id,
                    "stage": "completed" if current_job["status"] == "completed" else "failed",
                    "stage_name": "Complete" if current_job["status"] == "completed" else "Failed",
                    "stage_description": current_job.get("error") or "Report generated successfully",
                    "progress": 100 if current_job["status"] == "completed" else progress.get("progress", 0),
                    "elapsed_seconds": progress.get("elapsed_seconds", 0),
                    "stages_completed": progress.get("stages_completed", []),
                    "status": current_job["status"],
                    "error": current_job.get("error"),
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                break

            await asyncio.sleep(0.5)  # 500ms refresh rate

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/jobs/{job_id}/status")
async def get_job_progress(
    job_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR)),
):
    """
    Get current progress status for a report job (polling endpoint).

    This is a simpler alternative to the SSE endpoint for clients that
    prefer polling over streaming.
    """
    job = await RedisStore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get current progress from service
    progress = ReportService.get_progress(job_id)

    # Also try Redis progress store
    if not progress:
        progress = await RedisStore.get_progress(job_id)

    # If no progress data yet, return based on job state
    if not progress:
        return {
            "job_id": job_id,
            "stage": job.get("status", "pending"),
            "stage_name": "Queued" if job.get("status") == "pending" else "Processing",
            "stage_description": job.get("error") or "Waiting to start...",
            "progress": 0 if job.get("status") == "pending" else 5,
            "elapsed_seconds": 0,
            "stages_completed": [],
            "status": job.get("status", "pending"),
            "error": job.get("error"),
        }

    return progress
