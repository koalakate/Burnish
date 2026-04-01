import enum
import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.db.models.base import Base, TimestampMixin, UUIDMixin


class PlanType(enum.StrEnum):
    free = "free"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


class OrgRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    plan: Mapped[PlanType] = mapped_column(Enum(PlanType), default=PlanType.free)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255))
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole), default=OrgRole.editor)

    organization: Mapped["Organization"] = relationship(back_populates="users")
