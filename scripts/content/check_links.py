"""Verify every curated resource and practice link responds.

Some sites (LeetCode, Codeforces) block automated clients; a 403/429 from those
hosts is reported as "unverifiable" rather than broken. Any other failure exits 1.

Usage: python scripts/content/check_links.py
"""

import concurrent.futures
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402

BOT_PROTECTED = {"leetcode.com", "codeforces.com", "realpython.com", "www.geeksforgeeks.org"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Socrat content link checker)"}


def check(url: str) -> tuple[str, str]:
    host = httpx.URL(url).host
    try:
        response = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
    except httpx.HTTPError as exc:
        if host in BOT_PROTECTED and isinstance(exc, httpx.TimeoutException):
            return url, "unverifiable"
        return url, f"error {type(exc).__name__}"
    if response.status_code < 400:
        # YouTube answers 200 for removed videos; a real video page has a title.
        if host.endswith("youtube.com") and "<title>- YouTube</title>" in response.text:
            return url, "missing video"
        return url, "ok"
    if host in BOT_PROTECTED and response.status_code in {403, 429, 503}:
        return url, "unverifiable"
    return url, f"http {response.status_code}"


def main() -> int:
    catalog = load(CONTENT_ROOT)
    urls = sorted(
        {
            str(item.url)
            for course in catalog.courses.values()
            for concept in course.concepts
            for item in [*concept.resources, *concept.practice_links]
        }
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(check, urls))
    broken = [(url, status) for url, status in results if status not in {"ok", "unverifiable"}]
    unverifiable = [url for url, status in results if status == "unverifiable"]
    for url, status in broken:
        print(f"BROKEN {status}: {url}")
    print(
        f"{len(urls)} links: {len(urls) - len(broken) - len(unverifiable)} ok, "
        f"{len(unverifiable)} unverifiable (bot-protected), {len(broken)} broken."
    )
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
