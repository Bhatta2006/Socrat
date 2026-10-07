"""Twelve-month raw code/tutor retention; derived evidence remains replayable."""

from typing import cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.orm import Session

from socrat.models import CodeDraft, CodeRun, CodeRunSource, TutorArtifact, TutorTurn

RAW_RETENTION_SECONDS = 365 * 86400


def prune_once(engine, stamp):
    cutoff = stamp - RAW_RETENTION_SECONDS
    with Session(engine) as db, db.begin():
        count = cast(
            CursorResult, db.execute(delete(CodeDraft).where(CodeDraft.updated_at < cutoff))
        ).rowcount
        count += cast(
            CursorResult,
            db.execute(
                delete(CodeRunSource).where(
                    CodeRunSource.run_id.in_(
                        select(CodeRun.id).where(
                            CodeRun.created_at < cutoff,
                            CodeRun.status.not_in(["queued", "running"]),
                        )
                    )
                )
            ),
        ).rowcount
        count += cast(
            CursorResult,
            db.execute(
                delete(TutorArtifact).where(
                    TutorArtifact.turn_id.in_(
                        select(TutorTurn.id).where(TutorTurn.created_at < cutoff)
                    )
                )
            ),
        ).rowcount
        return count
