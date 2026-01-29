"""Report generation job model."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.user import User


class JobStatus(str, enum.Enum):
    """Report job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportJob(Base):
    """Report generation job tracking."""

    __tablename__ = "report_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False
    )
    # Report configuration (event name, date, speakers, etc.)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # File paths
    transcript_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    survey_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", backref="report_jobs")

    def __repr__(self) -> str:
        return f"<ReportJob {self.id[:8]} ({self.status.value})>"
