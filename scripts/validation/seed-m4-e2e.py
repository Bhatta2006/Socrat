"""Create isolated browser-test goals. Never activate this synthetic pack as launch coverage."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/api/tests")]

from m4_support import diagnostic_pack  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from test_onboarding import goal  # noqa: E402

from socrat.database import make_engine  # noqa: E402
from socrat.models import LearnerGoal, SkillPackHead, SkillPackVersion, User  # noqa: E402
from socrat.onboarding.policy import digest, route  # noqa: E402
from socrat.skillpacks.schema import SkillPack  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("track", choices=["foundations", "interview", "competitive"])
parser.add_argument("language", choices=["python", "cpp", "java"])
parser.add_argument("subject")
parser.add_argument("--planning", action="store_true")
args = parser.parse_args()
if not args.subject.startswith(("m4-e2e-", "m5-e2e-")) or not (ROOT / "socrat.e2e.db").is_file():
    parser.error("Requires an existing isolated browser database and m4-e2e subject")
payload = diagnostic_pack().model_dump()
if args.planning:
    from m5_support import planner_pack

    payload = planner_pack().model_dump()
    payload["version"] = "1.0.5"
payload["purpose"] = "launch"  # This copy exists only inside socrat.e2e.db.
for template in payload["goals"]:
    value = goal(template["id"])
    template["released_targets"] = [dict(outcome=value.target_outcome, value=value.target_value,
        role_level=value.role_level, platform_or_format=value.platform_or_format)]
pack = SkillPack.model_validate(payload)
engine = make_engine(f"sqlite:///{ROOT / 'socrat.e2e.db'}")
with Session(engine) as db, db.begin():
    user = db.scalar(select(User).where(User.issuer == "local-development", User.subject == args.subject))
    if user is None:
        user = User(issuer="local-development", subject=args.subject, display_name="Synthetic M4 learner", adult_confirmed=True)
        db.add(user)
        db.flush()
    record = db.scalar(select(SkillPackVersion).where(SkillPackVersion.pack_key == pack.key, SkillPackVersion.version == pack.version))
    if record is None:
        record = SkillPackVersion(pack_key=pack.key, version=pack.version, domain=pack.domain,
            payload=json.loads(pack.canonical_json()), digest=pack.digest(), status="released", author_id=user.id)
        db.add(record)
        db.flush()
    if db.get(SkillPackHead, pack.key) is None:
        db.add(SkillPackHead(pack_key=pack.key))  # No active head: inherited waitlist journeys stay isolated.
    value = goal(args.track, language=args.language)
    snapshot = route(value, True, [pack], date(2026, 10, 2))
    db.add(LearnerGoal(user_id=user.id, idempotency_key=args.subject,
        review_digest=digest({"user_id": user.id, "snapshot": snapshot}), snapshot=snapshot))
engine.dispose()
