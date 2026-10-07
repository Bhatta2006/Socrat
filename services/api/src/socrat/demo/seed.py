"""Idempotent local demo seed. Does not import test fixtures or approve gates."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.config import Settings
from socrat.database import make_engine
from socrat.demo.content import validated_pack
from socrat.models import DemoClock, SkillPackHead, SkillPackVersion, User

PERSONAS = {
    "beginner": ("Beginner", "foundations", "python", "none"),
    "interview": ("Interview prep", "interview", "java", "professional"),
    "competitive": ("Competitive", "competitive", "cpp", "professional"),
}


def seed(settings: Settings) -> dict:
    if not settings.demo_mode or settings.environment != "development":
        raise ValueError("Demo seed requires explicit development demo mode")
    refs = {x["language"]: x["image"] for x in settings.execution_profiles}
    if set(refs) != {"python", "cpp", "java"}:
        raise ValueError("Build all three immutable demo runtimes before seeding")
    pack, audit = validated_pack(refs)
    engine = make_engine(settings.database_url_value)
    try:
        with Session(engine) as db, db.begin():
            author = db.scalar(
                select(User).where(
                    User.issuer == "local-development", User.subject == "demo-content-author"
                )
            )
            if author is None:
                author = User(
                    issuer="local-development",
                    subject="demo-content-author",
                    display_name="Demo content author",
                    adult_confirmed=True,
                )
                db.add(author)
                db.flush()
            existing = db.scalar(
                select(SkillPackVersion).where(
                    SkillPackVersion.pack_key == pack.key, SkillPackVersion.version == pack.version
                )
            )
            if existing is not None and existing.digest != pack.digest():
                raise ValueError(
                    "Demo runtime/content changed: use a new demo version or a fresh demo volume"
                )
            if existing is None:
                existing = SkillPackVersion(
                    pack_key=pack.key,
                    version=pack.version,
                    domain=pack.domain,
                    payload=json.loads(pack.canonical_json()),
                    digest=pack.digest(),
                    status="released",
                    author_id=author.id,
                )
                db.add(existing)
                db.flush()
            head = db.get(SkillPackHead, pack.key)
            if head is None:
                db.add(SkillPackHead(pack_key=pack.key, active_id=existing.id))
            else:
                head.active_id = existing.id
            if db.get(DemoClock, "demo") is None:
                db.add(DemoClock(id="demo", offset_seconds=0))
            for key, (name, _, _, _) in PERSONAS.items():
                if (
                    db.scalar(
                        select(User.id).where(
                            User.issuer == "local-development", User.subject == "demo-" + key
                        )
                    )
                    is None
                ):
                    db.add(
                        User(
                            issuer="local-development",
                            subject="demo-" + key,
                            display_name=name,
                            adult_confirmed=True,
                            timezone="Asia/Kolkata",
                        )
                    )
        return dict(
            pack_key=pack.key,
            digest=pack.digest(),
            concepts=len(pack.concepts),
            exercises=len(pack.exercises),
            planner_ready=audit["ready"],
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    print(json.dumps(seed(Settings())))
