# Course Foundry M2: compliance and acquisition

Date: 15 October 2026. Local implementation after [M1](course-foundry-m1.md). No push, deployment, frontend edits or learner publication. Five implementation phases remain: M3–M7.

## What changed

- Added a common resource-fetcher interface, HTTP acquisition, a GitHub REST client, and an optional Crawl4AI Markdown adapter. S2/S3 are wired into the separate worker for explicitly supplied smoke URLs; automatic discovery/resolution remains M4. Other unfinished stages still park the build as `needs_human`, never a published course.
- Added reviewed-domain policy checks, robots parsing and 24-hour snapshots, noai/TDM detection, license classification/evidence, and metadata-only handling for unknown/restricted rights. No unknown domain is fetched simply to find its license.
- Added a public-network transport that pins validated DNS results, retains the original TLS hostname, rechecks redirects, rejects private/metadata destinations, and bounds DNS waiting, bytes, redirects and socket deadlines. No proxy inheritance, cookies, browser execution, Git cloning, paywall/login/captcha bypass or transcript scraping.
- Added shared domain reservations for delay/concurrency/backoff, immutable fetch records, metadata-only ETag caching, and content-addressed local/S3 snapshot adapters. Only permitted bodies receive object keys; writes are journaled before upload. Policy revocation quarantines a source and removes retained objects/chunks before changing its storage permission.
- Added migration `0009_foundry_acquisition`, tests and optional dependency profiles. The API readiness head is updated; existing learner tables, curated packs, planner and mastery/assessment logic are unchanged.

## Files and boundaries

`services/api/src/socrat/foundry/compliance/` contains URL/IP checks, fixed failure reasons and licensing/signals. `acquisition/` contains the wire transport, shared rate limiter, HTTP/GitHub/Crawl4AI adapters and stage wiring. `storage.py` implements private snapshot storage. Existing Foundry config/models/jobs/worker add only the acquisition fields and entry points they need.

The migration adds `foundry_robots_snapshots`, `foundry_fetch_records`, `foundry_api_cache`, and rate/concurrency state to the existing domain policy rows. New columns have safe defaults for existing rows. The historical M1 migration is unchanged. SQLite/PostgreSQL migration tests now expect fifteen Foundry tables and continue proving rollback preserves existing users. No pgvector extension is installed.

Each resource hop rechecks its reviewed domain policy, robots rules and TDM reservation before the resource request. The policy bootstrap files themselves are the necessary exception to recursive robots checking: their requests still pass domain, destination, rate, budget and kill controls. Robots snapshots are scoped to origin and User-Agent, bounded in size and cached for at most 24 hours. Unavailable/denied policy files fail closed; robots 404/410 permits ordinary path evaluation. Non-empty `ai.txt` and unknown/malformed TDM rules require review rather than being interpreted as permission.

Robots parsing uses Protego's RFC 9309 matching and its crawl-delay/request-rate extensions. The effective delay is the stricter of configured and remote delays. Domain rows serialize token/lease updates across PostgreSQL workers; at most two requests are active per domain. Expiring leases recover from worker loss. Retry-After dates/seconds and quota reset headers feed the shared backoff. A wait beyond the job's remaining deadline yields to the existing bounded retry/parking mechanism.

Every outbound attempt reserves a document slot before sending, including redirects and policy probes. This conservatively counts control/API requests against the document cap. Requests use the lesser of their configured timeout and the active lease/job deadline. Failed attempts do not refund reservations. DNS lookup workers cannot open sockets and their results are discarded after timeout. Only validated numeric addresses reach TCP; all returned addresses must be public, excluding cloud metadata, mapped/transition/NAT64 and local/reserved destinations. HTTPS certificate/SNI verification uses the original hostname. Compressed responses are rejected rather than allowing decompression to evade the byte cap.

Fetch records retain the URL, time, status, selected non-secret headers, body hash when read, robots snapshot, pipeline, decision, license evidence and permitted object key. They do not retain response bodies for link-only/blocked material or API error bodies. Robots rule text is retained as the required policy snapshot, not learning content. API cache payloads contain only selected public repository metadata, never descriptions, README text, snippets or code.

The GitHub client uses public repositories and allow-listed REST endpoints only: search, repository metadata, README, LICENSE and trees. Searches slice by star bands, use conditional ETags and observe authenticated/unauthenticated pacing. README storage requires eligible repository/file rights, and decoded content is checked for conflicting rights/noai/restriction signals before retaining the raw API response. Files are decoded as data, never executed. Unknown licenses remain link-only. Other endpoints and cross-host API redirects cannot receive a token. Cloning remains deferred under the M0 REST-only decision.

Snapshot objects are scoped to source ID plus SHA-256, so deletion does not remove another source's copy. Local writes are atomic and path-checked; S3 writes omit public ACLs and request server-side encryption. S3 SDK retries are disabled so the job remains the retry owner. The operator-configured storage service is a separate trusted infrastructure boundary, not a URL discovered from source material. No real bucket was contacted during validation.

## Dependency profiles and the Crawl4AI exception

The default `foundry` extra pins HTTPcore **1.0.9**, Protego **0.7.0** and boto3 **1.43.114**, reusing HTTPX and the existing DB/config libraries. CI installs this profile and prevents later `uv run` steps from silently changing it. Existing base/runtime requirements remain unchanged; deployment of a separate acquisition worker must explicitly install the Foundry extra.

Crawl4AI **0.9.5** is pinned separately in `foundry-markdown`, excluded from the default worker and CI environment. Its NLTK **3.10.3** dependency is flagged by `pip-audit` for **PYSEC-2026-3740 / CVE-2026-81726**. The [upstream advisory](https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp) reports no patched version. The affected model import/export APIs are not called by this adapter, but this does **not** make the optional profile's dependency audit clean. No vulnerability ignore/waiver was added. Keep that optional profile out of a public deployment until the dependency issue is resolved and reviewed.

An initial test run also exposed Crawl4AI importing private dotenv settings into its caller. Three offline-provider assertions failed, and a synthetic tutor fixture made an unintended provider request. Credentials were not printed, and the fixture used temporary test data rather than production learner data. This side effect is fixed at the adapter boundary: there is no parent-process Crawl4AI import. Conversion runs in a bounded child process with a stripped environment, dotenv disabled, temporary library state and Python socket operations blocked. It consumes already-permitted HTML and returns bounded Markdown; it does not launch a browser or call a model. A targeted regression runs the adapter followed by those three offline-provider checks and verifies parent provider/credential environment hashes remain unchanged.

This subprocess boundary is not represented as an OS filesystem/network sandbox. It does not justify enabling arbitrary browser rendering or model-artifact APIs. Full parser isolation for PDF/notebook processing remains M3. Crawl4AI conversion was tested only with a synthetic local fixture; the default profile does not install Crawl4AI or NLTK at all.

The current official APIs were checked against installed signatures and these primary references: [HTTPcore network backends](https://www.encode.io/httpcore/network-backends/), [Protego](https://github.com/scrapy/protego), [Crawl4AI Markdown generation](https://docs.crawl4ai.com/core/markdown-generation/), [GitHub contents](https://docs.github.com/en/rest/repos/contents), [GitHub API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions), [TDMRep](https://www.w3.org/community/reports/tdmrep/CG-FINAL-tdmrep-20240510/) and [S3 put_object](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html). GitHub requests use the documented `2026-03-10` version. Static fetching uses the existing HTTP stack; no Scrapling/stealth dependency was introduced.

## How to run and test

From the repository root:

```powershell
uv sync --frozen --extra foundry
$foundryTemp = Join-Path (Get-Location).Path ('.cache/foundry-tests-' + [guid]::NewGuid().ToString('N'))
uv run --frozen --extra foundry pytest --basetemp $foundryTemp --cov=socrat --cov-fail-under=85
uv run --frozen --extra foundry ruff check services/api services/execution
uv run --frozen --extra foundry mypy services/api/src services/execution/src
uv run --frozen --extra foundry pip-audit
```

Set `SOCRAT_TEST_POSTGRES_URL` only to an authorized test server to include five PostgreSQL integration cases. Each owns a random schema and drops only that schema. Local checks use the existing disposable Foundry test cluster on loopback port 55438, not the project's service/database on 5432. Frontend checks are not part of this task.

Live acquisition is off by default. Before a manual `--live` smoke run, the operator must supply an actual bot information URL/contact, a dedicated Foundry database, reviewed domain/ToS policy rows, and snapshot storage. Use PostgreSQL for multiple workers. The credential field is `SOCRAT_FOUNDRY_GITHUB_TOKEN` or `_TOKEN_FILE`; never paste its value into a request, log or URL. S3 uses the SDK's operator-provided credential mechanism. No policy is automatically approved or created by this CLI.

After configuring those values privately and migrating that dedicated database, the explicit smoke command is:

```powershell
$env:PYTHONPATH = 'services/api/src;services/execution/src'
$env:SOCRAT_FOUNDRY_ENABLED = 'true'
$env:SOCRAT_FOUNDRY_LIVE_ENABLED = 'true'
uv run --frozen --extra foundry alembic upgrade head
uv run --frozen --extra foundry python -m socrat.foundry.worker --once --live --skill sql-basics --acquire-url https://approved-domain.example/approved-path
```

The example domain is a placeholder and must be replaced with an explicitly reviewed domain/path. The bot URL/contact and storage settings are required configuration, not generated defaults. Unknown domains produce only metadata with zero network requests. No live source crawl, GitHub search, bucket upload or model call is needed for the fixture-based M2 checks. A completed acquisition smoke job still parks for the remaining unimplemented stages.

## Acceptance and validation

| Criterion | Evidence |
|---|---|
| Disallowed robots path never fetched | Fixture checks include wildcard rules; no target request appears |
| noai/TDM and restricted rights | Header/meta/TDM/ai.txt, unknown license, paywall/captcha and conflicting file license checks retain no text/chunks/objects |
| SSRF | Private/metadata/reserved/mapped/transition URL cases, mixed DNS answers, rebinding and metadata redirects rejected before connecting |
| Shared rate limits | Deterministic delay/Retry-After checks and real PostgreSQL cross-worker slot exclusion/recovery |
| GitHub quotas/caching | Star-band searches, sanitized ETag/304 cache, rate-limit responses, public-only metadata and README/tree fixtures |
| Provenance/storage | Hash/robots/license linkage; atomic local snapshots; S3 request contract; journaled interrupted writes; revocation deletion |
| M1 integration | Real S2/S3 fixture pipeline skips an unsafe URL, stores the permitted resource once and does not re-run a completed request |
| Optional converter | Targeted isolated conversion plus three previously failing offline-provider checks passed; optional dependency audit remains blocked as described above |

Final validation results:

- Full default-profile backend suite: **319 passed, 25 skipped, 3 warnings in 197.16 seconds**; **88.99% coverage**, above the 85% gate. All five PostgreSQL integration tests passed. The skips are 24 dedicated gVisor cases and the optional Crawl4AI test. Log: `.cache/foundry-m2-verified-pytest.log` (local/untracked).
- Focused Foundry checks: **93 passed, 1 skipped** after the final rights-notice, configured-concurrency and secret-redaction regressions. A focused command initially hit Windows' inaccessible default pytest temp directory; rerunning with an explicit unique workspace `--basetemp` passed. The documented full command already uses that workaround.
- Optional converter isolation regression, run separately while its extra was installed: **4 passed**, including the three offline-provider checks that previously failed. The extra was then removed; the final default environment contains neither Crawl4AI nor NLTK.
- Default worker dependency audit: **no known vulnerabilities found**. The optional `foundry-markdown` profile remains flagged, with no ignore or waiver, as explained above.
- Ruff lint passed across both backend services. All 23 changed/new Python files pass formatting. Foundry mypy passed for 16 source files. Full-backend formatting/type checks still report the same **17 pre-existing unformatted files and two existing mypy errors** in `explainer/routes.py:105,136`; no overall clean type/format gate is claimed.
- SQLite/PostgreSQL migrations and reversals passed without losing existing fixture users; model metadata matches the migrated schema. No existing development/service database was migrated. Temporary PostgreSQL schemas were removed by fixtures; the owned test-only server was stopped after validation.
- Staged diff checks passed. Frontend files, curated packs, learner/planner/assessment code and remote branches are excluded from this milestone. No push or deployment was performed.

## Assumptions and next milestone

M2 acquires explicitly supplied URLs from reviewed domains. Automatic skill resolution/discovery is M4, after M3's cleaning, chunking, embedding and retrieval. M5 adds graph induction/export, M6 adds gates/review/status/takedown, and M7 measures calibration and quality. These are the five remaining phases; this milestone does not implement the first-enrollment trigger or promise course quality before those checks exist.

Before public acquisition: review domain policy and bot/storage configuration. Before optional Crawl4AI deployment: resolve the NLTK advisory. Before learner publication: the M0 Explorer/runtime contract decision and human quality review still apply. No source score, graph quality, retrieval relevance or learning outcome is claimed by M2. Stop after the local M2 commit for the owner's review; do not push.

Skipped: live crawling/cloud uploads, frontend checks and OS browser/parser sandbox deployment. The optional Crawl4AI dependency profile still has a known unpatched advisory and is not part of the default worker.
