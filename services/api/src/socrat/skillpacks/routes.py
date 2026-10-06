"""Fail-closed editorial API and assessment-safe public catalogue."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.learning.audit import planning_audit
from socrat.learning.content import coverage_audit
from socrat.models import ContentReview, SkillPackHead, SkillPackVersion, User
from socrat.skillpacks.schema import Contract, Language, SkillPack
from socrat.skillpacks.service import PackError, import_pack, load, safe_manifest, transition

router = APIRouter(prefix="/api/v1")


class ReviewRequest(Contract):
    action: Literal[
        "technical_review",
        "learning_review",
        "language_verified",
        "staged",
        "publish",
        "activate",
        "quarantine",
        "retire",
    ]
    evidence_reference: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=2000)
    verified_languages: list[Language] = Field(default_factory=list, max_length=3)


def require_admin(request: Request, db: Session, write: bool = False) -> str:
    session = require_session(request, db)
    user = db.get(User, session.user_id)
    settings = request.app.state.settings
    if user is None or not any(
        identity.issuer == user.issuer and identity.subject == user.subject
        for identity in settings.content_admin_identities
    ):
        raise HTTPException(403, "content_admin_required")
    if write:
        if request.headers.get("origin") != settings.public_origin:
            raise HTTPException(403, "origin_rejected")
        require_csrf(request, session)
    return user.id


def record_view(record: SkillPackVersion) -> dict:
    return {
        "id": record.id,
        "key": record.pack_key,
        "version": record.version,
        "status": record.status,
        "digest": record.digest,
    }


@router.post("/admin/skill-packs", status_code=201)
def import_content(body: SkillPack, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            actor = require_admin(request, db, write=True)
            return record_view(import_pack(db, body, actor))
    except PackError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "concurrent_content_change") from exc


@router.get("/admin/skill-packs")
def admin_catalogue(request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        records = db.scalars(
            select(SkillPackVersion)
            .order_by(SkillPackVersion.pack_key, SkillPackVersion.version)
            .limit(1000)
        ).all()
        return {"items": [record_view(record) for record in records]}


@router.get("/admin/skill-packs/{key}/versions/{version}")
def admin_version(key: str, version: str, request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        record = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == key, SkillPackVersion.version == version
            )
        )
        if record is None:
            raise HTTPException(404, "pack_not_found")
        try:
            pack = load(record)
        except PackError as exc:
            raise HTTPException(exc.status, exc.code) from exc
        reviews = db.scalars(
            select(ContentReview)
            .where(ContentReview.version_id == record.id)
            .order_by(ContentReview.created_at, ContentReview.id)
        ).all()
        return {
            **record_view(record),
            "pack": pack.model_dump(mode="json"),
            "coverage": pack.coverage(),
            "learning_coverage": coverage_audit(pack),
            "topological_order": pack.topological_order(),
            "reviews": [
                {
                    "id": review.id,
                    "action": review.action,
                    "evidence_reference": review.evidence_reference,
                    "reason": review.reason,
                    "created_at": review.created_at,
                }
                for review in reviews
            ],
        }


@router.get("/admin/skill-packs/{key}/versions/{version}/learning-plan-audit")
def admin_learning_plan_audit(key: str, version: str, request: Request):
    with Session(request.app.state.engine) as db:
        require_admin(request, db)
        record = db.scalar(
            select(SkillPackVersion).where(
                SkillPackVersion.pack_key == key, SkillPackVersion.version == version
            )
        )
        if record is None:
            raise HTTPException(404, "pack_not_found")
        try:
            return planning_audit(load(record))
        except PackError as exc:
            raise HTTPException(exc.status, exc.code) from exc


@router.post("/admin/skill-packs/{key}/versions/{version}/actions")
def review_content(key: str, version: str, body: ReviewRequest, request: Request):
    try:
        with Session(request.app.state.engine) as db, db.begin():
            actor = require_admin(request, db, write=True)
            return record_view(
                transition(
                    db,
                    key,
                    version,
                    actor,
                    body.action,
                    body.evidence_reference,
                    body.reason,
                    body.verified_languages,
                )
            )
    except PackError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    except IntegrityError as exc:
        raise HTTPException(409, "concurrent_content_change") from exc


@router.get("/skill-packs")
def public_catalogue(request: Request):
    with Session(request.app.state.engine) as db:
        records = db.scalars(
            select(SkillPackVersion)
            .join(SkillPackHead, SkillPackHead.active_id == SkillPackVersion.id)
            .where(SkillPackVersion.status == "released")
            .order_by(SkillPackVersion.pack_key)
            .limit(1000)
        ).all()
        try:
            return {
                "items": [
                    safe_manifest(record) for record in records if load(record).purpose == "launch"
                ]
            }
        except PackError as exc:
            raise HTTPException(exc.status, exc.code) from exc
