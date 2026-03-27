import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class SourceType(enum.StrEnum):
    pptx = "pptx"
    gslides = "gslides"
    figma = "figma"
    pdf = "pdf"
    keynote = "keynote"


class Deck(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decks"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    source_ref: Mapped[str] = mapped_column(String(1024))
    slide_count: Mapped[int] = mapped_column(Integer, default=0)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_deck_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=True
    )
    csm_ref: Mapped[str] = mapped_column(String(1024), default="")
