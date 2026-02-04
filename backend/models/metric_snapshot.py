"""MetricSnapshot model - stores account-level metrics over time for trend analysis."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class MetricSnapshot(Base):
    """Point-in-time snapshot of an account-level metric.

    Append-only table. One row per metric per sync cycle.
    Enables "you gained X followers this week" insights and growth charts.
    """

    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<MetricSnapshot {self.platform}.{self.metric_name}={self.metric_value}>"
