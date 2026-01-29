"""Report generation service - integrates with chm_report_automation pipeline."""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import yaml

logger = logging.getLogger(__name__)

# Path to the report automation package - use environment variable for flexibility
REPORT_AUTOMATION_PATH = Path(
    os.environ.get("REPORT_AUTOMATION_PATH", "/home/ubuntu/chm_report_automation")
)
# Use /app/reports inside container to avoid permission issues with /tmp
REPORTS_OUTPUT_DIR = Path(os.environ.get("REPORTS_OUTPUT_DIR", "/app/reports"))


def ensure_reports_dir():
    """Ensure reports output directory exists. Called lazily to avoid permission issues at import time."""
    try:
        REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to user's temp directory
        fallback = Path(tempfile.gettempdir()) / "chm_mediahub_reports"
        fallback.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Could not create {REPORTS_OUTPUT_DIR}, using fallback: {fallback}")
        return fallback
    return REPORTS_OUTPUT_DIR

# In-memory progress storage (shared with routers)
_job_progress: dict[str, dict] = {}


class ReportService:
    """Service for generating reports using the CHM report automation pipeline."""

    @staticmethod
    def create_config_file(
        event_name: str,
        event_date: str,
        transcript_path: Path,
        survey_path: Path,
        output_dir: Path,
    ) -> Path:
        """Create a YAML config file for the report pipeline."""
        # Format date for display (e.g., "January 21, 2026")
        from datetime import datetime
        try:
            date_obj = datetime.strptime(event_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except ValueError:
            formatted_date = event_date

        config = {
            "event": {
                "title": event_name,
                "subtitle": "Webinar Recap",
                "speakers": "",  # Will be extracted from transcript
                "date": formatted_date,
                "time": "",
                "location": "Virtual Webinar",
                "client": "Community Health Media",
                "report_date": datetime.now().strftime("%B %d, %Y"),
            },
            "kols": [],  # Will be extracted from transcript
            "branding": {
                "primary_color": "#1e3a5f",
                "secondary_color": "#4a90a4",
                "logo_path": None,
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
            },
            "survey_mapping": {
                "metadata_cols": [0, 1, 2, 3, 4],
                "question_start_col": 5,
            },
            "inputs": {
                "transcript_path": str(transcript_path),
                "survey_path": str(survey_path),
                "template_path": None,
            },
            "outputs": {
                "output_path": str(output_dir / f"{event_name.replace(' ', '_')}_report.pptx"),
            },
        }

        config_path = output_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        return config_path

    @staticmethod
    def get_progress(job_id: str) -> Optional[dict]:
        """Get current progress for a job."""
        return _job_progress.get(job_id)

    @staticmethod
    def set_progress(job_id: str, progress: dict):
        """Update progress for a job."""
        _job_progress[job_id] = progress

    @staticmethod
    def clear_progress(job_id: str):
        """Clear progress data for a job."""
        _job_progress.pop(job_id, None)

    @staticmethod
    async def run_pipeline(
        job_id: str,
        event_name: str,
        event_date: str,
        transcript_path: str,
        survey_path: str,
        on_status_update: Optional[Callable] = None,
    ) -> dict:
        """
        Run the report generation pipeline.

        Returns a dict with status, output_path or error.
        """
        reports_base = ensure_reports_dir()
        output_dir = reports_base / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize progress
        start_time = time.time()
        initial_progress = {
            "job_id": job_id,
            "stage": "upload",
            "stage_name": "Starting",
            "stage_description": "Initializing report generation",
            "progress": 0,
            "elapsed_seconds": 0,
            "stages_completed": [],
            "status": "processing",
            "error": None,
        }
        ReportService.set_progress(job_id, initial_progress)

        try:
            # Create config file
            config_path = ReportService.create_config_file(
                event_name=event_name,
                event_date=event_date,
                transcript_path=Path(transcript_path),
                survey_path=Path(survey_path),
                output_dir=output_dir,
            )

            if on_status_update:
                await on_status_update("processing", "Starting report generation...")

            # Run the pipeline as a subprocess with progress output
            # The pipeline will output JSON progress updates to stdout
            process = await asyncio.create_subprocess_exec(
                "python", "-m", "src.pipeline_runner",
                str(config_path), job_id,
                cwd=str(REPORT_AUTOMATION_PATH),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Read progress updates as they come in
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if line_str.startswith('{"'):  # JSON progress update
                    try:
                        progress_data = json.loads(line_str)
                        progress_data["elapsed_seconds"] = round(time.time() - start_time, 1)
                        ReportService.set_progress(job_id, progress_data)
                    except json.JSONDecodeError:
                        pass
                else:
                    logger.debug(f"Pipeline output: {line_str}")

            await process.wait()

            if process.returncode == 0:
                # Find the output file
                output_files = list(output_dir.glob("*.pptx"))
                if output_files:
                    output_path = output_files[0]
                    # Mark as completed
                    final_progress = ReportService.get_progress(job_id) or {}
                    final_progress.update({
                        "status": "completed",
                        "progress": 100,
                        "stage": "completed",
                        "stage_name": "Complete",
                        "stage_description": "Report generated successfully",
                        "elapsed_seconds": round(time.time() - start_time, 1),
                    })
                    ReportService.set_progress(job_id, final_progress)
                    return {
                        "status": "completed",
                        "output_path": str(output_path),
                        "message": "Report generated successfully",
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "Pipeline completed but no output file found",
                    }
            else:
                stderr_content = await process.stderr.read()
                error_msg = stderr_content.decode() if stderr_content else "Unknown error"
                logger.error(f"Pipeline failed: {error_msg}")
                # Mark as failed
                fail_progress = ReportService.get_progress(job_id) or {}
                fail_progress.update({
                    "status": "failed",
                    "error": error_msg[:500],
                })
                ReportService.set_progress(job_id, fail_progress)
                return {
                    "status": "failed",
                    "error": error_msg[:500],  # Truncate long errors
                }

        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            # Mark as failed
            fail_progress = ReportService.get_progress(job_id) or {}
            fail_progress.update({
                "status": "failed",
                "error": str(e),
            })
            ReportService.set_progress(job_id, fail_progress)
            return {
                "status": "failed",
                "error": str(e),
            }

    @staticmethod
    def validate_files(transcript_path: str, survey_path: str) -> tuple[bool, str]:
        """Validate that input files exist and are readable."""
        transcript = Path(transcript_path)
        survey = Path(survey_path)

        if not transcript.exists():
            return False, f"Transcript file not found: {transcript_path}"
        if not survey.exists():
            return False, f"Survey file not found: {survey_path}"

        # Check file sizes (sanity check)
        if transcript.stat().st_size == 0:
            return False, "Transcript file is empty"
        if survey.stat().st_size == 0:
            return False, "Survey file is empty"

        return True, "Files validated successfully"
