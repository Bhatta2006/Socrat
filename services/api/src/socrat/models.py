import time
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def identifier() -> str:
    return str(uuid.uuid4())


def now() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    adult_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    delivered_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class DeliveredEvent(Base):
    __tablename__ = "delivered_events"
    event_id: Mapped[str] = mapped_column(ForeignKey("outbox_events.id"), primary_key=True)
    delivered_at: Mapped[int] = mapped_column(Integer, default=now)


class ContentOperator(Base):
    __tablename__ = "content_operators"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(40), primary_key=True)


class PackVersion(Base):
    __tablename__ = "pack_versions"
    __table_args__ = (
        UniqueConstraint("pack_key", "version"),
        Index(
            "ux_pack_versions_active_key",
            "pack_key",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active = true"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    pack_key: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    digest: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    published_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_active_id: Mapped[str | None] = mapped_column(
        ForeignKey("pack_versions.id"), nullable=True
    )


class PackReview(Base):
    __tablename__ = "pack_reviews"
    __table_args__ = (UniqueConstraint("version_id", "role", "reviewer_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    version_id: Mapped[str] = mapped_column(ForeignKey("pack_versions.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(40))
    decision: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class PackQuarantine(Base):
    __tablename__ = "pack_quarantines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    version_id: Mapped[str] = mapped_column(ForeignKey("pack_versions.id"), index=True)
    reason: Mapped[str] = mapped_column(String(500))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class PackItemQuarantine(Base):
    __tablename__ = "pack_item_quarantines"
    __table_args__ = (UniqueConstraint("version_id", "item_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    version_id: Mapped[str] = mapped_column(ForeignKey("pack_versions.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(500))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[int] = mapped_column(Integer, default=now)
