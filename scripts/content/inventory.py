"""Content inventory export (CSV) with explicit rights and review for every record.

Ported from the one-off audit script that produced content-inventory.csv; record IDs and
columns are kept, plus the Content Master Plan Appendix B columns. Rights are never
guessed: a record states its recorded rights, the license of a matching entry in
content/sources/registry.yaml, or an explicit "unknown: ..." value.

Usage:
  python scripts/content/inventory.py [--out content-inventory.csv]
  python scripts/content/inventory.py --check     # fail if any rights/review cell is empty
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.registry import load  # noqa: E402
from socrat.catalog.sources import SourceEntry, SourceRegistry, load_registry  # noqa: E402

FIELDS = [
    "record_id",
    "asset_type",
    "course_ids",
    "module_ids",
    "concept_ids",
    "primary_concept",
    "title",
    "source_name",
    "source_url",
    "source_file",
    "source_revision",
    "storage",
    "difficulty",
    "languages",
    "word_count",
    "rights_or_license",
    "review_record",
    "details",
    "source_file_sha256",
    "pattern_ids",
    "band",
    "misconception_ids",
    "provenance_origin",
    "license_status",
    "last_verified_at",
]
NOT_RECORDED = "unknown: not recorded in the repository"
EXTERNAL_UNKNOWN = "unknown: external link, license not recorded"
NO_REVIEW = "none recorded"
PLATFORMS = {"LeetCode": "leetcode", "Codeforces": "codeforces", "CSES": "cses"}


def words(value: str) -> int:
    return len(re.findall(r"\S+", value))


def sections(lesson: str) -> list[dict]:
    """Markdown headings outside code fences, with the words each heading owns."""
    raw = lesson.splitlines()
    marks, fence = [], None
    for index, line in enumerate(raw):
        if match := re.match(r"^\s*(`{3,}|~{3,})", line):
            if fence is None:
                fence = match[1][0]
            elif match[1][0] == fence:
                fence = None
            continue
        if fence is None and (match := re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)):
            marks.append((index, len(match[1]), match[2]))
    result, path = [], []
    for number, (start, level, title) in enumerate(marks):
        own_end = marks[number + 1][0] if number + 1 < len(marks) else len(raw)
        whole_end = next((i for i, lvl, _ in marks[number + 1 :] if lvl <= level), len(raw))
        path = [(lvl, t) for lvl, t in path if lvl < level] + [(level, title)]
        result.append(
            dict(
                level=level,
                title=title,
                path=" > ".join(t for _, t in path),
                own_words=words("\n".join(raw[start + 1 : own_end])),
                inclusive_words=words("\n".join(raw[start + 1 : whole_end])),
            )
        )
    return result


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").removeprefix("www.")


class Rights:
    """Rights/licence lookups against the source registry."""

    def __init__(self, registry: SourceRegistry):
        self.registry = registry
        hosts: dict[str, list[SourceEntry]] = {}
        for entry in registry.sources:
            hosts.setdefault(host(str(entry.url)), []).append(entry)
        # Only hosts that identify exactly one source can be matched by URL.
        self.by_host = {h: entries[0] for h, entries in hosts.items() if len(entries) == 1}

    def entry(self, source_id: str | None = None, url: str = "") -> SourceEntry | None:
        if source_id:
            return self.registry.find(source_id)
        return self.by_host.get(host(url)) if url else None

    @staticmethod
    def columns(entry: SourceEntry | None, fallback: str) -> dict:
        if entry is None:
            return dict(rights_or_license=fallback, license_status="unknown", last_verified_at="")
        suffix = "" if entry.license_status == "verified" else " (unverified)"
        return dict(
            rights_or_license=entry.license + suffix,
            license_status=entry.license_status,
            last_verified_at=entry.last_verified_at or "",
        )


def local(provenance, review=None, rights=None) -> dict:
    """Rights/review columns for Socrat-authored records."""
    recorded = provenance.rights if provenance else rights
    reviewed = (provenance.review if provenance else None) or review
    return dict(
        rights_or_license=recorded or NOT_RECORDED,
        review_record=json.dumps(reviewed.model_dump()) if reviewed else NO_REVIEW,
        provenance_origin=provenance.origin if provenance else "not recorded",
        license_status="not applicable",
    )


def build_rows(root: Path = ROOT) -> list[dict]:
    content = root / "content"
    catalog = load(content / "courses", tests_root=None)
    rights = Rights(load_registry(content / "sources" / "registry.yaml"))
    hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(content.rglob("*"))
        if p.is_file()
    }
    practice = content / "practice"
    external = [
        json.loads(line)
        for line in (practice / "problems.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    implementations = [
        json.loads(line)
        for line in (practice / "implementations.jsonl").read_text("utf-8").splitlines()
        if line
    ]
    companies = json.loads((practice / "companies.json").read_text("utf-8"))
    book = json.loads((practice / "book.json").read_text("utf-8"))
    learning = json.loads((content / "learning-resources.json").read_text("utf-8"))
    snapshots = json.loads((practice / "sources.json").read_text("utf-8"))["snapshots"]
    taxonomy = set(yaml.safe_load((content / "atoms" / "misconceptions.yaml").read_text("utf-8")))
    tests_root = root / ".cache" / "content-tests"
    concepts = catalog.concepts
    rows: list[dict] = []

    def add(asset_type, ident, title, qs=(), source_file="", **values):
        qs = list(qs)
        modules = sorted({f"{q.split(':')[0]}:{concepts[q].module}" for q in qs if q in concepts})
        row = dict.fromkeys(FIELDS, "")
        row.update(
            record_id=f"{asset_type}:{ident}",
            asset_type=asset_type,
            title=title,
            course_ids=";".join(sorted({q.split(":")[0] for q in qs})),
            module_ids=";".join(modules),
            concept_ids=";".join(qs),
            primary_concept=qs[0] if qs else "",
            source_file=source_file,
            source_file_sha256=hashes.get(source_file, ""),
        )
        row.update(values)
        rows.append(row)

    def tests(problem_id: str, source_file: str) -> dict:
        path = tests_root / f"{problem_id}.json"
        if not path.exists():
            return dict(tests="not built")
        cases = json.loads(path.read_text("utf-8"))
        public = sum(bool(t["public"]) for t in cases)
        stamp = tests_root / f"{problem_id}.sha256"
        fresh = stamp.exists() and stamp.read_text().strip() == hashes.get(source_file)
        return dict(tests=len(cases), public=public, hidden=len(cases) - public, cache_fresh=fresh)

    for course_id in ("zero", "dsa", "cp"):
        course = catalog.courses[course_id]
        course_file = f"content/courses/{course.id}/course.yaml"
        add(
            "course",
            course.id,
            course.title,
            source_file=course_file,
            course_ids=course.id,
            storage="local curriculum metadata",
            languages=";".join(course.languages),
            details=json.dumps(
                {"version": course.version, "description": course.description}, ensure_ascii=False
            ),
            **local(None),
        )
        for module in course.modules:
            add(
                "module",
                f"{course.id}:{module.id}",
                module.title,
                [f"{course.id}:{cid}" for cid in module.concepts],
                source_file=course_file,
                storage="local curriculum metadata",
                details=module.summary,
                **local(None),
            )
        for concept in course.concepts:
            q = f"{course.id}:{concept.id}"
            path = f"content/courses/{course.id}/concepts/{concept.id}.yaml"
            add(
                "lesson",
                q,
                concept.title,
                [q],
                source_file=path,
                storage="local lesson text/code",
                source_name="Repository course authoring; item author not recorded",
                word_count=words(concept.lesson),
                difficulty=concept.difficulty,
                languages=";".join(course.languages),
                details=concept.summary,
                **local(concept.provenance),
            )
            for index, section in enumerate(sections(concept.lesson), 1):
                add(
                    "lesson_section",
                    f"{q}:{index}",
                    section["title"],
                    [q],
                    source_file=path,
                    word_count=section["own_words"],
                    storage="section within the lesson, not an additional lesson",
                    details=json.dumps(section, ensure_ascii=False),
                    **local(concept.provenance),
                )
            for quiz in concept.quiz:
                add(
                    "quiz",
                    f"{q}:{quiz.id}",
                    quiz.prompt,
                    [q],
                    source_file=path,
                    source_name="Repository course authoring; item author not recorded",
                    storage="local quiz and answer/explanation",
                    difficulty=quiz.difficulty,
                    languages=";".join(quiz.code),
                    details=quiz.kind,
                    **local(quiz.provenance or concept.provenance),
                )
            for index, r in enumerate(concept.resources, 1):
                add(
                    "course_resource",
                    f"{q}:{index}",
                    r.title,
                    [q],
                    source_file=path,
                    source_name=r.source,
                    source_url=str(r.url),
                    storage="external metadata/link only",
                    languages=";".join(r.languages) or "neutral",
                    details=f"kind={r.kind}; level={r.level}; estimated_minutes={r.minutes}",
                    review_record=NO_REVIEW,
                    provenance_origin="linked",
                    **rights.columns(rights.entry(url=str(r.url)), EXTERNAL_UNKNOWN),
                )
            for index, r in enumerate(concept.practice_links, 1):
                add(
                    "practice_link",
                    f"{q}:{index}",
                    r.title,
                    [q],
                    source_file=path,
                    source_name=r.platform,
                    source_url=str(r.url),
                    storage="external metadata/link only",
                    difficulty=r.difficulty,
                    review_record=NO_REVIEW,
                    provenance_origin="linked",
                    **rights.columns(rights.entry(url=str(r.url)), EXTERNAL_UNKNOWN),
                )
        for p in course.problems:
            path = f"content/courses/{course.id}/problems/{p.id}.yaml"
            add(
                "native_problem",
                p.id,
                p.title,
                [f"{course.id}:{x}" for x in p.concepts],
                source_file=path,
                source_name="Repository problem authoring; individual attribution not recorded",
                storage="local statement/examples/hints/reference/generator",
                difficulty=p.difficulty,
                word_count=words(p.statement),
                languages="python" + (";" + ";".join(p.references) if p.references else ""),
                details=json.dumps(
                    {
                        "examples": len(p.examples),
                        "hints": len(p.hints),
                        "brute": bool(p.brute),
                        **tests(p.id, path),
                    }
                ),
                **local(p.provenance, review=p.review),
            )
    for q, pack in sorted(catalog.atom_packs.items()):
        for atom in pack.atoms:
            add(
                "teaching_atom",
                f"{q}:{atom.id}",
                atom.title,
                [q],
                source_file=f"content/atoms/{q.replace(':', '/')}.yaml",
                source_name=pack.owner,
                storage="local teaching body/checks/code",
                word_count=words(atom.body),
                languages=";".join(atom.adapters) or "neutral",
                misconception_ids=atom.misconception or "",
                details=json.dumps(
                    {
                        "kind": atom.kind,
                        "status": pack.status,
                        "version": pack.version,
                        "steps": len(atom.steps),
                        "misconception": atom.misconception,
                        "body": atom.body,
                    },
                    ensure_ascii=False,
                ),
                **local(pack.provenance, review=pack.review, rights=pack.rights),
            )
    for q, entry in learning["concepts"].items():
        for item in entry["roadmap"]:
            add(
                "roadmap_link",
                f"{q}:{item['url']}",
                item["title"],
                [q],
                source_file="content/learning-resources.json",
                source_name=item.get("source", "Developer Roadmap"),
                source_url=item["url"],
                source_revision=learning["sources"]["roadmap_revision"],
                storage="external metadata/link only",
                languages=item.get("language") or "neutral",
                review_record=NO_REVIEW,
                provenance_origin="linked",
                **rights.columns(rights.entry("developer-roadmap"), EXTERNAL_UNKNOWN),
            )
        for item in entry["exercises"]:
            add(
                "python_exercise_link",
                f"{q}:{item['number']}",
                item["title"],
                [q],
                source_file="content/learning-resources.json",
                source_name="zhiwehu/Python-programming-exercises",
                source_url=item["url"],
                source_revision="master (unpinned)",
                storage="external metadata/link/guidance only",
                languages=item["language"],
                details=item["guidance"],
                review_record=NO_REVIEW,
                provenance_origin="linked",
                **rights.columns(None, EXTERNAL_UNKNOWN),
            )
    handbook = rights.entry("competitive-programmers-handbook")
    for q, chapters in book["concepts"].items():
        for chapter, title, page in chapters:
            add(
                "book_chapter_link",
                f"{q}:{chapter}:{page}",
                title,
                [q],
                source_file="content/practice/book.json",
                source_name=book["book"]["title"] + " — " + book["book"]["author"],
                source_url=book["book"]["url"] + f"#page={page + book['book']['page_offset']}",
                storage="external book/page link only",
                details=f"chapter={chapter}; printed_page={page}",
                review_record=NO_REVIEW,
                provenance_origin="linked",
                **{
                    **rights.columns(handbook, EXTERNAL_UNKNOWN),
                    "rights_or_license": book["book"]["license"],
                },
            )
    algorithms = rights.entry("thealgorithms")
    for item in implementations:
        revision = re.search(r"/blob/([a-f0-9]{40})/", item["url"])
        add(
            "implementation_link",
            item["id"],
            item["title"],
            [item["concept"]],
            source_file="content/practice/implementations.jsonl",
            source_name="TheAlgorithms",
            source_url=item["url"],
            source_revision=revision[1] if revision else "",
            languages=item["language"],
            storage="external code link only; code not stored in this catalog",
            review_record=NO_REVIEW,
            provenance_origin="linked",
            **rights.columns(algorithms, EXTERNAL_UNKNOWN),
        )
    for item in external:
        add(
            "external_problem",
            item["id"],
            item["title"],
            item["concepts"],
            source_file="content/practice/problems.jsonl",
            source_name=item["platform"],
            source_url=item["url"],
            storage="external problem metadata/link only",
            difficulty=item["difficulty"],
            source_revision="See content/practice/sources.json; no per-item import timestamp",
            details=json.dumps(
                {
                    k: item.get(k)
                    for k in [
                        "rating",
                        "tags",
                        "sheets",
                        "companies",
                        "recent_companies",
                        "solvers",
                    ]
                },
                ensure_ascii=False,
            ),
            review_record=NO_REVIEW,
            provenance_origin="linked",
            **rights.columns(rights.entry(PLATFORMS.get(item["platform"])), EXTERNAL_UNKNOWN),
        )
    for slug, company in sorted(companies.items()):
        add(
            "company_index_metadata",
            slug,
            company["name"],
            source_file="content/practice/companies.json",
            source_name="snehasishroy/leetcode-companywise-interview-questions",
            source_revision=snapshots["companywise"],
            storage="company/problem frequency metadata, not teaching content",
            details=json.dumps(
                {
                    "problem_associations": len(company["problems"]),
                    "problem_ids": [r[0] for r in company["problems"]],
                }
            ),
            review_record=NO_REVIEW,
            provenance_origin="linked",
            **rights.columns(None, "unknown: third-party metadata snapshot, license not recorded"),
        )
    for row in rows:
        unknown = sorted(set(filter(None, row["misconception_ids"].split(";"))) - taxonomy)
        if unknown:
            raise ValueError(f"{row['record_id']}: unknown misconception {unknown}")
    return rows


def problems(rows: list[dict]) -> list[str]:
    found = []
    ids = [row["record_id"] for row in rows]
    if len(set(ids)) != len(ids):
        found.append("inventory IDs must be unique")
    for row in rows:
        for column in ("rights_or_license", "review_record"):
            if not str(row[column]).strip():
                found.append(f"{row['record_id']}: empty {column}")
    return found


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        # Neutralise spreadsheet formula injection in text cells.
        writer.writerows(
            {
                k: (
                    "'" + v
                    if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                )
                for k, v in row.items()
            }
            for row in rows
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "content-inventory.csv")
    parser.add_argument("--check", action="store_true", help="validate only; write nothing")
    args = parser.parse_args()
    rows = build_rows()
    found = problems(rows)
    for problem in found:
        print(problem, file=sys.stderr)
    if not args.check and not found:
        write_csv(rows, args.out)
        print(f"{len(rows)} records -> {args.out}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
