"""External practice index: curated links to LeetCode/CSES/Codeforces problems, company lists,
reference implementations and handbook chapters, all mapped to Socrat concepts.

Built offline by scripts/content/import_practice.py; metadata and links only.
"""

import json
import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from socrat.catalog.registry import REPO_ROOT

PRACTICE_ROOT = Path(os.environ.get("SOCRAT_PRACTICE_ROOT", REPO_ROOT / "content" / "practice"))
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
WINDOW_RANK = {
    "thirty-days": 0,
    "three-months": 1,
    "six-months": 2,
    "more-than-six-months": 3,
    "all": 4,
}
# Comparable difficulty on one scale. Codeforces problems carry a real rating; others are
# placed by their platform's label.
LABEL_RATING = {
    "LeetCode": {"easy": 1000, "medium": 1400, "hard": 1900},
    "CSES": {"easy": 1100, "medium": 1500, "hard": 1900},
}
PLATFORMS = ("LeetCode", "CSES", "Codeforces")


def rating_of(problem: dict) -> int:
    if problem.get("rating"):
        return int(problem["rating"])
    return LABEL_RATING.get(problem["platform"], LABEL_RATING["LeetCode"])[problem["difficulty"]]


# Which external difficulties suit each mastery band.
BAND_DIFFICULTIES = {
    "not_started": ("easy",),
    "needs_practice": ("easy", "medium"),
    "developing": ("easy", "medium"),
    "likely_known": ("medium", "hard"),
    "strong": ("medium", "hard"),
}


@dataclass
class PracticeIndex:
    problems: dict[str, dict] = field(default_factory=dict)
    by_concept: dict[str, list[str]] = field(default_factory=dict)
    companies: dict[str, dict] = field(default_factory=dict)
    implementations: dict[tuple[str, str], list[dict]] = field(default_factory=dict)
    book: dict = field(default_factory=dict)
    _urls: dict[str, str] = field(default_factory=dict, repr=False)

    def for_concept(self, concept: str, band: str, limit: int = 8) -> list[dict]:
        """Best external problems for a concept, matched to the learner's level."""
        wanted = BAND_DIFFICULTIES.get(band, ("easy", "medium"))
        ids = self.by_concept.get(concept, [])
        ranked = sorted(
            (self.problems[i] for i in ids),
            key=lambda p: (
                p["difficulty"] not in wanted,
                p["concepts"][0] != concept,  # primary matches first
                "striver-a2z" not in p["sheets"],
                -p["companies"],
                -p.get("solvers", 0),
                p["id"],
            ),
        )
        return [public(p) for p in ranked[:limit]]

    def find_url(self, url: str) -> dict | None:
        if not self._urls:
            self._urls = {normal_url(p["url"]): i for i, p in self.problems.items()}
        problem_id = self._urls.get(normal_url(url))
        return self.problems[problem_id] if problem_id else None

    def search(
        self,
        query: str = "",
        platforms: tuple[str, ...] = (),
        concept: str = "",
        difficulty: str = "",
        rating_min: int = 0,
        rating_max: int = 0,
        sheet: str = "",
        ids: set[str] | None = None,
    ) -> list[dict]:
        """Filter the whole library. Callers sort; this keeps index order (by id)."""
        words = query.lower().split()
        pool = (
            (self.problems[i] for i in self.by_concept.get(concept, []))
            if concept
            else self.problems.values()
        )
        out = []
        for p in pool:
            if ids is not None and p["id"] not in ids:
                continue
            if platforms and p["platform"] not in platforms:
                continue
            if difficulty and p["difficulty"] != difficulty:
                continue
            if sheet and sheet not in p["sheets"]:
                continue
            if rating_min or rating_max:
                r = rating_of(p)
                if (rating_min and r < rating_min) or (rating_max and r > rating_max):
                    continue
            if words and not all(w in p["title"].lower() for w in words):
                continue
            out.append(p)
        return out

    def implementations_for(self, concept: str, language: str, limit: int = 3) -> list[dict]:
        return [
            {"title": i["title"], "url": i["url"]}
            for i in self.implementations.get((concept, language), [])[:limit]
        ]

    def book_for(self, concept: str) -> list[dict]:
        meta = self.book.get("book", {})
        offset = meta.get("page_offset", 0)
        return [
            {
                "chapter": chapter,
                "title": title,
                "page": page,
                "url": f"{meta['url']}#page={page + offset}",
                "source": f"{meta['title']} — {meta['author']}",
            }
            for chapter, title, page in self.book.get("concepts", {}).get(concept, [])
        ]


def normal_url(url: str) -> str:
    return url.lower().split("?")[0].rstrip("/").replace("http://", "https://").replace("www.", "")


def public(problem: dict) -> dict:
    return {
        "id": problem["id"],
        "title": problem["title"],
        "url": problem["url"],
        "platform": problem["platform"],
        "difficulty": problem["difficulty"],
        "rating": problem.get("rating"),
        "concepts": problem["concepts"],
        "companies": problem["companies"],
        "striver": "striver-a2z" in problem["sheets"],
    }


def load(root: Path = PRACTICE_ROOT) -> PracticeIndex:
    index = PracticeIndex()
    problems_path = root / "problems.jsonl"
    if not problems_path.exists():
        return index
    for line in problems_path.read_text(encoding="utf-8").splitlines():
        problem = json.loads(line)
        index.problems[problem["id"]] = problem
        for concept in problem["concepts"]:
            index.by_concept.setdefault(concept, []).append(problem["id"])
    companies_path = root / "companies.json"
    if companies_path.exists():
        index.companies = json.loads(companies_path.read_text(encoding="utf-8"))
    implementations_path = root / "implementations.jsonl"
    if implementations_path.exists():
        for line in implementations_path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            index.implementations.setdefault((item["concept"], item["language"]), []).append(item)
    book_path = root / "book.json"
    if book_path.exists():
        index.book = json.loads(book_path.read_text(encoding="utf-8"))
    return index


@cache
def default_index() -> PracticeIndex:
    return load()
