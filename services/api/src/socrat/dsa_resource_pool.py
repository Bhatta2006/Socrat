"""Draft DSA source index and policy-bounded candidate selector.

The index stores links and metadata, never third-party statements or solutions.
An imported record is not learner eligible until editorial and rights release.
"""

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote, urlparse

from pydantic import Field, model_validator

from socrat.skill_packs import StrictModel

POLICY_VERSION = "dsa-resource-selector-0.1.0"
ResourceKind = Literal["problem", "solution", "lesson", "roadmap", "implementation"]
ResourceScope = Literal["dsa_candidate", "out_of_scope", "unknown"]
SOURCE_URLS = {
    "striver": "https://github.com/Codensity30/Strivers-A2Z-DSA-Sheet",
    "practical": "https://github.com/namphuongtran/practical-dsa",
    "cpalg": "https://github.com/cp-algorithms/cp-algorithms",
    "thealg": "https://github.com/TheAlgorithms/C-Plus-Plus",
    "roadmap": "https://github.com/maroofiums/DSA_Roadmap",
    "ishaan": "https://github.com/ishaanbuildsthings/leetcode",
    "companies": "https://github.com/liquidslr/leetcode-company-wise-problems",
    "cses": "https://cses.fi/problemset/",
}
SOURCE_RIGHTS = {
    "striver": "unverified_no_license",
    "practical": "MIT_repo; linked_problems_separate",
    "cpalg": "CC-BY-SA-4.0_repo; links_only",
    "thealg": "MIT_code; generated_docs_CC-BY-SA-4.0",
    "roadmap": "unverified_no_license",
    "ishaan": "unverified_no_license",
    "companies": "unverified_no_license; company_tags_unverified",
    "cses": "external_site_terms_unverified",
}

# Broad tags retain fine-grained structure. The current M2 graph has fewer nodes;
# unreleased topics remain catalogued here for later editorial graph expansion.
TOPIC_PARENTS = {
    "language-readiness": [],
    "complexity": ["language-readiness"],
    "arrays": ["language-readiness"],
    "strings": ["language-readiness"],
    "hash-maps": ["arrays"],
    "sorting": ["arrays", "complexity"],
    "binary-search": ["arrays", "complexity"],
    "two-pointers": ["arrays"],
    "sliding-window": ["arrays", "two-pointers"],
    "prefix-sums": ["arrays"],
    "linked-lists": ["language-readiness"],
    "stacks-queues": ["arrays"],
    "heaps": ["trees"],
    "recursion": ["language-readiness"],
    "backtracking": ["recursion"],
    "trees": ["recursion"],
    "binary-search-trees": ["trees", "binary-search"],
    "tries": ["trees", "strings"],
    "graphs": ["trees"],
    "dsu": ["graphs"],
    "shortest-paths": ["graphs"],
    "minimum-spanning-trees": ["graphs", "dsu"],
    "topological-sort": ["graphs"],
    "greedy": ["complexity"],
    "dynamic-programming": ["recursion", "arrays"],
    "bit-manipulation": ["language-readiness"],
    "number-theory": ["complexity"],
    "combinatorics": ["number-theory"],
    "range-queries": ["arrays", "trees"],
    "segment-trees": ["range-queries"],
    "string-algorithms": ["strings"],
    "geometry": ["complexity"],
    "probability": ["combinatorics"],
    "game-theory": ["dynamic-programming"],
    "sorting-searching": ["arrays", "complexity"],
    "contest-strategy": ["greedy"],
    "introductory-problems": ["language-readiness"],
    "advanced-algorithms": ["complexity"],
    "counting-problems": ["combinatorics"],
    "constructive-algorithms": ["greedy"],
    "interactive-problems": ["contest-strategy"],
}
TOPIC_ALIASES = {
    "array": "arrays",
    "arrays": "arrays",
    "matrix": "arrays",
    "string": "strings",
    "strings": "strings",
    "hash table": "hash-maps",
    "hashing": "hash-maps",
    "hash map": "hash-maps",
    "sorting": "sorting",
    "sort": "sorting",
    "binary search": "binary-search",
    "two pointers": "two-pointers",
    "sliding window": "sliding-window",
    "prefix sum": "prefix-sums",
    "linked list": "linked-lists",
    "stack": "stacks-queues",
    "queue": "stacks-queues",
    "heap": "heaps",
    "heaps": "heaps",
    "priority queue": "heaps",
    "recursion": "recursion",
    "backtracking": "backtracking",
    "binary tree": "trees",
    "binary trees": "trees",
    "tree": "trees",
    "trees": "trees",
    "binary search tree": "binary-search-trees",
    "trie": "tries",
    "graph": "graphs",
    "graphs": "graphs",
    "graph algorithms": "graphs",
    "tree algorithms": "trees",
    "union find": "dsu",
    "disjoint set": "dsu",
    "dsu": "dsu",
    "shortest path": "shortest-paths",
    "dijkstra": "shortest-paths",
    "minimum spanning tree": "minimum-spanning-trees",
    "topological sort": "topological-sort",
    "greedy": "greedy",
    "dynamic programming": "dynamic-programming",
    "dp": "dynamic-programming",
    "bit manipulation": "bit-manipulation",
    "bitmask": "bit-manipulation",
    "number theory": "number-theory",
    "math": "number-theory",
    "mathematics": "number-theory",
    "combinatorics": "combinatorics",
    "range queries": "range-queries",
    "segment tree": "segment-trees",
    "string algorithms": "string-algorithms",
    "geometry": "geometry",
    "probability": "probability",
    "game theory": "game-theory",
    "sorting and searching": "sorting-searching",
    "introductory problems": "introductory-problems",
    "advanced techniques": "advanced-algorithms",
    "counting problems": "counting-problems",
    "construction problems": "constructive-algorithms",
    "interactive problems": "interactive-problems",
    "bitwise operations": "bit-manipulation",
}
ROADMAP_WEEK_TOPICS = {
    1: "arrays",
    2: "strings",
    3: "sliding-window",
    4: "linked-lists",
    5: "stacks-queues",
    6: "binary-search",
    7: "trees",
    8: "trees",
    9: "graphs",
    10: "backtracking",
    11: "heaps",
    12: "dynamic-programming",
}
CS_EASIER = {
    "introductory problems": 2,
    "sorting and searching": 4,
    "dynamic programming": 5,
    "graph algorithms": 5,
    "tree algorithms": 6,
    "range queries": 6,
    "mathematics": 6,
    "string algorithms": 7,
    "geometry": 7,
    "advanced techniques": 8,
    "additional problems i": 7,
    "additional problems ii": 8,
    "advanced graph problems": 8,
    "counting problems": 6,
    "sliding window problems": 5,
    "bitwise operations": 5,
    "construction problems": 6,
    "interactive problems": 8,
}
COMPANY_WINDOWS = {
    "1. Thirty Days": "thirty_days",
    "2. Three Months": "three_months",
    "3. Six Months": "six_months",
    "4. More Than Six Months": "older",
    "5. All": "all_time",
}
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".cpp": "cpp",
    ".c": "c",
    ".java": "java",
    ".js": "javascript",
}


class Difficulty(StrictModel):
    band: int | None = Field(default=None, ge=1, le=10)
    status: str
    basis: str
    source_label: str | None = None


class Reference(StrictModel):
    source: str
    role: str
    url: str
    language: str | None = None
    match_basis: Literal["source_identity", "exact_title_unverified"] = "source_identity"


class CompanySignal(StrictModel):
    company: str
    window: str
    frequency: float | None = Field(default=None, ge=0, le=100)
    source_path: str | None = None
    as_of_month: str | None = None


class Resource(StrictModel):
    id: str
    kind: ResourceKind
    title: str
    url: str
    provider: str
    topics: list[str]
    primary_topic: str | None = None
    difficulty: Difficulty
    languages: list[str]
    tracks: list[str]
    expected_minutes: int | None = None
    release_status: Literal["review_required", "released", "quarantined"]
    scope: ResourceScope = "unknown"
    rights_reviewed_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    delivery: Literal["external_link", "reference_only"]
    references: list[Reference]
    company_signals: list[CompanySignal]

    @model_validator(mode="after")
    def valid_release(self) -> "Resource":
        if self.release_status == "released":
            if self.scope != "dsa_candidate":
                raise ValueError("released resource must be in scope")
            if self.primary_topic is None or self.primary_topic not in self.topics:
                raise ValueError("released resource needs reviewed primary topic")
            if not self.rights_reviewed_at:
                raise ValueError("released resource needs rights review")
            if self.difficulty.band is None or self.expected_minutes is None:
                raise ValueError("released resource needs difficulty and time review")
            if self.kind == "problem" and not self.languages:
                raise ValueError("released problem needs verified language availability")
        return self


class SourceSnapshot(StrictModel):
    key: str
    url: str
    revision: str | None
    rights: str


class ResourcePool(StrictModel):
    schema_version: Literal[1]
    sources: list[SourceSnapshot]
    resources: list[Resource]


def load_resource_pool(resources_path: Path, summary_path: Path) -> ResourcePool:
    """Load the committed line index with its pinned-source manifest."""
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with resources_path.open(encoding="utf-8") as stream:
        resources = [Resource.model_validate_json(line) for line in stream if line.strip()]
    return ResourcePool.model_validate(
        {
            "schema_version": summary["schema_version"],
            "sources": summary["snapshots"],
            "resources": resources,
        }
    )


class LearnerSnapshot(StrictModel):
    track: str
    language: str
    ready_topics: list[str]
    released_topics: list[str]
    target_topics: list[str]
    target_difficulty: int = Field(ge=1, le=10)
    time_budget_minutes: int = Field(ge=1)
    target_company: str | None = None
    preferred_kinds: list[str] = Field(default_factory=lambda: ["problem"])
    solved_ids: list[str] = Field(default_factory=list)
    recent_ids: list[str] = Field(default_factory=list)
    due_topics: list[str] = Field(default_factory=list)
    topic_mastery: dict[str, Annotated[float, Field(ge=0, le=1)]] = Field(default_factory=dict)
    misconception_topics: list[str] = Field(default_factory=list)
    recent_performance: list["PerformanceSignal"] = Field(default_factory=list)


class PerformanceSignal(StrictModel):
    topic: str
    difficulty_band: int = Field(ge=1, le=10)
    success: bool
    independent: bool
    within_expected_time: bool


class RankedCandidate(StrictModel):
    id: str
    score: float
    reason_codes: list[str]


class SelectionDecision(StrictModel):
    policy_version: str
    input_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_id: str | None
    candidates: list[RankedCandidate]
    exclusion_counts: dict[str, int]


class AdvisorChoice(StrictModel):
    policy_version: str
    input_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    recommended_candidate_ids: list[str] = Field(min_length=1, max_length=8)
    evidence_refs: list[str] = Field(min_length=1)
    reason_codes: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def clean_title(stem: str) -> str:
    return re.sub(r"^\d+[. :_ -]+", "", stem).replace("_", " ").strip()


def topics_for(*texts: str) -> list[str]:
    found = []
    for text in texts:
        normal = " " + re.sub(r"[^a-z0-9]+", " ", text.casefold()) + " "
        for alias in sorted(TOPIC_ALIASES, key=len, reverse=True):
            if f" {alias} " in normal and TOPIC_ALIASES[alias] not in found:
                found.append(TOPIC_ALIASES[alias])
    return found


class CsesIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.category = ""
        self.heading = False
        self.current_id: str | None = None
        self.problems: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h2":
            self.heading = True
        if tag == "a":
            match = re.fullmatch(r"/problemset/task/(\d+)", attributes.get("href") or "")
            if match:
                self.current_id = match.group(1)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self.heading = False
        if tag == "a":
            self.current_id = None

    def handle_data(self, data: str) -> None:
        if self.heading:
            self.category = data.strip()
        if self.current_id and data.strip():
            self.problems.append((self.current_id, data.strip(), self.category))


def _revision(repo: Path) -> str | None:
    if not (repo / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _github_file(source: str, revision: str | None, relative: str) -> str:
    branch = revision or "HEAD"
    encoded = "/".join(quote(part, safe="") for part in relative.split("/"))
    return f"{SOURCE_URLS[source]}/blob/{branch}/{encoded}"


def _difficulty(label: str | None, basis: str) -> Difficulty:
    if label:
        band = {"easy": 2, "medium": 5, "hard": 8}.get(label.casefold())
        if band:
            return Difficulty(band=band, status="provisional", basis=basis, source_label=label)
    return Difficulty(band=None, status="unclassified", basis="insufficient_evidence")


def _source_item(
    source: str,
    relative: str,
    revision: str | None,
    kind: ResourceKind,
    title: str,
    topic_texts: Iterable[str],
    difficulty: Difficulty,
) -> Resource:
    url = _github_file(source, revision, relative)
    language = LANGUAGE_EXTENSIONS.get(Path(relative).suffix.casefold())
    topics = topics_for(*topic_texts)
    return Resource(
        id=f"source:{source}:{slug(relative)}",
        kind=kind,
        title=title,
        url=url,
        provider=source,
        topics=topics,
        primary_topic=topics[0] if topics else None,
        difficulty=difficulty,
        languages=[language] if language in {"python", "cpp", "java"} else [],
        tracks=(
            ["competitive"]
            if source == "cpalg"
            else ["foundations", "interview"]
            if source in {"striver", "practical", "roadmap"}
            else ["interview", "competitive"]
            if source == "ishaan"
            else ["foundations", "interview", "competitive"]
        ),
        expected_minutes=None,
        release_status="review_required",
        scope="dsa_candidate" if topics else "unknown",
        delivery="reference_only",
        references=[Reference(source=source, role=kind, url=url, language=language)],
        company_signals=[],
    )


def _add_reference(
    item: Resource, ref: Reference, topic_keys: list[str], difficulty: Difficulty
) -> None:
    if not any(existing.url == ref.url for existing in item.references):
        item.references.append(ref)
    item.topics = sorted(set(item.topics + topic_keys))
    if item.difficulty.band is None and difficulty.band is not None:
        item.difficulty = difficulty


def _iter_source_paths(repo: Path, source: str) -> list[str]:
    if source == "ishaan" and (repo / ".git").exists():
        # This repository has Windows-invalid filenames; its Git tree still
        # yields stable paths without checking out or reading those blobs.
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.splitlines()
    return [
        path.relative_to(repo).as_posix()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    ]


def build_resource_pool(source_root: Path, *, cses_html: str) -> ResourcePool:
    """Index local source snapshots and CSES task HTML without copying content."""
    revisions = {key: _revision(source_root / key) for key in SOURCE_URLS if key != "cses"}
    revisions["cses"] = hashlib.sha256(cses_html.encode()).hexdigest() if cses_html else None
    resources: dict[str, Resource] = {}
    title_index: dict[str, str] = {}
    company_root = source_root / "companies"
    if company_root.exists():
        for path in sorted(company_root.rglob("*.csv")):
            company = path.parent.name
            window = COMPANY_WINDOWS.get(path.stem)
            if window is None:
                continue
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    url = (row.get("Link") or "").strip().rstrip("/") + "/"
                    parsed = urlparse(url)
                    match = re.fullmatch(r"/problems/([a-z0-9-]+)/", parsed.path)
                    if parsed.netloc != "leetcode.com" or not match:
                        continue
                    key = f"leetcode:{match.group(1)}"
                    title = (row.get("Title") or "").strip() or match.group(1).replace("-", " ")
                    topics = topics_for(*(row.get("Topics") or "").split(","))
                    raw_topics = (row.get("Topics") or "").casefold()
                    scope: ResourceScope = (
                        "out_of_scope"
                        if any(
                            excluded in raw_topics
                            for excluded in (
                                "database",
                                "shell",
                                "pandas",
                                "javascript",
                                "concurrency",
                            )
                        )
                        else "dsa_candidate"
                        if topics
                        else "unknown"
                    )
                    difficulty = _difficulty(row.get("Difficulty"), "provider_label")
                    if key not in resources:
                        resources[key] = Resource(
                            id=key,
                            kind="problem",
                            title=title,
                            url=url,
                            provider="leetcode",
                            topics=topics,
                            primary_topic=topics[0] if topics else None,
                            difficulty=difficulty,
                            languages=[],
                            tracks=["interview", "competitive"],
                            expected_minutes=None,
                            release_status="review_required",
                            scope=scope,
                            delivery="external_link",
                            references=[
                                Reference(
                                    source="companies",
                                    role="metadata",
                                    url=_github_file(
                                        "companies",
                                        revisions["companies"],
                                        path.relative_to(company_root).as_posix(),
                                    ),
                                )
                            ],
                            company_signals=[],
                        )
                    item = resources[key]
                    item.topics = sorted(set(item.topics + topics))
                    if item.primary_topic is None and topics:
                        item.primary_topic = topics[0]
                    if scope == "dsa_candidate":
                        item.scope = scope
                    if item.difficulty.band is None and difficulty.band is not None:
                        item.difficulty = difficulty
                    try:
                        raw_frequency = float(row["Frequency"])
                        frequency: float | None = (
                            raw_frequency if 0 <= raw_frequency <= 100 else None
                        )
                    except (ValueError, TypeError, KeyError):
                        frequency = None
                    if not any(
                        s.company == company and s.window == window for s in item.company_signals
                    ):
                        item.company_signals.append(
                            CompanySignal(
                                company=company,
                                window=window,
                                frequency=frequency,
                                source_path=path.relative_to(company_root).as_posix(),
                                as_of_month="2025-06",
                            )
                        )
                    title_index.setdefault(slug(title), key)

    parser = CsesIndexParser()
    parser.feed(cses_html)
    for problem_id, title, category in parser.problems:
        key = f"cses:{problem_id}"
        category_name = category.casefold()
        band = CS_EASIER.get(category_name)
        topics = topics_for(category, title)
        resources[key] = Resource(
            id=key,
            kind="problem",
            title=title,
            url=f"https://cses.fi/problemset/task/{problem_id}",
            provider="cses",
            topics=topics,
            primary_topic=topics[0] if topics else None,
            difficulty=Difficulty(
                band=band,
                status="provisional" if band else "unclassified",
                basis="category_prior" if band else "insufficient_evidence",
                source_label=category,
            ),
            languages=[],
            tracks=["competitive"],
            expected_minutes=None,
            release_status="review_required",
            scope=(
                "out_of_scope"
                if category_name == "interactive problems"
                else "dsa_candidate"
                if topics
                else "unknown"
            ),
            delivery="external_link",
            references=[
                Reference(
                    source="cses",
                    role="problem",
                    url=f"https://cses.fi/problemset/task/{problem_id}",
                )
            ],
            company_signals=[],
        )
        title_index.setdefault(f"cses:{slug(title)}", key)

    for source in ("striver", "practical", "cpalg", "thealg", "roadmap", "ishaan"):
        repo = source_root / source
        if not repo.exists():
            continue
        for relative in sorted(_iter_source_paths(repo, source)):
            path = Path(relative)
            parts = path.parts
            suffix = path.suffix.casefold()
            kind: ResourceKind
            if any(part.startswith(".") for part in parts) or "__pycache__" in parts:
                continue
            if source == "striver":
                if suffix != ".cpp":
                    continue
                kind = "solution"
                title = clean_title(path.stem)
                label = next(
                    (
                        label
                        for part in parts
                        for label in ("Easy", "Medium", "Hard")
                        if re.search(rf"\b{label}\b", part, re.IGNORECASE)
                    ),
                    None,
                )
                difficulty = _difficulty(label, "sheet_label")
                topic_texts = [parts[0], *parts[1:-1], title]
            elif source == "practical":
                if not relative.startswith("phase-") and relative not in {
                    "README.md",
                    "ROADMAP.md",
                    "docs/prerequisites.md",
                    "docs/resources.md",
                    "docs/guidelines.md",
                }:
                    continue
                if suffix not in {".md", ".c", ".cpp"}:
                    continue
                kind = (
                    "lesson"
                    if path.name in {"notes.md", "prerequisites.md", "resources.md"}
                    else (
                        "roadmap"
                        if suffix == ".md"
                        else "implementation"
                        if "impl" in parts
                        else "solution"
                    )
                )
                title = (
                    " ".join(part for part in parts if part.startswith("week-"))
                    + " "
                    + clean_title(path.stem)
                )
                week = re.search(r"week-(\d+)", relative)
                band = min(8, max(2, int(week.group(1)) // 2 + 2)) if week else None
                difficulty = Difficulty(
                    band=band,
                    status="provisional" if band else "unclassified",
                    basis="curriculum_position" if band else "insufficient_evidence",
                )
                topic_texts = [relative]
            elif source == "cpalg":
                if (
                    not relative.startswith("src/")
                    or suffix != ".md"
                    or path.stem in {"index", "tags", "preview"}
                ):
                    continue
                kind, title = "lesson", clean_title(path.stem).replace("-", " ")
                difficulty = _difficulty(None, "")
                topic_texts = [str(path.parent), title]
            elif source == "thealg":
                if suffix != ".cpp" or len(parts) < 2:
                    continue
                kind, title = "implementation", clean_title(path.stem)
                difficulty = _difficulty(None, "")
                topic_texts = [parts[0], title]
            elif source == "roadmap":
                if suffix not in {".md", ".py"} or not relative.startswith("Week"):
                    continue
                kind = "roadmap" if suffix == ".md" else "solution"
                title = (
                    f"{parts[0]} {parts[1]} guide"
                    if suffix == ".md" and len(parts) > 2
                    else clean_title(path.stem)
                )
                week = re.match(r"Week(\d+)", parts[0])
                band = min(8, max(2, (int(week.group(1)) + 1) // 2 + 1)) if week else None
                difficulty = Difficulty(
                    band=band,
                    status="provisional" if band else "unclassified",
                    basis="curriculum_position" if band else "insufficient_evidence",
                )
                week_topic = ROADMAP_WEEK_TOPICS.get(int(week.group(1))) if week else None
                topic_texts = [week_topic or "", relative, title]
            else:
                if not relative.startswith("problems/") or suffix not in LANGUAGE_EXTENSIONS:
                    continue
                kind, title = "solution", clean_title(path.stem)
                difficulty = _difficulty(None, "")
                topic_texts = [title]

            canonical = None
            if kind == "solution":
                if source == "ishaan" and len(parts) > 1 and parts[1] == "CSES":
                    canonical = title_index.get(f"cses:{slug(title)}")
                elif source != "ishaan" or (len(parts) > 1 and parts[1] == "Leetcode"):
                    canonical = title_index.get(slug(title))
            if canonical:
                _add_reference(
                    resources[canonical],
                    Reference(
                        source=source,
                        role="solution",
                        url=_github_file(source, revisions[source], relative),
                        language=LANGUAGE_EXTENSIONS.get(suffix),
                        match_basis="exact_title_unverified",
                    ),
                    topics_for(*topic_texts),
                    difficulty,
                )
            else:
                item = _source_item(
                    source, relative, revisions[source], kind, title, topic_texts, difficulty
                )
                if item.id not in resources:
                    resources[item.id] = item

    snapshots = [
        SourceSnapshot(key=key, url=url, revision=revisions.get(key), rights=SOURCE_RIGHTS[key])
        for key, url in SOURCE_URLS.items()
    ]
    ordered = sorted(
        resources.values(),
        key=lambda item: (
            item.topics[0] if item.topics else "zzz-unclassified",
            item.difficulty.band if item.difficulty.band is not None else 99,
            item.title.casefold(),
            item.id,
        ),
    )
    return ResourcePool(schema_version=1, sources=snapshots, resources=ordered)


def _prerequisites_ready(topic: str, ready: set[str]) -> bool:
    pending = list(TOPIC_PARENTS.get(topic, []))
    seen = set()
    while pending:
        prerequisite = pending.pop()
        if prerequisite in seen:
            continue
        seen.add(prerequisite)
        if prerequisite not in ready:
            return False
        pending.extend(TOPIC_PARENTS.get(prerequisite, []))
    return True


def choose_next(pool: ResourcePool, learner: LearnerSnapshot) -> SelectionDecision:
    """Hard-filter first, then score only permitted candidate IDs."""
    exclusions: Counter[str] = Counter()
    ranked: list[RankedCandidate] = []
    ready = set(learner.ready_topics)
    released = set(learner.released_topics)
    target = set(learner.target_topics)
    solved = set(learner.solved_ids)
    recent = set(learner.recent_ids)
    effective_band = learner.target_difficulty
    relevant_performance = [
        signal
        for signal in learner.recent_performance
        if signal.topic in target and signal.difficulty_band == learner.target_difficulty
    ]
    if len(relevant_performance) >= 3 and all(
        signal.success and signal.independent and signal.within_expected_time
        for signal in relevant_performance[-3:]
    ):
        effective_band = min(10, effective_band + 1)
    elif len(relevant_performance) >= 2 and all(
        not signal.success and signal.independent for signal in relevant_performance[-2:]
    ):
        effective_band = max(1, effective_band - 1)
    for item in pool.resources:
        reason = None
        if item.release_status != "released":
            reason = "not_released"
        elif item.scope != "dsa_candidate":
            reason = "out_of_scope"
        elif item.primary_topic not in released:
            reason = "topic_not_released"
        elif item.kind not in learner.preferred_kinds:
            reason = "wrong_kind"
        elif learner.track not in item.tracks:
            reason = "wrong_track"
        elif learner.language not in item.languages:
            reason = "unsupported_language"
        elif item.id in solved or item.id in recent:
            reason = "exposure_excluded"
        elif item.primary_topic not in target:
            reason = "outside_goal"
        elif not _prerequisites_ready(item.primary_topic, ready):
            reason = "prerequisite_locked"
        elif item.difficulty.band is None or item.difficulty.band > effective_band + 1:
            reason = "difficulty_unavailable"
        elif item.expected_minutes is None or item.expected_minutes > learner.time_budget_minutes:
            reason = "time_unavailable"
        if reason:
            exclusions[reason] += 1
            continue
        assert item.difficulty.band is not None
        score = 10.0 - abs(item.difficulty.band - effective_band) * 2
        codes = ["goal_topic", "difficulty_fit"]
        if item.primary_topic in learner.topic_mastery:
            score += 3 * (1 - learner.topic_mastery[item.primary_topic])
            codes.append("concept_need")
        if item.primary_topic in learner.misconception_topics:
            score += 2
            codes.append("misconception_match")
        if set(item.topics) & set(learner.due_topics):
            score += 3
            codes.append("due_review")
        if learner.target_company and learner.track == "interview":
            signals = [
                signal
                for signal in item.company_signals
                if signal.company.casefold() == learner.target_company.casefold()
            ]
            if signals:
                historical = [signal for signal in signals if signal.window == "all_time"]
                best = max((signal.frequency or 0) for signal in (historical or signals))
                score += min(2, best / 50)
                codes.append("company_goal")
        ranked.append(RankedCandidate(id=item.id, score=round(score, 3), reason_codes=codes))
    ranked.sort(key=lambda candidate: (-candidate.score, candidate.id))
    top = ranked[:8]
    snapshot = {
        "policy_version": POLICY_VERSION,
        "learner": learner.model_dump(),
        "sources": [(source.key, source.revision) for source in pool.sources],
        "candidates": [candidate.model_dump() for candidate in top],
    }
    snapshot_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SelectionDecision(
        policy_version=POLICY_VERSION,
        input_snapshot_hash=snapshot_hash,
        baseline_id=top[0].id if top else None,
        candidates=top,
        exclusion_counts=dict(exclusions),
    )


def validate_advisor_choice(
    decision: SelectionDecision, advice: AdvisorChoice, *, allowed_evidence_refs: set[str]
) -> str | None:
    """The advisor may only rerank the supplied envelope; invalid advice falls back."""
    eligible = {candidate.id for candidate in decision.candidates}
    if (
        advice.policy_version != decision.policy_version
        or advice.input_snapshot_hash != decision.input_snapshot_hash
        or advice.confidence < 0.6
        or len(set(advice.recommended_candidate_ids)) != len(advice.recommended_candidate_ids)
        or not set(advice.recommended_candidate_ids) <= eligible
        or not set(advice.evidence_refs) <= allowed_evidence_refs
        or not set(advice.reason_codes)
        <= {
            "goal_topic",
            "difficulty_fit",
            "due_review",
            "company_goal",
            "concept_need",
            "misconception_match",
        }
    ):
        return decision.baseline_id
    return advice.recommended_candidate_ids[0]
