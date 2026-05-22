import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models.db import Base, utcnow


class CanvasSyncMode(str, enum.Enum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class CanvasConnection(Base):
    __tablename__ = "canvas_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    canvas_domain = Column(String(255), nullable=False)
    canvas_token_encrypted = Column(Text, nullable=False)
    canvas_course_id = Column(Integer, nullable=False)

    sync_mode = Column(Enum(CanvasSyncMode, name="canvas_sync_mode"), default=CanvasSyncMode.POLLING, nullable=False)
    webhook_subscription_id = Column(String(255), nullable=True)
    webhook_compatible = Column(String(16), nullable=True)  # "true" | "false" | null=unchecked

    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    course = relationship("Course", back_populates="canvas_connection")
