"""Operator-controlled M2 import, review, publication, and quarantine endpoints."""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.auth import require_csrf, require_session
from socrat.database import record_event
from socrat.models import (
    ContentOperator,
    PackItemQuarantine,
    PackQuarantine,
    PackReview,
    PackVersion,
)
from socrat.skill_packs import (
    PackManifest,
    manifest_digest,
    verified_manifest,
    verify_concept_migration,
)

REVIEW_ROLES = {
    "domain_reviewer",
    "learning_reviewer",
    "accessibility_reviewer",
    "rights_reviewer",
    "language_reviewer",
    "assessment_reviewer",
}
CORE_REVIEWS = {
    "domain_reviewer",
    "learning_reviewer",
    "accessibility_reviewer",
    "rights_reviewer",
}


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str
    decision: str
    note: str = Field(min_length=10, max_length=1000)


class QuarantineInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=10, max_length=500)


def operator(db: Session, request: Request, role: str) -> str:
    session = require_session(request, db)
    require_csrf(request, session)
    if db.get(ContentOperator, (session.user_id, role)) is None:
        raise HTTPException(403, "content_role_required")
    return session.user_id


def get_version(db: Session, version_id: str) -> PackVersion:
    version = db.get(PackVersion, version_id)
    if version is None:
        raise HTTPException(404, "not_found")
    return version


def public_view(version: PackVersion) -> dict:
    manifest = verified_manifest(version)
    return {
        "key": version.pack_key,
        "version": version.version,
        "name": manifest.name,
        "domain": manifest.domain,
        "tracks": sorted({cell.track for cell in manifest.coverage if cell.status == "released"})
        if manifest.contract_version == 2
        else [track.key for track in manifest.track_policies],
        "languages": sorted(
            {
                cell.language
                for cell in manifest.coverage
                if cell.status == "released" and cell.language
            }
        )
        if manifest.contract_version == 2
        else [adapter.language for adapter in manifest.language_adapters],
        "coverage": [cell.model_dump() for cell in manifest.coverage]
        if manifest.contract_version == 2
        else [],
        "digest": version.digest,
    }


def required_reviews(manifest: PackManifest) -> set[str]:
    roles = set(CORE_REVIEWS)
    if manifest.language_adapters:
        roles.add("language_reviewer")
    if manifest.assessment_blueprints or any(
        item.kind == "assessment" for item in manifest.content
    ):
        roles.add("assessment_reviewer")
    return roles


def verify_reviews(db: Session, version: PackVersion) -> None:
    reviews = db.scalars(select(PackReview).where(PackReview.version_id == version.id)).all()
    if any(review.decision == "reject" for review in reviews):
        raise HTTPException(409, "content_review_rejected")
    approved = {review.role for review in reviews if review.decision == "approve"}
    if not required_reviews(PackManifest.model_validate(version.manifest)) <= approved:
        raise HTTPException(409, "content_reviews_incomplete")


def previous_good_release(db: Session, version: PackVersion) -> PackVersion | None:
    """Follow the recorded active-release chain, skipping quarantined versions."""
    seen = {version.id}
    predecessor_id = version.previous_active_id
    while predecessor_id is not None:
        if predecessor_id in seen:
            raise HTTPException(409, "release_history_invalid")
        seen.add(predecessor_id)
        predecessor = db.get(PackVersion, predecessor_id)
        if predecessor is None or predecessor.pack_key != version.pack_key:
            raise HTTPException(409, "release_history_invalid")
        if predecessor.status == "released":
            return predecessor
        predecessor_id = predecessor.previous_active_id
    return None


def register_skill_pack_routes(app: FastAPI) -> None:
    engine = app.state.engine

    @app.get("/api/v1/admin/content-roles")
    def own_content_roles(request: Request):
        with Session(engine) as db:
            session = require_session(request, db)
            roles = db.scalars(
                select(ContentOperator.role).where(ContentOperator.user_id == session.user_id)
            ).all()
            return {"roles": sorted(roles)}

    @app.get("/api/v1/admin/skill-packs")
    def operator_inventory(request: Request):
        with Session(engine) as db:
            session = require_session(request, db)
            if not db.scalar(
                select(ContentOperator.role).where(ContentOperator.user_id == session.user_id)
            ):
                raise HTTPException(403, "content_role_required")
            versions = db.scalars(select(PackVersion).order_by(PackVersion.created_at.desc())).all()
            return [
                {
                    "id": version.id,
                    "key": version.pack_key,
                    "version": version.version,
                    "status": version.status,
                    "is_active": version.is_active,
                    "digest": version.digest,
                }
                for version in versions
            ]

    @app.get("/api/v1/skill-packs")
    def list_packs():
        with Session(engine) as db:
            versions = db.scalars(
                select(PackVersion).where(
                    PackVersion.is_active.is_(True), PackVersion.status == "released"
                )
            ).all()
            return [public_view(version) for version in versions]

    @app.get("/api/v1/skill-packs/{key}/versions/{version_name}")
    def pinned_pack(key: str, version_name: str):
        with Session(engine) as db:
            version = db.scalar(
                select(PackVersion).where(
                    PackVersion.pack_key == key,
                    PackVersion.version == version_name,
                    PackVersion.status == "released",
                )
            )
            if version is None:
                raise HTTPException(404, "not_found")
            return public_view(version)

    @app.post("/api/v1/admin/skill-packs", status_code=201)
    def import_pack(manifest: PackManifest, request: Request):
        with Session(engine) as db, db.begin():
            actor_id = operator(db, request, "author")
            existing = db.scalar(
                select(PackVersion.id).where(
                    PackVersion.pack_key == manifest.key, PackVersion.version == manifest.version
                )
            )
            if existing:
                raise HTTPException(409, "pack_version_exists")
            version = PackVersion(
                pack_key=manifest.key,
                version=manifest.version,
                digest=manifest_digest(manifest),
                manifest=manifest.model_dump(mode="json"),
                author_id=actor_id,
                status="draft",
                is_active=False,
            )
            db.add(version)
            db.flush()
            record_event(db, actor_id, "skill_pack.imported", version.id)
            return {"id": version.id, "digest": version.digest, "status": version.status}

    @app.get("/api/v1/admin/skill-packs/{version_id}")
    def inspect_pack(version_id: str, request: Request):
        with Session(engine) as db:
            session = require_session(request, db)
            if not db.scalar(
                select(ContentOperator.role).where(ContentOperator.user_id == session.user_id)
            ):
                raise HTTPException(403, "content_role_required")
            version = get_version(db, version_id)
            reviews = db.scalars(
                select(PackReview).where(PackReview.version_id == version.id)
            ).all()
            return {
                "id": version.id,
                "status": version.status,
                "digest": version.digest,
                "manifest": version.manifest,
                "required_reviews": sorted(
                    required_reviews(PackManifest.model_validate(version.manifest))
                ),
                "reviews": [
                    {
                        "role": review.role,
                        "decision": review.decision,
                        "note": review.note,
                        "reviewer_id": review.reviewer_id,
                        "created_at": review.created_at,
                    }
                    for review in reviews
                ],
            }

    @app.post("/api/v1/admin/skill-packs/{version_id}/reviews", status_code=201)
    def review_pack(version_id: str, body: ReviewInput, request: Request):
        if body.role not in REVIEW_ROLES or body.decision not in {"approve", "reject"}:
            raise HTTPException(422, "invalid_review")
        with Session(engine) as db, db.begin():
            actor_id = operator(db, request, body.role)
            version = get_version(db, version_id)
            if version.status != "draft":
                raise HTTPException(409, "pack_not_draft")
            if actor_id == version.author_id:
                raise HTTPException(403, "author_cannot_review")
            existing = db.scalar(
                select(PackReview.id).where(
                    PackReview.version_id == version.id,
                    PackReview.reviewer_id == actor_id,
                    PackReview.role == body.role,
                )
            )
            if existing:
                raise HTTPException(409, "review_already_recorded")
            db.add(
                PackReview(
                    version_id=version.id,
                    reviewer_id=actor_id,
                    role=body.role,
                    decision=body.decision,
                    note=body.note,
                )
            )
            record_event(db, actor_id, "skill_pack.reviewed", version.id)
            return {"status": body.decision, "role": body.role}

    @app.post("/api/v1/admin/skill-packs/{version_id}/publish")
    def publish_pack(version_id: str, request: Request):
        with Session(engine) as db, db.begin():
            actor_id = operator(db, request, "release_owner")
            version = get_version(db, version_id)
            if version.status != "draft":
                raise HTTPException(409, "pack_not_draft")
            if actor_id == version.author_id:
                raise HTTPException(403, "author_cannot_publish")
            manifest = PackManifest.model_validate(version.manifest)
            if manifest.release_stage != "candidate":
                raise HTTPException(409, "pack_not_release_candidate")
            if manifest.contract_version != 2:
                raise HTTPException(409, "pack_contract_version_unsupported_for_release")
            verify_reviews(db, version)
            if manifest_digest(manifest) != version.digest:
                raise HTTPException(409, "pack_integrity_failed")
            active_versions = db.scalars(
                select(PackVersion).where(
                    PackVersion.pack_key == version.pack_key, PackVersion.is_active.is_(True)
                )
            ).all()
            if active_versions:
                try:
                    verify_concept_migration(verified_manifest(active_versions[0]), manifest)
                except ValueError as error:
                    raise HTTPException(409, "concept_migration_incomplete") from error
            version.previous_active_id = active_versions[0].id if active_versions else None
            for active in active_versions:
                active.is_active = False
            db.flush()
            version.status = "released"
            version.is_active = True
            from socrat.models import now

            version.published_at = now()
            record_event(db, actor_id, "skill_pack.published", version.id)
            return {"status": version.status, "digest": version.digest}

    @app.post("/api/v1/admin/skill-packs/{version_id}/quarantine")
    def quarantine_pack(version_id: str, body: QuarantineInput, request: Request):
        with Session(engine) as db, db.begin():
            actor_id = operator(db, request, "release_owner")
            version = get_version(db, version_id)
            if version.status != "released":
                raise HTTPException(409, "pack_not_released")
            was_active = version.is_active
            fallback = None
            version.status = "quarantined"
            version.is_active = False
            db.add(PackQuarantine(version_id=version.id, reason=body.reason, actor_id=actor_id))
            db.flush()
            if was_active:
                fallback = previous_good_release(db, version)
                if fallback is not None:
                    fallback.is_active = True
                    record_event(db, actor_id, "skill_pack.rollback_activated", fallback.id)
            record_event(db, actor_id, "skill_pack.quarantined", version.id)
            return {
                "status": version.status,
                "active_version": fallback.version if was_active and fallback else None,
            }

    @app.post("/api/v1/admin/skill-packs/{version_id}/items/{item_key}/quarantine")
    def quarantine_item(version_id: str, item_key: str, body: QuarantineInput, request: Request):
        with Session(engine) as db, db.begin():
            actor_id = operator(db, request, "release_owner")
            version = get_version(db, version_id)
            if version.status != "released":
                raise HTTPException(409, "pack_not_released")
            manifest = PackManifest.model_validate(version.manifest)
            if item_key not in {item.key for item in manifest.content}:
                raise HTTPException(404, "not_found")
            exists = db.scalar(
                select(PackItemQuarantine.id).where(
                    PackItemQuarantine.version_id == version.id,
                    PackItemQuarantine.item_key == item_key,
                )
            )
            if exists:
                raise HTTPException(409, "item_already_quarantined")
            db.add(
                PackItemQuarantine(
                    version_id=version.id,
                    item_key=item_key,
                    reason=body.reason,
                    actor_id=actor_id,
                )
            )
            record_event(db, actor_id, "skill_pack.item_quarantined", version.id)
            return {"status": "quarantined", "item_key": item_key}
