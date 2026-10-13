"""Review queue for drafted judge problems.

Drafts are YAML files under ``<drafts>/<course>/<id>.yaml`` on an authoring checkout.
A reviewer runs the quality gates, reads the statement, solutions and hints, and then:

- approves: the gates must not fail on the current file. The review (who, when, notes)
  is written into the YAML, the file moves to ``<courses>/<course>/problems/`` and the
  problem is added to its first concept's ``problems`` list, ready to commit and build;
- requests changes: a note is kept next to the draft for its author.

Every decision is also an audit event. Nothing here touches the running catalog: approved
problems ship through a commit, the content build and a deploy.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from fastapi import HTTPException

from socrat.catalog import validate
from socrat.catalog.registry import CONTENT_ROOT, Catalog

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Roots:
    drafts: Path
    courses: Path

    @classmethod
    def from_settings(cls, settings) -> "Roots":
        courses = (
            Path(settings.content_courses_dir) if settings.content_courses_dir else CONTENT_ROOT
        )
        drafts = (
            Path(settings.content_drafts_dir)
            if settings.content_drafts_dir
            else courses.parent / "drafts"
        )
        return cls(drafts=drafts, courses=courses)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar(path: Path, kind: str) -> Path:
    return path.with_name(f"{path.stem}.{kind}.json")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _find(roots: Roots, draft_id: str) -> Path:
    if not SLUG.match(draft_id):
        raise HTTPException(404, "not_found")
    matches = sorted(roots.drafts.glob(f"*/{draft_id}.yaml")) if roots.drafts.exists() else []
    if not matches:
        raise HTTPException(404, "not_found")
    return matches[0]


def _load(path: Path) -> dict:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raw = None
    return raw if isinstance(raw, dict) else {}


def _status(path: Path) -> tuple[str, dict | None, dict | None]:
    """(status, validation, review) where validation is only trusted for the current file."""
    validation = _read_json(_sidecar(path, "validation"))
    if validation and validation.get("digest") != _digest(path):
        validation = None  # the draft changed since it was validated
    review = _read_json(_sidecar(path, "review"))
    if review and review.get("digest") == _digest(path):
        return "changes_requested", validation, review
    if validation is None:
        return "needs_validation", None, review
    return ("failing" if validation["verdict"] == "fail" else "ready"), validation, review


def summary(roots: Roots, path: Path) -> dict:
    raw = _load(path)
    status, validation, review = _status(path)
    return dict(
        id=path.stem,
        course=path.parent.name,
        title=raw.get("title", path.stem),
        difficulty=raw.get("difficulty"),
        concepts=raw.get("concepts", []),
        status=status,
        verdict=validation["verdict"] if validation else None,
        review=review,
        updated_at=int(path.stat().st_mtime),
    )


def queue(roots: Roots) -> dict:
    paths = sorted(roots.drafts.glob("*/*.yaml")) if roots.drafts.exists() else []
    items = [summary(roots, p) for p in paths]
    order = {"ready": 0, "needs_validation": 1, "failing": 2, "changes_requested": 3}
    items.sort(key=lambda d: (order[d["status"]], -d["updated_at"]))
    return dict(enabled=roots.drafts.exists(), items=items)


def detail(roots: Roots, draft_id: str) -> dict:
    path = _find(roots, draft_id)
    raw = _load(path)
    status, validation, review = _status(path)
    shown = {
        k: raw.get(k)
        for k in (
            "title",
            "concepts",
            "difficulty",
            "statement",
            "input_format",
            "output_format",
            "constraints",
            "examples",
            "hints",
            "approach",
            "reference",
            "brute",
            "time_limit_ms",
        )
    }
    drafted = _read_json(_sidecar(path, "draft"))  # written by draft_problem.py
    statement = next(
        (g for g in (drafted or {}).get("gates", []) if g["name"] == "statement"), None
    )
    return dict(
        id=path.stem,
        course=path.parent.name,
        status=status,
        problem=shown,
        validation=validation,
        review=review,
        drafted=dict(
            model=drafted.get("model"), idea=drafted.get("idea"), statement_check=statement
        )
        if drafted
        else None,
    )


def run_validation(roots: Roots, catalog: Catalog, draft_id: str) -> dict:
    path = _find(roots, draft_id)
    drafts = {p.stem: _load(p).get("statement", "") for p in roots.drafts.glob("*/*.yaml")}
    result = validate.validate_file(
        path,
        catalog,
        strict=True,
        titles=validate.library_titles(),
        statements=validate.statements_of(catalog, drafts),
    )
    record = dict(digest=_digest(path), verdict=result["verdict"], gates=result["gates"])
    _sidecar(path, "validation").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return detail(roots, draft_id)


def _link_concept(courses: Path, course: str, concept: str, problem_id: str) -> None:
    path = courses / course / "concepts" / f"{concept}.yaml"
    if not path.exists():
        raise HTTPException(422, "unknown_concept")
    text = path.read_text(encoding="utf-8")
    line = re.search(r"^problems: \[(.*)\]$", text, flags=re.MULTILINE)
    if line:
        ids = [i.strip() for i in line.group(1).split(",") if i.strip()]
        if problem_id not in ids:
            ids.append(problem_id)
        text = text[: line.start()] + f"problems: [{', '.join(ids)}]" + text[line.end() :]
    elif re.search(r"^problems:", text, flags=re.MULTILINE):
        raise HTTPException(422, "concept_problems_not_inline")  # keep edits predictable
    else:
        text = text.rstrip("\n") + f"\nproblems: [{problem_id}]\n"
    path.write_text(text, encoding="utf-8")


def approve(roots: Roots, draft_id: str, reviewer: str, notes: str) -> dict:
    path = _find(roots, draft_id)
    status, validation, _ = _status(path)
    if validation is None:
        raise HTTPException(409, "validate_first")
    if status == "failing":
        raise HTTPException(409, "gates_failing")
    raw = _load(path)
    course = path.parent.name
    target = roots.courses / course / "problems" / f"{draft_id}.yaml"
    if target.exists():
        raise HTTPException(409, "problem_exists")
    concepts = raw.get("concepts") or []
    if not concepts:
        raise HTTPException(422, "no_concept")
    _link_concept(roots.courses, course, concepts[0], draft_id)
    review = dict(by=reviewer, at=date.today().isoformat(), notes=notes)
    text = path.read_text(encoding="utf-8").rstrip("\n")
    text += "\n" + yaml.safe_dump({"review": review}, sort_keys=False, allow_unicode=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    path.unlink()
    for kind in ("validation", "review", "draft"):
        _sidecar(path, kind).unlink(missing_ok=True)
    return dict(id=draft_id, course=course, path=str(target), review=review)


def request_changes(roots: Roots, draft_id: str, reviewer: str, notes: str) -> dict:
    path = _find(roots, draft_id)
    if not notes.strip():
        raise HTTPException(422, "notes_required")
    review = dict(
        decision="changes_requested",
        by=reviewer,
        at=date.today().isoformat(),
        notes=notes.strip(),
        digest=_digest(path),
    )
    _sidecar(path, "review").write_text(json.dumps(review, indent=2), encoding="utf-8")
    return detail(roots, draft_id)
