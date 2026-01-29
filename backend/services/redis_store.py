"""Redis-based storage for report jobs and uploaded files.

This service provides persistent storage for:
- Report generation jobs (status, progress, results)
- Uploaded file metadata (transcript and survey files)

Data survives container restarts, unlike in-memory storage.
"""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from config import get_settings

settings = get_settings()

# Redis key prefixes
JOBS_PREFIX = "mediahub:jobs:"
FILES_PREFIX = "mediahub:files:"
PROGRESS_PREFIX = "mediahub:progress:"

# TTL for completed jobs (7 days)
COMPLETED_JOB_TTL = 60 * 60 * 24 * 7
# TTL for uploaded files metadata (24 hours)
FILE_TTL = 60 * 60 * 24


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO format datetime string."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class RedisStore:
    """Async Redis store for job and file data."""

    _pool: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis connection pool."""
        if cls._pool is None:
            cls._pool = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._pool

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None

    # --- Job Operations ---

    @classmethod
    async def save_job(cls, job_id: str, job_data: dict) -> None:
        """Save a report job to Redis."""
        client = await cls.get_client()
        key = f"{JOBS_PREFIX}{job_id}"
        data = json.dumps(job_data, cls=DateTimeEncoder)
        await client.set(key, data)

        # Add to sorted set for listing (sorted by created_at timestamp)
        created_at = job_data.get("created_at")
        if isinstance(created_at, datetime):
            score = created_at.timestamp()
        elif isinstance(created_at, str):
            score = parse_datetime(created_at).timestamp() if parse_datetime(created_at) else 0
        else:
            score = datetime.now().timestamp()

        await client.zadd("mediahub:jobs_list", {job_id: score})

    @classmethod
    async def get_job(cls, job_id: str) -> dict | None:
        """Get a report job from Redis."""
        client = await cls.get_client()
        key = f"{JOBS_PREFIX}{job_id}"
        data = await client.get(key)

        if data is None:
            return None

        job = json.loads(data)
        # Convert datetime strings back to datetime objects
        for field in ("created_at", "completed_at", "started_at"):
            if field in job and job[field]:
                job[field] = parse_datetime(job[field])

        return job

    @classmethod
    async def update_job(cls, job_id: str, updates: dict) -> dict | None:
        """Update specific fields of a job."""
        job = await cls.get_job(job_id)
        if job is None:
            return None

        job.update(updates)
        await cls.save_job(job_id, job)
        return job

    @classmethod
    async def list_jobs(cls, limit: int = 100) -> list[dict]:
        """List all jobs, newest first."""
        client = await cls.get_client()

        # Get job IDs from sorted set (newest first)
        job_ids = await client.zrevrange("mediahub:jobs_list", 0, limit - 1)

        jobs = []
        for job_id in job_ids:
            job = await cls.get_job(job_id)
            if job:
                jobs.append(job)

        return jobs

    @classmethod
    async def delete_job(cls, job_id: str) -> bool:
        """Delete a job from Redis."""
        client = await cls.get_client()
        key = f"{JOBS_PREFIX}{job_id}"

        # Remove from both the key and the sorted set
        await client.delete(key)
        await client.zrem("mediahub:jobs_list", job_id)
        await client.delete(f"{PROGRESS_PREFIX}{job_id}")

        return True

    # --- Progress Operations ---

    @classmethod
    async def save_progress(cls, job_id: str, progress_data: dict) -> None:
        """Save progress data for a job."""
        client = await cls.get_client()
        key = f"{PROGRESS_PREFIX}{job_id}"
        data = json.dumps(progress_data, cls=DateTimeEncoder)
        # Progress data expires after 1 hour (jobs should complete by then)
        await client.set(key, data, ex=3600)

    @classmethod
    async def get_progress(cls, job_id: str) -> dict | None:
        """Get progress data for a job."""
        client = await cls.get_client()
        key = f"{PROGRESS_PREFIX}{job_id}"
        data = await client.get(key)

        if data is None:
            return None

        return json.loads(data)

    # --- File Operations ---

    @classmethod
    async def save_file(cls, file_id: str, file_data: dict) -> None:
        """Save uploaded file metadata to Redis."""
        client = await cls.get_client()
        key = f"{FILES_PREFIX}{file_id}"
        data = json.dumps(file_data, cls=DateTimeEncoder)
        # Files metadata expires after 24 hours
        await client.set(key, data, ex=FILE_TTL)

        # Add to sorted set for listing
        uploaded_at = file_data.get("uploaded_at")
        if isinstance(uploaded_at, datetime):
            score = uploaded_at.timestamp()
        elif isinstance(uploaded_at, str):
            score = parse_datetime(uploaded_at).timestamp() if parse_datetime(uploaded_at) else 0
        else:
            score = datetime.now().timestamp()

        await client.zadd("mediahub:files_list", {file_id: score})
        # Also set expiry on the sorted set entry
        await client.expire("mediahub:files_list", FILE_TTL)

    @classmethod
    async def get_file(cls, file_id: str) -> dict | None:
        """Get uploaded file metadata from Redis."""
        client = await cls.get_client()
        key = f"{FILES_PREFIX}{file_id}"
        data = await client.get(key)

        if data is None:
            return None

        file_info = json.loads(data)
        if "uploaded_at" in file_info and file_info["uploaded_at"]:
            file_info["uploaded_at"] = parse_datetime(file_info["uploaded_at"])

        return file_info

    @classmethod
    async def list_files(cls, limit: int = 100) -> list[dict]:
        """List all uploaded files, newest first."""
        client = await cls.get_client()

        # Get file IDs from sorted set (newest first)
        file_ids = await client.zrevrange("mediahub:files_list", 0, limit - 1)

        files = []
        for file_id in file_ids:
            file_info = await cls.get_file(file_id)
            if file_info:
                files.append(file_info)

        return files

    @classmethod
    async def delete_file(cls, file_id: str) -> bool:
        """Delete file metadata from Redis."""
        client = await cls.get_client()
        key = f"{FILES_PREFIX}{file_id}"

        await client.delete(key)
        await client.zrem("mediahub:files_list", file_id)

        return True

    # --- Health Check ---

    @classmethod
    async def health_check(cls) -> bool:
        """Check if Redis is available."""
        try:
            client = await cls.get_client()
            await client.ping()
            return True
        except Exception:
            return False
