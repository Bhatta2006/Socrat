import hashlib
import json
import socket

import pytest

pytest.importorskip("protego")

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.foundry.acquisition.crawl4ai import Crawl4AIFetcher
from socrat.foundry.acquisition.github import GitHubClient
from socrat.foundry.acquisition.http import Fetcher
from socrat.foundry.acquisition.network import (
    PublicBackend,
    Response,
)
from socrat.foundry.acquisition.rate import Limiter
from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.compliance.licenses import License, license_file, page_signals
from socrat.foundry.compliance.urls import canonical_url, resolve_public
from socrat.foundry.jobs import (
    FoundryStopped,
    JobRequest,
    RetryableError,
    StageContext,
    claim,
    enqueue,
)
from socrat.foundry.models import (
    ApiCache,
    Chunk,
    Control,
    DomainPolicy,
    FetchRecord,
    Job,
    RobotsSnapshot,
    Source,
)
from socrat.foundry.storage import LocalStore, S3Store, object_key

ORIGIN = "https://docs.example.org"
PAGE = b'<html><head><link rel="license" href="https://creativecommons.org/licenses/by/4.0/"></head><body><h1>Learn SQL</h1><p>Use a select query.</p></body></html>'


class FixtureWire:
    live = False

    def __init__(self):
        self.calls = []
        self.routes = {
            "/robots.txt": Response(200, {}, b"User-agent: *\nAllow: /"),
            "/.well-known/tdmrep.json": Response(404, {}, b""),
            "/ai.txt": Response(404, {}, b""),
            "/lesson": Response(200, {"content-type": "text/html"}, PAGE),
        }

    def get(self, url, headers, timeout, max_bytes):
        self.calls.append((url, headers))
        route = self.routes.get(
            url, self.routes.get(canonical_url(url).path, Response(404, {}, b""))
        )
        response = route(url, headers) if callable(route) else route
        if len(response.body) > max_bytes:
            raise PolicyBlocked("response_too_large")
        return response


@pytest.fixture
def acquisition(engine, settings, clock, tmp_path):
    ticks = [float(clock.stamp)]
    settings = settings.model_copy(
        update={"max_docs_per_job": 100, "snapshot_directory": str(tmp_path / "objects")}
    )
    job_id = enqueue(engine, settings, JobRequest(slug="sql", title="SQL"))
    with Session(engine) as db, db.begin():
        db.add(DomainPolicy(domain="docs.example.org", mode="allow", tos_reviewed_at=clock.stamp))
        skill_id = db.get(Job, job_id).skill_id

    def sleep(seconds):
        ticks[0] += seconds

    wire = FixtureWire()
    limiter = Limiter(engine, clock=lambda: ticks[0], sleep=sleep)
    store = LocalStore(str(tmp_path / "objects"))
    with claim(engine, settings, lambda: int(ticks[0])) as lease:
        context = StageContext(lease, settings, lambda: int(ticks[0]), "S3", skill_id, {})
        yield Fetcher(engine, wire=wire, store=store, limiter=limiter), context, wire, ticks, store


@pytest.mark.parametrize(
    "spdx,category,stores",
    [
        ("CC-BY-4.0", "open_permissive", True),
        ("CC-BY-SA-4.0", "open_sharealike", True),
        ("CC-BY-NC-SA-4.0", "noncommercial", False),
        ("CC-BY-ND-4.0", "noderivs", False),
        ("MIT", "open_permissive", True),
        ("GPL-3.0-only", "open_sharealike", True),
        ("unknown", "unknown", False),
        ("NOASSERTION", "all_rights", False),
    ],
)
def test_license_policy_table(spdx, category, stores):
    license = License(spdx, 0.95, "fixture")
    assert license.category == category and license.permits_storage == stores
    assert not License(spdx, 0.5).permits_storage
    assert not License(spdx, float("nan")).permits_storage


def test_license_signals_require_machine_evidence_and_detect_conflicts():
    assert page_signals(PAGE)[0].permits_storage
    assert not page_signals(b"<footer>MIT</footer>")[0].permits_storage
    assert (
        page_signals(
            b'<script type="application/ld+json">{"license":"https://creativecommons.org/licenses/by-sa/4.0/"}</script>'
        )[0].category
        == "open_sharealike"
    )
    assert not page_signals(PAGE, License("MIT", 0.95, "api"))[0].permits_storage
    assert (
        license_file(
            b"Permission is hereby granted, free of charge... THE SOFTWARE IS PROVIDED"
        ).spdx
        == "MIT"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://10.0.0.1/",
        "http://[::1]/",
        "http://[fec0::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://168.63.129.16/",
        "http://[64:ff9b::a9fe:a9fe]/",
        "file:///etc/passwd",
        "https://user:password@example.org/",
        "https://example.org:5432/",
        "http://2130706433/",
        "https://example.local/",
        "https://example.org/?access_token=secret",
        "https://example.org\\@127.0.0.1/",
    ],
)
def test_ssrf_url_forms_are_rejected(url):
    with pytest.raises(PolicyBlocked):
        canonical_url(url)


def test_dns_rebinding_is_rechecked_and_numeric_address_pinned(monkeypatch):
    addresses = iter(["93.184.216.34", "169.254.169.254"])
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(addresses), 443))],
    )
    calls = []
    import httpcore

    monkeypatch.setattr(
        httpcore.SyncBackend, "connect_tcp", lambda self, host, *a: calls.append(host) or object()
    )
    import time

    backend = PublicBackend(time.monotonic() + 10)
    backend.connect_tcp("docs.example.org", 443, 5)
    with pytest.raises(PolicyBlocked, match="private_address"):
        backend.connect_tcp("docs.example.org", 443, 5)
    assert calls == ["93.184.216.34"]


def test_mixed_public_private_dns_answers_are_denied(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443)), (2, 1, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(PolicyBlocked, match="private_address"):
        resolve_public("docs.example.org", 443, 1)


def test_unknown_domain_is_metadata_only_without_network(acquisition):
    fetcher, ctx, wire, _, store = acquisition
    result = fetcher.fetch("https://unknown.example.org/lesson", ctx)
    assert result.policy == "link_only" and not result.body and not wire.calls
    with Session(fetcher.engine) as db:
        assert db.get(Source, result.source_id).fetched_at is None
        assert db.scalar(select(func.count()).select_from(FetchRecord)) == 0
    assert not list(store.root.glob("**/*"))


def test_disallowed_robots_never_fetches_page(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    wire.routes["/robots.txt"] = Response(200, {}, b"User-agent: SocratBot\nDisallow: /lesson*\n")
    result = fetcher.fetch(ORIGIN + "/lesson", ctx)
    assert result.policy == "link_only"
    assert not any(canonical_url(u).path == "/lesson" for u, _ in wire.calls)


def test_permitted_snapshot_has_provenance_and_cached_robots(acquisition):
    fetcher, ctx, wire, _, store = acquisition
    first = fetcher.fetch(ORIGIN + "/lesson", ctx)
    second = fetcher.fetch(ORIGIN + "/lesson", ctx)
    assert first.source_id == second.source_id and first.policy == "store"
    assert len([u for u, _ in wire.calls if u.endswith("/robots.txt")]) == 1
    with Session(fetcher.engine) as db:
        source = db.get(Source, first.source_id)
        assert store.get(source.raw_object_key, ctx) == PAGE
        assert source.content_hash == hashlib.sha256(PAGE).hexdigest()
        assert db.get(RobotsSnapshot, source.robots_snapshot_id).content_hash
        fetched = db.scalars(select(FetchRecord).where(FetchRecord.source_id == source.id)).all()
        assert len(fetched) == 2 and all(
            f.robots_snapshot_id and f.license_evidence and f.raw_object_key for f in fetched
        )


@pytest.mark.parametrize(
    "signal", ["header", "meta", "tdm", "ai", "unknown", "paywall", "captcha", "all_rights"]
)
def test_restricted_content_never_retains_text(acquisition, signal):
    fetcher, ctx, wire, _, store = acquisition
    if signal == "header":
        wire.routes["/lesson"] = Response(200, {"x-robots-tag": "noai"}, PAGE)
    if signal == "meta":
        wire.routes["/lesson"] = Response(
            200, {}, PAGE.replace(b"<head>", b'<head><meta name="robots" content="noai">')
        )
    if signal == "tdm":
        wire.routes["/.well-known/tdmrep.json"] = Response(200, {}, b'[{"tdm-reservation":1}]')
    if signal == "ai":
        wire.routes["/ai.txt"] = Response(200, {}, b"Do not train")
    if signal == "unknown":
        wire.routes["/lesson"] = Response(200, {}, b"Our private course material")
    if signal == "paywall":
        wire.routes["/lesson"] = Response(
            200,
            {},
            PAGE + b'<script type="application/ld+json">{"isAccessibleForFree": false}</script>',
        )
    if signal == "captcha":
        wire.routes["/lesson"] = Response(200, {}, PAGE + b"captcha")
    if signal == "all_rights":
        wire.routes["/lesson"] = Response(200, {}, PAGE + b"All rights reserved.")
    result = fetcher.fetch(ORIGIN + "/lesson", ctx)
    assert result.policy != "store" and not result.body
    assert not list(store.root.glob("sources/**/*"))
    with Session(fetcher.engine) as db:
        source = db.get(Source, result.source_id)
        assert not source.raw_object_key
        assert db.scalar(select(func.count()).select_from(Chunk)) == 0
        assert not any(db.scalars(select(FetchRecord.raw_object_key)))


def test_robots_cache_expires_after_24_hours(acquisition):
    fetcher, ctx, wire, ticks, _ = acquisition
    first = fetcher.robots(ORIGIN + "/lesson", ctx)
    assert fetcher.robots(ORIGIN + "/lesson", ctx).id == first.id
    # Expire the cached snapshot without changing the active job's wall clock.
    with Session(fetcher.engine) as db, db.begin():
        db.get(RobotsSnapshot, first.id).expires_at = ctx.clock()
    assert fetcher.robots(ORIGIN + "/lesson", ctx).id != first.id
    assert len(wire.calls) == 2


def test_redirect_to_metadata_is_never_requested(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    wire.routes["/lesson"] = Response(
        302, {"location": "http://169.254.169.254/latest/meta-data"}, b""
    )
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"
    assert not any("169.254" in u for u, _ in wire.calls)


def test_redirect_limit_and_size_caps(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    wire.routes["/lesson"] = Response(302, {"location": "/lesson"}, b"")
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"
    wire.routes["/lesson"] = Response(200, {}, b"x" * (ctx.settings.max_bytes + 1))
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"


def test_limiter_waits_and_honors_retry_after(acquisition):
    fetcher, ctx, _, ticks, _ = acquisition
    start = ticks[0]
    with fetcher.limiter.slot("docs.example.org", ctx):
        pass
    with fetcher.limiter.slot("docs.example.org", ctx):
        assert ticks[0] >= start + 2
    fetcher.limiter.feedback("docs.example.org", Response(429, {"retry-after": "30"}, b""))
    blocked_at = ticks[0]
    with fetcher.limiter.slot("docs.example.org", ctx):
        assert ticks[0] >= blocked_at + 30


def test_limiter_obeys_stricter_configured_concurrency(acquisition):
    from dataclasses import replace

    fetcher, ctx, _, ticks, _ = acquisition
    ctx = replace(ctx, settings=ctx.settings.model_copy(update={"max_concurrency_per_domain": 1}))

    def no_wait(seconds):
        raise RetryableError("slot_busy")

    limiter = Limiter(fetcher.engine, clock=lambda: ticks[0], sleep=no_wait)
    with limiter.slot("docs.example.org", ctx):
        ticks[0] += 2
        with pytest.raises(RetryableError, match="slot_busy"):
            with limiter.slot("docs.example.org", ctx):
                pytest.fail("second request exceeded the configured limit")
    with limiter.slot("docs.example.org", ctx):
        pass


def test_policy_revocation_removes_previously_permitted_snapshot(acquisition):
    fetcher, ctx, wire, _, store = acquisition
    first = fetcher.fetch(ORIGIN + "/lesson", ctx)
    with Session(fetcher.engine) as db:
        key = db.get(Source, first.source_id).raw_object_key
    wire.routes["/lesson"] = Response(200, {"x-robots-tag": "noai"}, PAGE)
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"
    assert not store.path(key).exists()
    with Session(fetcher.engine) as db:
        source = db.get(Source, first.source_id)
        assert source.status == "quarantined" and source.policy_decision == "link_only"
        assert not any(db.scalars(select(FetchRecord.raw_object_key)))


def test_live_network_is_not_possible_without_configuration(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    wire.live = True
    with pytest.raises(FoundryStopped, match="live_disabled"):
        fetcher.fetch(ORIGIN + "/lesson", ctx)
    assert not wire.calls


def test_kill_switch_checked_after_wait_before_fetch(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.get(Control, "global").kill_switch = True
    with pytest.raises(FoundryStopped, match="kill_switch"):
        fetcher.fetch(ORIGIN + "/lesson", ctx)
    assert not wire.calls


def test_crawl4ai_local_markdown_has_no_browser_requests(acquisition):
    import importlib.util
    import os

    if importlib.util.find_spec("crawl4ai") is None:
        pytest.skip("Install the optional foundry-markdown extra for this isolated adapter test")
    fetcher, ctx, wire, _, _ = acquisition
    before = {
        k: hashlib.sha256(v.encode()).hexdigest()
        for k, v in os.environ.items()
        if k.startswith(("SOCRAT_", "OPENAI_", "ANTHROPIC_", "NEBIUS_"))
    }
    result = Crawl4AIFetcher(fetcher).fetch(ORIGIN + "/lesson", ctx)
    assert before == {
        k: hashlib.sha256(v.encode()).hexdigest()
        for k, v in os.environ.items()
        if k.startswith(("SOCRAT_", "OPENAI_", "ANTHROPIC_", "NEBIUS_"))
    }
    assert "Learn SQL" in result.markdown and result.policy == "store"
    assert {canonical_url(u).path for u, _ in wire.calls} == {
        "/robots.txt",
        "/.well-known/tdmrep.json",
        "/ai.txt",
        "/lesson",
    }


def test_github_search_slices_stars_and_reuses_sanitized_etag_cache(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="api.github.com", mode="api_only", tos_reviewed_at=ctx.clock()))
    seen = []
    repo = {
        "full_name": "owner/course",
        "stargazers_count": 5000,
        "license": {"spdx_id": "MIT"},
        "description": "discard this unsanitized text",
        "readme": "never cache",
        "archived": False,
        "fork": False,
    }

    def search(url, headers):
        seen.append(url)
        if headers.get("If-None-Match"):
            return Response(304, {}, b"")
        return Response(
            200, {"etag": '"fixture"'}, json.dumps({"items": [repo], "total_count": 1}).encode()
        )

    wire.routes["/search/repositories"] = search
    client = GitHubClient(fetcher)
    assert len(client.search("sql", ctx)) == 1
    assert len(client.search("sql", ctx)) == 1
    assert len(set(seen)) == 3 and len(seen) == 6
    with Session(fetcher.engine) as db:
        assert "never cache" not in json.dumps([c.payload for c in db.scalars(select(ApiCache))])


def test_github_backoff_does_not_loop_or_log_remote_body(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="api.github.com", mode="api_only", tos_reviewed_at=ctx.clock()))
    wire.routes["/search/repositories"] = Response(
        403, {"retry-after": "60", "x-ratelimit-remaining": "0"}, b"secret token server error"
    )
    with pytest.raises(RetryableError):
        GitHubClient(fetcher).search("sql", ctx)
    assert len([u for u, _ in wire.calls if "/search/" in u]) == 1
    with Session(fetcher.engine) as db:
        assert db.get(DomainPolicy, "api.github.com").blocked_until >= fetcher.limiter.clock() + 60


def test_github_unknown_license_never_fetches_readme(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="api.github.com", mode="api_only", tos_reviewed_at=ctx.clock()))
    wire.routes["/repos/owner/course"] = Response(
        200, {}, json.dumps({"full_name": "owner/course", "license": None}).encode()
    )
    assert GitHubClient(fetcher).readme("owner/course", ctx).policy == "link_only"
    assert not any(u.endswith("/readme") for u, _ in wire.calls)


def test_s3_snapshot_adapter_uses_private_encrypted_objects(acquisition):
    _, ctx, _, _, _ = acquisition
    calls = []

    class Client:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    store = S3Store("fixture-bucket", client=Client(), live=False)
    key = object_key("fixture", PAGE)
    store.put(key, PAGE, ctx)
    assert calls[0]["ServerSideEncryption"] == "AES256" and "ACL" not in calls[0]
    assert calls[0]["Metadata"]["sha256"] == hashlib.sha256(PAGE).hexdigest()


def test_storage_cannot_escape_directory_or_accept_changed_bytes(acquisition):
    _, ctx, _, _, store = acquisition
    with pytest.raises(PolicyBlocked):
        store.path("../../escape")
    with pytest.raises(PolicyBlocked):
        store.put(object_key("fixture", PAGE), b"different", ctx)


def test_redirect_checks_destination_tdm_before_its_page(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="other.example.org", mode="allow", tos_reviewed_at=ctx.clock()))
    wire.routes["/lesson"] = Response(302, {"location": "https://other.example.org/private"}, b"")
    wire.routes["https://other.example.org/.well-known/tdmrep.json"] = Response(
        200, {}, b'[{"tdm-reservation":1}]'
    )
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"
    assert not any(u == "https://other.example.org/private" for u, _ in wire.calls)


def test_github_readme_and_tree_use_api_without_executing_content(acquisition):
    import base64

    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="api.github.com", mode="api_only", tos_reviewed_at=ctx.clock()))
    wire.routes["/repos/owner/course"] = Response(
        200, {}, json.dumps({"full_name": "owner/course", "license": {"spdx_id": "MIT"}}).encode()
    )
    body = b"# Learn\nNever execute this: os.remove('anything')"
    wire.routes["/repos/owner/course/readme"] = Response(
        200,
        {},
        json.dumps({"encoding": "base64", "content": base64.b64encode(body).decode()}).encode(),
    )
    sha = "a" * 40
    wire.routes[f"/repos/owner/course/git/trees/{sha}"] = Response(
        200,
        {},
        json.dumps(
            {
                "tree": [
                    {"path": "README.md", "type": "blob", "sha": sha},
                    {"path": "external", "type": "commit"},
                ]
            }
        ).encode(),
    )
    client = GitHubClient(fetcher)
    result = client.fetch("https://github.com/owner/course", ctx)
    assert result.policy == "store" and client.decoded_file(result.body) == body
    assert len(client.tree("owner/course", sha, ctx)["tree"]) == 1
    assert all(canonical_url(u).host == "api.github.com" for u, _ in wire.calls)
    assert any(h.get("X-GitHub-Api-Version") == "2026-03-10" for _, h in wire.calls)


def test_readme_restricted_file_license_overrides_repository_license(acquisition):
    import base64

    fetcher, ctx, wire, _, _ = acquisition
    with Session(fetcher.engine) as db, db.begin():
        db.add(DomainPolicy(domain="api.github.com", mode="api_only", tos_reviewed_at=ctx.clock()))
    wire.routes["/repos/owner/course"] = Response(
        200, {}, json.dumps({"full_name": "owner/course", "license": {"spdx_id": "MIT"}}).encode()
    )
    wire.routes["/repos/owner/course/readme"] = Response(
        200,
        {},
        json.dumps(
            {
                "encoding": "base64",
                "content": base64.b64encode(b"License: CC-BY-NC-SA-4.0").decode(),
            }
        ).encode(),
    )
    assert GitHubClient(fetcher).readme("owner/course", ctx).policy == "link_only"


def test_absolute_stream_deadline_caps_each_read(monkeypatch):
    from socrat.foundry.acquisition import network

    stamp = [100.0]
    monkeypatch.setattr(network.time, "monotonic", lambda: stamp[0])
    received = []

    class Stream:
        def read(self, size, timeout):
            received.append(timeout)
            return b"part"

    stream = network.DeadlineStream(Stream(), 102)
    assert stream.read(10, 20) == b"part" and received == [2]
    stamp[0] = 103
    with pytest.raises(PolicyBlocked, match="request_timeout"):
        stream.read(10, 20)


def test_policy_bootstrap_does_not_follow_unreviewed_redirect(acquisition):
    fetcher, ctx, wire, _, _ = acquisition
    wire.routes["/robots.txt"] = Response(
        301, {"location": "https://other.example.org/robots.txt"}, b""
    )
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "link_only"
    assert len(wire.calls) == 1


def test_failed_snapshot_write_is_journaled_and_recoverable(acquisition):
    fetcher, ctx, _, _, store = acquisition

    class FailedStore:
        def put(self, *args):
            raise OSError("private storage error must not be logged")

    fetcher.store = FailedStore()
    with pytest.raises(OSError):
        fetcher.fetch(ORIGIN + "/lesson", ctx)
    with Session(fetcher.engine) as db:
        records = db.scalars(
            select(FetchRecord).where(FetchRecord.raw_object_key.is_not(None))
        ).all()
        assert len(records) == 1 and records[0].source_id
        assert not db.get(Source, records[0].source_id).raw_object_key
    fetcher.store = store
    assert fetcher.fetch(ORIGIN + "/lesson", ctx).policy == "store"


def test_real_acquisition_stages_resume_without_duplicate_content(
    engine, settings, tmp_path, clock
):
    from socrat.foundry.acquisition.stages import acquisition_handlers
    from socrat.foundry.jobs import run_once

    settings = settings.model_copy(update={"snapshot_directory": str(tmp_path / "snapshots")})
    job_id = enqueue(
        engine,
        settings,
        JobRequest(
            slug="sql",
            title="SQL",
            payload={"urls": ["http://169.254.169.254/", ORIGIN + "/lesson"]},
        ),
    )
    with Session(engine) as db, db.begin():
        db.add(DomainPolicy(domain="docs.example.org", mode="allow", tos_reviewed_at=clock.stamp))
    ticks = [float(clock.stamp)]

    def sleep(seconds):
        ticks[0] += seconds

    wire = FixtureWire()
    stages = acquisition_handlers(
        engine, wire=wire, limiter=Limiter(engine, clock=lambda: ticks[0], sleep=sleep)
    )
    assert run_once(engine, settings, stages, clock=lambda: int(ticks[0]))
    calls = len(wire.calls)
    assert not run_once(engine, settings, stages, clock=lambda: int(ticks[0]))
    assert len(wire.calls) == calls
    with Session(engine) as db:
        assert db.get(Job, job_id).error_code == "stub_pipeline_complete"
        assert db.scalar(select(func.count()).select_from(Source)) == 1
        assert db.scalar(select(Source.policy_decision)) == "store"


def test_noai_headers_and_nested_paywalls_are_detected():
    from socrat.foundry.acquisition.network import optout_headers

    assert optout_headers({"x-robots-tag": "noai, index"})
    assert optout_headers({"tdm-reservation": "1"})
    assert page_signals(
        PAGE
        + b'<script type="application/ld+json">{"@graph":[{"isAccessibleForFree":false}]}</script>'
    )[2]
