import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Protocol
from urllib.parse import urljoin

from protego import Protego
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from socrat.foundry.acquisition.network import PublicWire, Wire, optout_headers
from socrat.foundry.acquisition.rate import Limiter, policy
from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.compliance.licenses import License, page_signals
from socrat.foundry.compliance.urls import canonical_url
from socrat.foundry.jobs import RetryableError
from socrat.foundry.models import Chunk, FetchRecord, RobotsSnapshot, Source
from socrat.foundry.storage import LocalStore, SnapshotStore, object_key
from socrat.models import identifier

SAFE_HEADERS = {"content-type", "etag", "last-modified", "x-robots-tag", "tdm-reservation"}
CONTROL_PATHS = {"/robots.txt", "/.well-known/tdmrep.json", "/ai.txt"}


@dataclass(frozen=True)
class Fetched:
    source_id: str
    url: str
    policy: str
    license: License
    body: bytes = b""
    markdown: str = ""


class ResourceFetcher(Protocol):
    def fetch(self, url: str, context) -> Fetched: ...


class Fetcher:
    def __init__(
        self,
        engine,
        *,
        wire: Wire | None = None,
        store: SnapshotStore | None = None,
        limiter: Limiter | None = None,
    ):
        self.engine = engine
        self.wire = wire or PublicWire()
        self.store = store
        self.limiter = limiter or Limiter(engine)

    def permitted(self, url, *, api=False):
        url = canonical_url(str(url))
        if api and (url.host != "api.github.com" or url.scheme != "https"):
            raise PolicyBlocked("unrecognized_api")
        if (
            api
            and url.path not in CONTROL_PATHS
            and not re.fullmatch(
                r"/search/repositories|/repos/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}(?:/(?:readme|license|git/trees/[a-fA-F0-9]{40,64}))?",
                url.path,
            )
        ):
            raise PolicyBlocked("unrecognized_api_endpoint")
        with Session(self.engine) as db:
            policy(db, url.host, api=api)
        return url

    def request(
        self,
        url,
        context,
        *,
        api=False,
        controls=False,
        headers=None,
        delay=0,
        robots_id=None,
        source_id=None,
    ):
        current = self.permitted(url, api=api)
        first_host = current.host
        for _ in range(context.settings.max_redirects + 1):
            current = self.permitted(current, api=api)
            if controls and current.path not in CONTROL_PATHS:
                raise PolicyBlocked("control_redirect")
            if not controls:
                robots = self.robots(current, context, api=api)
                robots_id = robots.id
                parser = Protego.parse(robots.body)
                if robots.status not in {200, 404, 410} or not parser.can_fetch(
                    str(current), context.settings.user_agent
                ):
                    raise PolicyBlocked("robots_disallowed")
                if not self.tdm_allowed(current, context, api=api):
                    raise PolicyBlocked("tdm_reserved")
                crawl_delay = parser.crawl_delay(context.settings.user_agent) or 0
                rate = parser.request_rate(context.settings.user_agent)
                delay = max(delay, crawl_delay, rate.seconds / rate.requests if rate else 0)
            with self.limiter.slot(current.host, context, api=api, delay=delay):
                # Re-read policy/kill/budgets after waiting, immediately before this attempt.
                self.permitted(current, api=api)
                context.reserve(documents=1, live=self.wire.live)
                sent = {"User-Agent": context.settings.user_agent, "Accept-Encoding": "identity"}
                if headers and current.host == first_host:
                    sent.update(headers)
                response = self.wire.get(
                    str(current),
                    sent,
                    min(context.settings.request_timeout_seconds, context.remaining_seconds()),
                    min(context.settings.max_bytes, 512000)
                    if controls
                    else context.settings.max_bytes,
                )
                self.limiter.feedback(current.host, response)
            record = FetchRecord(
                id=identifier(),
                job_id=context.lease.job_id,
                source_id=source_id,
                url=str(current),
                fetched_at=context.clock(),
                status=response.status,
                headers={k: v[:512] for k, v in response.headers.items() if k in SAFE_HEADERS},
                content_hash=hashlib.sha256(response.body).hexdigest() if response.body else None,
                robots_snapshot_id=robots_id,
                pipeline_version=context.settings.pipeline_version,
                policy_decision="link_only",
                reason="control_response" if controls else "pending_policy",
            )
            with Session(self.engine) as db, db.begin():
                db.add(record)
                db.flush()
                record_id = record.id
            if response.status in {301, 302, 303, 307, 308}:
                destination = canonical_url(
                    urljoin(str(current), response.headers.get("location", ""))
                )
                if controls and (
                    destination.host != first_host or destination.path != current.path
                ):
                    raise PolicyBlocked("control_redirect")
                if api and destination.host != first_host:
                    raise PolicyBlocked("api_redirect")
                current = destination
                continue
            if (
                response.status == 429
                or response.status >= 500
                or (
                    response.status == 403
                    and (
                        "retry-after" in response.headers
                        or response.headers.get("x-ratelimit-remaining") == "0"
                    )
                )
            ):
                raise RetryableError("remote_backoff")
            return response, record_id, str(current), robots_id
        raise PolicyBlocked("redirect_limit")

    def robots(self, url, context, *, api=False):
        url = self.permitted(url, api=api)
        origin = str(url.copy_with(path="/", query=None, fragment=None)).rstrip("/")
        with Session(self.engine) as db:
            cached = db.scalar(
                select(RobotsSnapshot)
                .where(
                    RobotsSnapshot.origin == origin,
                    RobotsSnapshot.expires_at > context.clock(),
                    RobotsSnapshot.user_agent == context.settings.user_agent,
                )
                .order_by(RobotsSnapshot.fetched_at.desc())
            )
            if cached is not None:
                return cached
        response, record_id, _, _ = self.request(
            origin + "/robots.txt", context, api=api, controls=True
        )
        body = response.body.decode("utf-8", "replace") if response.status == 200 else ""
        status = 403 if optout_headers(response.headers) else response.status
        snapshot = RobotsSnapshot(
            id=identifier(),
            origin=origin,
            user_agent=context.settings.user_agent,
            fetched_at=context.clock(),
            expires_at=context.clock() + context.settings.robots_cache_seconds,
            status=status,
            body=body,
            content_hash=hashlib.sha256(response.body).hexdigest(),
            pipeline_version=context.settings.pipeline_version,
        )
        with Session(self.engine, expire_on_commit=False) as db, db.begin():
            db.add(snapshot)
            db.flush()
            db.get_one(FetchRecord, record_id).robots_snapshot_id = snapshot.id
        return snapshot

    def tdm_allowed(self, url, context, *, api=False):
        url = canonical_url(str(url))
        origin = str(url.copy_with(path="/", query=None, fragment=None)).rstrip("/")
        for path in ("/.well-known/tdmrep.json", "/ai.txt"):
            target = origin + path
            snapshot = self.robots(target, context, api=api)
            if snapshot.status not in {200, 404, 410} or not Protego.parse(snapshot.body).can_fetch(
                target, context.settings.user_agent
            ):
                return False
            response, _, _, _ = self.request(
                target, context, api=api, controls=True, robots_id=snapshot.id
            )
            if optout_headers(response.headers):
                return False
            if response.status in {404, 410}:
                continue
            if response.status != 200:
                return False
            if path == "/ai.txt":
                # There is no adopted permissive syntax here; a non-empty reservation is reviewed.
                if response.body.strip():
                    return False
            else:
                try:
                    value = json.loads(response.body)
                    entries = value if isinstance(value, list) else [value]
                    if not entries or any(
                        not isinstance(e, dict) or str(e.get("tdm-reservation", "1")) != "0"
                        for e in entries
                    ):
                        return False
                except ValueError:
                    return False
        return True

    def candidate(self, url: str, context) -> str:
        url = str(canonical_url(url))
        with Session(self.engine) as db, db.begin():
            source = db.scalar(
                select(Source).where(
                    Source.skill_id == context.skill_id, Source.canonical_url == url
                )
            )
            if source is None:
                source = Source(
                    id=identifier(),
                    skill_id=context.skill_id,
                    url=url,
                    canonical_url=url,
                    pipeline_version=context.settings.pipeline_version,
                )
                db.add(source)
                db.flush()
            return source.id

    def fetch(
        self,
        url: str,
        context,
        *,
        api_license: License | None = None,
        api=False,
        headers=None,
        decode_body=None,
    ) -> Fetched:
        url = str(canonical_url(url))
        source_id = self.candidate(url, context)
        try:
            self.permitted(url, api=api)
            response, record_id, final_url, robots_id = self.request(
                url, context, api=api, headers=headers, source_id=source_id
            )
            if response.status != 200:
                return self.finish(
                    source_id,
                    context,
                    final_url,
                    record_id=record_id,
                    robots_id=robots_id,
                    reason="access_denied",
                    blocked=response.status in {401, 403},
                )
            license, optout, restricted = page_signals(
                decode_body(response.body)
                if decode_body and not optout_headers(response.headers)
                else response.body,
                api_license,
            )
            if optout_headers(response.headers) or optout or restricted:
                return self.finish(
                    source_id,
                    context,
                    final_url,
                    record_id=record_id,
                    robots_id=robots_id,
                    reason="restricted_source",
                    blocked=restricted,
                )
            return self.finish(
                source_id,
                context,
                final_url,
                license=license,
                body=response.body,
                record_id=record_id,
                robots_id=robots_id,
            )
        except PolicyBlocked as exc:
            return self.finish(
                source_id, context, url, reason=str(exc), blocked=str(exc) == "domain_blocked"
            )

    def finish(
        self,
        source_id,
        context,
        url,
        *,
        license=License(),
        body=b"",
        record_id=None,
        robots_id=None,
        reason="license_policy",
        blocked=False,
    ):
        context.reserve()
        decision = "blocked" if blocked else "store" if license.permits_storage else "link_only"
        key = object_key(source_id, body) if decision == "store" else None
        store = self.store or LocalStore(context.settings.snapshot_directory)
        if decision != "store":
            with Session(self.engine) as db, db.begin():
                source = db.get_one(Source, source_id, with_for_update=True)
                keys = {
                    key
                    for key in db.scalars(
                        select(FetchRecord.raw_object_key).where(
                            FetchRecord.source_id == source_id,
                            FetchRecord.raw_object_key.is_not(None),
                        )
                    )
                    if key is not None
                }
                if source.raw_object_key:
                    keys.add(source.raw_object_key)
                if keys:
                    source.status = "quarantined"
            for old_key in keys:
                store.delete(old_key, context)
        # Journal the permitted object key BEFORE writing, so a crash cannot orphan an untracked copy.
        with Session(self.engine) as db, db.begin():
            source = db.get_one(Source, source_id, with_for_update=True)
            if decision != "store":
                db.execute(delete(Chunk).where(Chunk.source_id == source_id))
                for old in db.scalars(
                    select(FetchRecord).where(FetchRecord.source_id == source_id)
                ):
                    old.raw_object_key = None
                source.raw_object_key = None
            source.policy_decision = decision
            source.license_spdx, source.license_url = license.spdx, license.url or None
            source.license_class, source.license_confidence = license.category, license.confidence
            source.license_evidence = {"signal": license.evidence}
            source.pipeline_version = context.settings.pipeline_version
            source.last_checked_at = context.clock()
            if record_id:
                source.fetched_at, source.robots_snapshot_id = context.clock(), robots_id
                fetch = db.get_one(FetchRecord, record_id)
                source.content_hash = fetch.content_hash
                source.link_status = fetch.status
                fetch.license_evidence = asdict(license)
                fetch.policy_decision, fetch.raw_object_key, fetch.reason = decision, key, reason
        if key:
            store.put(key, body, context)
            with Session(self.engine) as db, db.begin():
                source = db.get_one(Source, source_id, with_for_update=True)
                source.raw_object_key = key
        return Fetched(source_id, url, decision, license, body if decision == "store" else b"")
