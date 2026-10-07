"""Scrub a restored database before granting learner traffic. IDs stay private."""

import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from socrat.accountability.privacy import erase  # noqa: E402
from socrat.auth import token_hash  # noqa: E402
from socrat.config import DatabaseSettings  # noqa: E402
from socrat.database import make_engine  # noqa: E402
from socrat.models import PrivacyRequest, User, identifier, now  # noqa: E402


def reapply(engine, user_ids):
    count = 0
    with Session(engine) as db, db.begin():
        for user_id in sorted(set(user_ids)):
            if db.get(User, user_id) is None:
                continue
            request = db.scalar(select(PrivacyRequest).where(PrivacyRequest.target_user_id == user_id))
            if request is None:
                request = PrivacyRequest(id=identifier(), target_user_id=user_id,
                    token_hash=token_hash(secrets.token_urlsafe(48)), status="queued",
                    tasks={"database": "pending", "backups_replicas_logs": "pending",
                           "provider": "pending", "shared_editorial_lineage": "not_applicable"},
                    cleanup_context={"user_id": user_id, "restored_copy": True},
                    created_at=now(), deadline_at=now())
                db.add(request)
                db.flush()
            erase(db, request, now())
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.private_manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, list) or any(not isinstance(x, str) or len(x) != 36 for x in manifest):
        raise ValueError("Expected a private JSON array of learner UUIDs")
    engine = make_engine(DatabaseSettings().database_url_value)
    try:
        count = reapply(engine, manifest)
        print(json.dumps({"erased_records": count}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
