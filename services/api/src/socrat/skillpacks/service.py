"""Transactional import/review/release authority. Callers own the transaction."""

import hmac
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.learning.content import coverage_audit
from socrat.models import ContentReview, SkillPackHead, SkillPackVersion
from socrat.skillpacks.schema import SkillPack

NEXT_STAGE = {
    "draft": "technical_review",
    "technical_review": "learning_review",
    "learning_review": "language_verified",
    "language_verified": "staged",
}


class PackError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code = code
        self.status = status


def load(record: SkillPackVersion) -> SkillPack:
    pack = SkillPack.model_validate(record.payload)
    if not hmac.compare_digest(pack.digest(), record.digest):
        raise PackError("pack_integrity_failed", 503)
    return pack


def import_pack(db: Session, pack: SkillPack, actor: str) -> SkillPackVersion:
    existing = db.scalar(
        select(SkillPackVersion).where(
            SkillPackVersion.pack_key == pack.key, SkillPackVersion.version == pack.version
        )
    )
    if existing:
        if existing.digest == pack.digest():
            return existing
        raise PackError("version_already_exists")
    versions = db.scalars(
        select(SkillPackVersion).where(SkillPackVersion.pack_key == pack.key)
    ).all()
    if any(item.domain != pack.domain or load(item).purpose != pack.purpose for item in versions):
        raise PackError("pack_identity_changed")
    if pack.migration:
        source = next(
            (item for item in versions if item.version == pack.migration.from_version), None
        )
        if source is None or not set(pack.migration.concept_mapping) <= {
            item.id for item in load(source).concepts
        }:
            raise PackError("invalid_migration_source", 422)
    if db.get(SkillPackHead, pack.key) is None:
        db.add(SkillPackHead(pack_key=pack.key))
    record = SkillPackVersion(
        pack_key=pack.key,
        version=pack.version,
        domain=pack.domain,
        payload=pack.model_dump(mode="json"),
        digest=pack.digest(),
        author_id=actor,
    )
    db.add(record)
    db.flush()
    record_event(db, actor, "content.imported", record.id)
    return record


def locked_version(db: Session, key: str, version: str):
    head = db.scalar(select(SkillPackHead).where(SkillPackHead.pack_key == key).with_for_update())
    record = db.scalar(
        select(SkillPackVersion).where(
            SkillPackVersion.pack_key == key, SkillPackVersion.version == version
        )
    )
    if head is None or record is None:
        raise PackError("pack_not_found", 404)
    load(record)
    return head, record


def transition(
    db: Session,
    key: str,
    version: str,
    actor: str,
    action: str,
    evidence: str,
    reason: str,
    verified_languages: Sequence[str],
) -> SkillPackVersion:
    head, record = locked_version(db, key, version)
    pack = load(record)
    if action in {"technical_review", "learning_review", "language_verified", "staged", "publish"}:
        if actor == record.author_id:
            raise PackError("independent_reviewer_required", 403)
        expected = "released" if action == "publish" else action
        if expected != ("released" if record.status == "staged" else NEXT_STAGE.get(record.status)):
            raise PackError("invalid_lifecycle_transition")
        if action == "language_verified" and set(verified_languages) != set(pack.languages):
            raise PackError("language_verification_incomplete", 422)
        if action == "publish":
            if (
                pack.purpose == "launch"
                and pack.session_content_version
                and not coverage_audit(pack)["ready"]
            ):
                raise PackError("learning_content_coverage_incomplete", 422)
            sources = [pack.provenance, *(item.provenance for item in pack.exercises)]
            if any(
                value.lower() in {"unknown", "unverified", "pending"}
                for source in sources
                for value in (source.license, source.source, source.rights_reference)
            ):
                raise PackError("unverified_content_rights", 422)
        record.status = expected
        if action == "publish":
            head.previous_id, head.active_id = head.active_id, record.id
    elif action == "activate":
        if record.status != "released":
            raise PackError("version_not_released")
        if head.active_id == record.id:
            return record
        head.previous_id, head.active_id = head.active_id, record.id
    elif action in {"quarantine", "retire"}:
        if record.status in {"quarantined", "retired"}:
            raise PackError("version_already_withdrawn")
        record.status = "quarantined" if action == "quarantine" else "retired"
        if head.active_id == record.id:
            previous = db.get(SkillPackVersion, head.previous_id) if head.previous_id else None
            if previous and previous.status == "released":
                load(previous)
                head.active_id = previous.id
            else:
                head.active_id = None
            head.previous_id = None
    else:
        raise PackError("unknown_content_action", 422)
    db.add(
        ContentReview(
            version_id=record.id,
            actor_id=actor,
            action=action,
            evidence_reference=evidence,
            reason=reason,
        )
    )
    record_event(db, actor, f"content.{action}", record.id)
    db.flush()
    return record


def safe_manifest(record: SkillPackVersion) -> dict:
    """No reference solutions, tests, assessment items, or private review data."""
    pack = load(record)
    return {
        "key": pack.key,
        "version": pack.version,
        "digest": record.digest,
        "title": pack.title,
        "domain": pack.domain,
        "languages": pack.languages,
        "concepts": [
            {"id": item.id, "title": item.title, "competency": item.competency}
            for item in pack.concepts
        ],
        "topological_order": pack.topological_order(),
        "practice_coverage": {
            key: value
            for key, value in pack.coverage().items()
            if next(item for item in pack.exercises if item.id == key).inventory == "practice"
        },
    }
