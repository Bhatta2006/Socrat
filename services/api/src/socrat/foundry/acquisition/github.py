import base64
import hashlib
import json
import re
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from socrat.foundry.acquisition.network import optout_headers
from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.compliance.licenses import License, license_file
from socrat.foundry.models import ApiCache


def repository_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise PolicyBlocked("invalid_repository")
    return value


def metadata(repo: dict) -> dict:
    if repo.get("private") or repo.get("visibility", "public") != "public":
        raise PolicyBlocked("private_repository")
    name = repository_name(repo.get("full_name", ""))
    return {
        "full_name": name,
        "stars": int(repo.get("stargazers_count", 0)),
        "forks": int(repo.get("forks_count", 0)),
        "pushed_at": str(repo.get("pushed_at", ""))[:32],
        "archived": bool(repo.get("archived")),
        "fork": bool(repo.get("fork")),
        "topics": [str(t)[:80] for t in repo.get("topics", [])[:30]],
        "default_branch": str(repo.get("default_branch", "main"))[:100],
        "spdx": str((repo.get("license") or {}).get("spdx_id", "unknown"))[:64],
        "url": "https://github.com/" + name,
    }


class GitHubClient:
    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch(self, url: str, context):
        from socrat.foundry.compliance.urls import canonical_url

        parsed = canonical_url(url)
        if parsed.scheme != "https" or parsed.host != "github.com" or parsed.query:
            raise PolicyBlocked("invalid_repository")
        return self.readme(repository_name(parsed.path.strip("/")), context)

    def headers(self, context):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
        token = context.settings.github_token.get_secret_value()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, path: str, context, *, query=None, cache_kind=None):
        url = "https://api.github.com" + path + ("?" + urlencode(query) if query else "")
        key = hashlib.sha256(url.encode()).hexdigest()
        headers = self.headers(context)
        with Session(self.fetcher.engine) as db:
            cached = db.get(ApiCache, key) if cache_kind else None
        if cached is not None:
            headers["If-None-Match"] = cached.etag
        response, _, _, _ = self.fetcher.request(
            url,
            context,
            api=True,
            headers=headers,
            delay=(2.01 if context.settings.github_token.get_secret_value() else 6.01)
            if path.startswith("/search/")
            else 0,
        )
        if optout_headers(response.headers):
            raise PolicyBlocked("tdm_reserved")
        if response.status == 304 and cached is not None:
            return cached.payload
        if response.status != 200:
            raise PolicyBlocked("github_unavailable")
        try:
            raw = json.loads(response.body)
        except (ValueError, TypeError):
            raise PolicyBlocked("invalid_api_response") from None
        if not isinstance(raw, dict):
            raise PolicyBlocked("invalid_api_response")
        if cache_kind == "search":
            data = {
                "items": [metadata(item) for item in raw.get("items", [])[:100]],
                "total_count": int(raw.get("total_count", 0)),
            }
        elif cache_kind == "repository":
            data = metadata(raw)
        else:
            return raw
        etag = response.headers.get("etag", "")
        if etag and len(etag) <= 256 and not any(ord(c) < 32 for c in etag):
            with Session(self.fetcher.engine) as db, db.begin():
                db.merge(ApiCache(key=key, etag=etag, payload=data, updated_at=context.clock()))
        return data

    def search(self, skill: str, context, *, pages=1) -> list[dict]:
        if not 1 <= len(skill) <= 200 or not 1 <= pages <= 10:
            raise PolicyBlocked("invalid_search")
        found = {}
        floor = context.settings.github_min_stars
        for low, high in ((10000, None), (1000, 9999), (floor, 999)):
            low = max(low, floor)
            if high is not None and low > high:
                continue
            stars = f">={low}" if high is None else f"{low}..{high}"
            for page in range(1, pages + 1):
                result = self.data(
                    "/search/repositories",
                    context,
                    cache_kind="search",
                    query={
                        "q": f"{skill} is:public in:readme,description stars:{stars} pushed:>{context.settings.github_pushed_after.isoformat()}",
                        "sort": "stars",
                        "per_page": 100,
                        "page": page,
                    },
                )
                for item in result["items"]:
                    if not item["archived"] and not item["fork"] and item["stars"] >= floor:
                        found[item["full_name"]] = item
                if len(result["items"]) < 100:
                    break
        return sorted(found.values(), key=lambda r: (-r["stars"], r["full_name"]))

    def repository(self, name, context):
        return self.data("/repos/" + repository_name(name), context, cache_kind="repository")

    @staticmethod
    def decoded_file(body: bytes) -> bytes:
        try:
            data = json.loads(body)
            if data.get("encoding") != "base64":
                raise ValueError()
            return base64.b64decode("".join(data["content"].split()), validate=True)
        except (ValueError, KeyError, TypeError):
            raise PolicyBlocked("invalid_repository_file") from None

    def license(self, name, context, repo):
        license = License(repo["spdx"], 0.95, "github_api")
        if license.spdx.lower() not in {"unknown", "noassertion"}:
            return license
        try:
            data = self.data("/repos/" + repository_name(name) + "/license", context)
            return license_file(self.decoded_file(json.dumps(data).encode()))
        except PolicyBlocked:
            return License(evidence="license_unavailable")

    def tree(self, name, sha, context):
        repository_name(name)
        if not re.fullmatch(r"[a-fA-F0-9]{40,64}", sha):
            raise PolicyBlocked("invalid_git_sha")
        raw = self.data(f"/repos/{name}/git/trees/{sha}", context, query={"recursive": 1})
        return {
            "truncated": bool(raw.get("truncated")),
            "tree": [
                {"path": str(n.get("path", ""))[:1024], "type": n.get("type"), "sha": n.get("sha")}
                for n in raw.get("tree", [])[:10000]
                if n.get("type") in {"tree", "blob"}
            ],
        }

    def readme(self, name, context):
        repo = self.repository(name, context)
        license = self.license(name, context, repo)
        url = f"https://api.github.com/repos/{repository_name(name)}/readme"
        if not license.permits_storage:
            source_id = self.fetcher.candidate(url, context)
            return self.fetcher.finish(source_id, context, url, license=license)
        return self.fetcher.fetch(
            url,
            context,
            api=True,
            api_license=license,
            headers=self.headers(context),
            decode_body=self.decoded_file,
        )
