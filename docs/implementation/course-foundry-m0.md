# Course Foundry: M0 reconnaissance and proposed plan

Date: 15 October 2026. Inspected baseline: `redefined` at `7e8d54d`.
Status: M0 report; implementation and the proposals below await owner approval.

## Request and boundaries

The pasted implementation request authorizes M0 first and requires a stop before code. The attached Course Foundry v0.1 design is reference material, narrowed by that request. The repository's [V1 PRD](../product/v1-product-requirements.md), dated 29 September 2026, is the product contract; no separately attached PRD was supplied. Design-file SHA-256: `43c5e80dbc5760bb1808492c55bd95a797421f72b9a9b9da783d48f8470e3448`.

The owner's additional restriction is **no frontend file changes**. All of `apps/web/` stays outside this work. There is already a generated change in `apps/web/next-env.d.ts`; it predates M0 and must remain unstaged and unmodified by this work.

M0 adds only this report. No Foundry code, migrations, dependencies, feature activation, content import, learner writes, or publication is authorized yet. The running local demo need not be stopped. The later milestones exclude generated practice, assessment authoring, Guided/Verified tiers, video/transcript acquisition, and changes to the learner model, planner, mastery rules, assessment engine, or curated DSA content.

## 1. Discovered implementation

| Area | What actually exists | Consequence for the Foundry |
|---|---|---|
| Backend | Python 3.12.14; FastAPI app factory in `services/api/src/socrat/main.py`; modular Python packages | Add `socrat.foundry` inside the backend, with a separately launched worker |
| Locked dependencies | FastAPI 0.141.1, SQLAlchemy 2.1.1, Alembic 1.20.0, Pydantic 2.13.5, HTTPX 0.28.1, psycopg 3.3.6, OpenAI 2.54.0, Anthropic 1.12.1 | Reuse installed libraries; `uv.lock` and `uv sync --frozen` are authoritative |
| Database | `database.make_engine`; PostgreSQL required in staging/production; the running Windows demo uses SQLite/WAL | Foundation models/migrations must retain SQLite compatibility; PostgreSQL-only guarantees need separate tests |
| PostgreSQL | Local Compose uses `postgres:17-alpine`; staging pins PostgreSQL 17.10. A local PostgreSQL process listens on 5432 | A listening server does not establish credentials, extension availability, or permission to install pgvector; those remain unverified |
| Models and migrations | SQLAlchemy `Mapped` models, string UUIDs from `identifier()`, integer UTC epoch times, portable `JSON`; Alembic head `0007_learning_sessions` | Add Foundry-owned tables after that head; register their metadata in migration setup; update `schema_revision.py` when the head changes |
| Outbox | `database.record_event` writes audit + outbox rows in the caller's transaction; `worker.drain_once` locks batches with `skip_locked` and marks delivery | This is a transactional outbox consumer, **not** an extensible pipeline/job queue; do not replace its delivery behavior |
| Durable work precedent | `judge.service.claim` leases queued `Submission` rows with row locking and worker ownership | Reuse the transaction/claim pattern for Foundry jobs, without sharing judge tables or credentials |
| LLM gateway | `assistant/gateway.py`: provider-neutral `Provider`, `make_provider`, tool-free `complete`, OpenAI/Anthropic SDK clients, secret-safe errors | Reuse provider configuration and clients; a bounded structured-result method with usage accounting is still needed |
| Current gateway limits | `Event` has no token-usage event; `complete` returns text only; OpenAI `converse` accepts `response_format`, Anthropic's current wrapper does not | Existing streaming completion alone cannot enforce all Foundry JSON/usage guarantees; add a backward-compatible gateway entry point, with no tools |
| Configuration/secrets | Pydantic Settings, `SOCRAT_` prefix, private `.env`, `SecretStr`, `_secret_from_file`; deployment rejects unsafe settings | Add Foundry configuration alongside these patterns; do not inspect or log actual credentials |
| Courses | `catalog/schema.py` defines strict Pydantic `Course`, `Concept`, `Resource`, `QuizItem`; `catalog/registry.py` loads YAML and validates a global DAG | This is the active authoring contract, not the historical full PRD skill-pack contract |
| Inventory | `content/courses/{zero,dsa,cp}`: respectively 18/23/20 concepts and 27/36/22 problems. DSA is version 1.0.0 | Read DSA only for the held-out M7 evaluator; do not regenerate or edit it |
| Registry/release | `default_catalog()` is cached; YAML folder discovery includes every `course.yaml` under the content root; catalog digest detects changes | Never export drafts beneath the live content root; an approved DB row would not automatically update this catalog |
| Review path | `admin/drafts.py` validates **problem** drafts, records reviewer/date, and moves approved files into courses for a later commit/build/deploy | Reuse admin authentication/audit conventions; this is not a course/edge review interface and must not receive Foundry output |
| Retrieval/storage | No vector index, embedder, full-text retrieval service, or ingestion object-store adapter found | Storage and retrieval are additions, not existing services to wire up |
| Proposed scraping packages | Scrapling, Crawl4AI, Trafilatura, Docling, pgvector, boto3 are not installed | No dependency installation in M0/M1; pin only the packages actually adopted in their later milestone |
| Tests | pytest, fixtures owning migrated temporary SQLite DBs, fake SDK clients in `test_gateway.py`; dedicated gVisor tests explicitly opt in | Extend these patterns with fixtures and deterministic `LLMClient`/`Embedder` fakes; no live acquisition/provider calls in unit tests |
| CI | `.github/workflows/ci.yml`: Ruff format/lint, mypy, pytest with 85% coverage gate, PostgreSQL migration/restore, content validation, web build/typecheck/E2E, security checks | Add explicit PostgreSQL concurrency/vector tests; current active backend tests do not consume the PostgreSQL test URL advertised by archived docs |

The archived M2 guide names `socrat.skillpacks`, `contracts/schemas/skill-pack.schema.json`, JSON pack fixtures and a full editorial lifecycle. Those modules/schema/fixtures are absent from this checkout. [ADR-0003](../architecture/adr/0003-versioned-skill-pack-contract.md) is still marked Proposed. Existing atom/session JSON schemas cover teaching atoms and API payloads; they are not substitutes for the missing pack contract. Several documentation links still point to pre-archive paths. The plan follows executable code rather than assuming that older documentation describes current capabilities.

## 2. Conflicts requiring a decision

| Conflict | Evidence | Concrete proposal, pending approval |
|---|---|---|
| Explorer versus PRD release contract | PRD §§11.2–11.4, 33 and 36.3 require reviewed content/assessment coverage and gated later-pack release; Foundry Explorer intentionally has no assessments | Build an internal draft/review system. Keep learner publication disabled until Product approves an Explorer exception or a separate compatible contract. Human draft approval alone does not waive PRD release requirements |
| M6 requires unchanged-planner selection | `Concept` requires a lesson, at least two resources and two quiz items. `planner.engine.concept_activities` always creates a quiz; `build_plan` adds mastery-dependent checkpoints | Revise that acceptance criterion to human-approved, versioned Explorer export/status only. Defer learner selection to separately approved work. Do not invent quizzes, set mastery, bypass checkpoints or quietly change planner logic |
| Missing full pack schema | Only current Course/atom/session schemas exist; the historical skill-pack schema is missing | Approve the draft manifest proposal in section 5. It is an authoring contract, not a claim that the current learner runtime can load Explorer packs |
| PostgreSQL design versus SQLite demo | Advisory locks, pgvector and generated `tsvector` are PostgreSQL features | Keep M1 portable; use PostgreSQL for multi-worker/live Foundry operation. SQLite supports deterministic single-worker development only; no claim of multi-worker equivalence |
| Store every raw response versus metadata-only rules | Design S3 saves raw HTML/PDF; request rules 2–3 forbid storage for restricted/unknown licenses or unreviewed domains | Persist bodies, snippets, contextualizations and embeddings only after access and license permission. Link-only retains metadata and policy evidence, never response text; byte hashes are allowed audit data. Unknown domains do not get content fetched merely to classify them |
| `store_internal` exception | Design S5 suggests a policy override; request requires fail-closed rights handling | A domain mode never overrides missing rights. Any written permission must be separately recorded and reviewed before storage is authorized |
| GitHub REST-only versus clone | M2 calls the client REST-only but also mentions `git clone --depth 1` | Start with REST search, README, tree and content endpoints only. Treat cloning as an explicit later exception, not a hidden subprocess escape hatch |
| Early diagnostic/starter path | Design §4.3 suggests diagnostics and resources before full review; request forbids generated assessment content and automatic publication | Return waiting/build status only. No generated diagnostic or unreviewed starter course |

These are open decisions, not implemented deviations. M1 can establish isolated foundations without resolving a learner runtime contract; M5 export needs manifest approval, and the original M6 learner-selection criterion remains blocked.

## 3. Proposed package and integration scope

Use the same Python environment and database, with `foundry_` table names to make ownership explicit. Launch the pipeline as `python -m socrat.foundry.worker`; leave `socrat.worker` and `runner.worker` unchanged. Do not add Redis, Celery, another vector database or a new learner system.

Proposed files appear only when their milestone needs them:

```text
services/api/src/socrat/foundry/
  __init__.py
  config.py                 # budgets, disabled-by-default live operation, tiers
  models.py                 # Foundry-owned SQLAlchemy models on the existing Base
  jobs.py                   # claims, checkpoints, reservations, retry/park logic
  worker.py                 # separate process; committed work is resumable
  clients.py                # LLMClient, Embedder, result/usage contracts
  compliance/               # policy, robots/TDM, rights, URL/network guard
  acquisition/              # HTTPX/GitHub; isolated allow-listed rendering
  storage.py                # permitted snapshots; local test/dev and object storage
  indexing.py               # extraction, sanitizer, chunks, hybrid retrieval
  discovery.py              # skill resolution, source discovery and scoring
  graph.py                  # candidate DAG, evidence, alignment, coverage gaps
  manifest.py               # strict draft contract and export
  review.py                 # gates, human decisions, takedown, audit
  routes.py                 # additive request/status endpoints only
  cli.py                    # worker operations and human review; no frontend
services/api/tests/foundry/
  fixtures/                 # permitted/licensed synthetic records, injected pages
  conftest.py               # migrated DBs, fake clients, clocks and transports
  test_*.py
services/api/migrations/versions/0008_foundry_foundations.py
contracts/schemas/foundry-draft-skill-pack.schema.json
scripts/content/evaluate_foundry.py
docs/implementation/course-foundry-m0.md
foundry/REPORT.md            # M7 measured results, not a new runtime package
```

Changes outside the new package must be narrowly additive:

- M1: Alembic metadata registration in `migrations/env.py`, new revisions and `schema_revision.py`; tests and CI configuration. No existing learner table migration/backfill.
- M2–M3: Python dependency declarations/lock when a chosen parser or storage/vector adapter is introduced; worker-only runtime/container configuration where required. No changes to web dependencies.
- M3: a structured, tool-free gateway operation in `assistant/gateway.py`, plus gateway regression tests. Existing tutor APIs/callers retain their behavior.
- M4/M6: router registration in `main.py`, using existing session/admin/CSRF checks. A separate skill-request/waitlist record can reference a user; do not invoke current enrollment/placement until an approved usable pack exists.
- M5–M7: new manifest/schema/fixtures, isolated exports and evaluation scripts. No export to `content/courses`, no call to `scripts/content/build.py` on acquired material, and no use of authoring validators that execute references/generators.

Scope checked includes callers, test fixtures, schema exports, migration metadata, readiness revision, configuration, worker entry points and CI. Existing course/quiz/assessment/planner callers are read-only inspection points, not implementation targets.

## 4. Proposed migrations and persistence guarantees

Revision numbers beyond M1 are provisional; re-check Alembic head before each milestone.

| Milestone/revision | Additions |
|---|---|
| M1 / `0008_foundry_foundations` | Design §7 entities as `foundry_skills`, `foundry_jobs`, `foundry_domain_policies`, `foundry_sources`, `foundry_chunks`, `foundry_concepts`, `foundry_concept_edges`, `foundry_resource_alignments`, `foundry_takedown_requests`, `foundry_skill_pack_versions`; narrow `foundry_stage_runs` and `foundry_controls` tables for durable checkpoints and global kill/budget controls. No practice candidates |
| M2 / compliance provenance | Immutable robots snapshots and fetch records, with status/allow-listed headers, license/policy evidence, hashes and permitted object keys. Domain rows hold rate/concurrency lease state, with expirations and serialized reservation |
| M3 / PostgreSQL retrieval | Only after confirming extension support/permission and embedding model/dimension: vector columns/indexes and full-text generated column/GIN index. No unconditional extension installation in the shared M1 migration |
| M4 / resolver | Unique normalized skill aliases and separate requester/waitlist references; no mutation to existing enrollment/evidence rows |
| M6 / review | Append-only review decisions bound to manifest/graph digest, and derived-artifact/source dependencies needed for complete takedown and re-gating |

Reuse string UUIDs, UTC epoch timestamps and portable JSON. Embedding dimensions and provider/model/version are explicit; do not hard-code the design's 1024 dimensions without selecting an embedder. A PostgreSQL retrieval migration must fail clearly when prerequisites are absent; SQLite fake retrieval must not be advertised as production HNSW/FTS coverage.

Important constraints to encode and test:

- Canonical skill slug and normalized alias are unique. Enqueue locks the skill; at most one non-terminal build exists per skill. Published/rejected/completed work is not overwritten by a refresh.
- PostgreSQL claims use short `FOR UPDATE SKIP LOCKED` transactions, a per-skill advisory lock on a dedicated connection, and durable job ownership/lease generation. Stale workers cannot checkpoint after a replacement takes ownership. Never hold an ordinary ORM transaction open over network/model calls. Advisory locks alone do not make retries idempotent. [PostgreSQL locking](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS), [SQLAlchemy 2.1 locking](https://docs.sqlalchemy.org/en/21/core/selectable.html#sqlalchemy.sql.expression.GenerativeSelect.with_for_update).
- Store the last completed stage and a stage-input digest; resume at the next incomplete stage. Stage effects and checkpoint commit together. Content hashes combine with pipeline/prompt/model versions and policy revisions; unchanged bytes do not bypass a new rights restriction.
- Reserve document/token/time budgets before external work, including worst-case model output and retries. Failed calls/partial responses cannot reset spend. Cumulative elapsed time survives restarts. Three failed attempts park the stage/job as `needs_human`; retryable work records `next_attempt_at` and bounded backoff. A policy-denied URL records a decision and is skipped, not repeatedly retried.
- A freshly read global DB control and environment disable flag apply before every outbound request and LLM/embedding/rerank call; unavailable controls fail closed. The embedding and rerank adapters are also budgeted external calls. Share rate and daily reservations across workers.
- Source/chunk provenance includes canonical URL, fetch time, body hash when fetched, license evidence/confidence, policy decision/revision, pipeline version and robots snapshot reference. Immutable fetch records preserve the evidence behind a particular chunk even after refresh. Unfetched metadata-only discoveries explicitly record that no fetch/hash/snapshot exists.
- Source identity is unique per canonical skill/URL. Chunk ordinal/hash/pipeline generation is unique; graph IDs/edges are scoped to a version. Finite confidence/support/relevance values are bounded to 0–1; edge endpoints must belong to the same graph version; no self-edges.
- The design's nullable `chunk_id` cannot be part of a primary key for link-only alignments. Use a surrogate ID and separate uniqueness constraints/indexes for whole-resource and chunk alignments.
- Link-only/blocked sources cannot acquire chunks or persisted raw/derived text. Policy tightening quarantines retrieval immediately and schedules removal of previously permitted derivatives. Retrieval filters source state/rights before ranking, including caches.
- Downgrades remove only Foundry-owned structures in reverse dependency order and leave existing learner data intact. Never drop a shared vector extension in downgrade. Upgrade/downgrade tests use disposable SQLite/PostgreSQL databases, not the running demo DB.

## 5. Proposed draft manifest contract

Approve a new strict `FoundryDraftSkillPack` schema before M5; export it from Pydantic as `contracts/schemas/foundry-draft-skill-pack.schema.json`, following the repo's generated-schema convention. Reuse compatible slug/reference/URL and semantic-version conventions. Do not relax `Course.Concept.quiz` or pass an empty assessment bank off as a valid published Course.

Proposed required fields and limits:

| Field | Proposed contract |
|---|---|
| `schema_version`, `pipeline_version`, `build_id`, `content_digest` | Exact version and immutable identity; digest binds review decisions to the complete payload |
| `status`, `tier_proposal`, `learner_selectable` | Literal `draft`, literal `explorer`, literal `false` for machine exports; publication is a separate human-controlled record |
| `skill` and `version` | Stable skill ID/slug/title, scope/exclusions, English content language, domain type, aliases and semantic version |
| `goal_templates` | Draft observable outcomes and scope; no learner enrollment or inferred mastery |
| `concepts` | Stable IDs, observable objectives, difficulty/time estimates, misconceptions, support/confidence, explicit source evidence and review flags |
| `prerequisite_edges` | Endpoints, support/confidence, `origin=sources|llm`, ordering evidence, review state; DAG validation plus documented cycle removals/transitive reduction |
| `resources`, `resource_alignments` | URLs, creators, license/permission/attribution, policy/provenance, scores and criterion evidence; no copied text for link-only sources |
| `tools`, `exercise_types`, `assessment_blueprints`, `mastery_policy`, `track_policies` | Explicit unsupported/empty/null values for this draft where no reviewed artifact exists; no generated assessments or executable plugins |
| `gate_report`, `coverage_gaps`, `limitations`, `review_requirements` | Compliance, captured rights, correctness score floor of 3, coverage, link health and safety outcomes; unresolved items stay visible |

The eight scoring criteria are exactly PRD §20.2: authority/correctness, exact-objective relevance, freshness, prerequisite/difficulty fit, clarity/accessibility, active-learning value, redundancy, and rights/availability/tracking risk. The design's differently worded rubric and reversed "accuracy risk" scale must not silently replace them.

Unknown-license sources may remain internal link-only discovery records. They cannot pass a learner release gate that requires known rights and owner review. The Explorer design's 80% resource coverage/95% link-health thresholds are proposal gates, not authority to waive PRD coverage or publication requirements.

An approved draft may be exported outside the live content tree with an audit trail. Export validation proves the draft authoring contract only. It does not prove PRD publication readiness or compatibility with the current Course loader.

## 6. Milestone implementation and acceptance plan

| Milestone | Smallest complete scope | Required evidence before its stop/report |
|---|---|---|
| M1 | Configuration, Foundry tables, isolated worker, stub S0–S8/S10 handlers, checkpoints, claims, durable budgets, kill switch, retry/park logging | Fresh upgrade/downgrade; crash/restart gives no duplicate effects; concurrent claims cannot process one skill twice on PostgreSQL; token/doc/time exhaustion parks; no learner/content writes |
| M2 | Central compliance/fetch boundary; HTTPX HTTP and GitHub adapters; robots snapshots/cache, TDM/noai and rights classifier; shared domain limits; permitted snapshot storage; allow-listed browser adapter with fail-closed isolation | Recorded/local-server tests for robots denial, unknown domain, noai, missing/ambiguous license, required license table, redirect/private/metadata IP rejection, DNS rebinding, response limits, Retry-After/ETag, concurrency and kill/budget boundaries |
| M3 | Article/docs/PDF/notebook extraction in appropriately isolated workers; injection detection before hiding/removing suspicious text; dedupe, structure-aware chunks, tool-free contextualization, Embedder, dense+FTS/RRF and reranker | No chunk/raw/summary/cache body for link-only; hidden injection quarantined; no notebook execution; code/table-safe chunking and documented oversized-block handling; attributed filtered retrieval; real PostgreSQL vector/FTS tests as well as deterministic fake tests |
| M4 | Skill request/resolver and unique aliases; safety/domain/source-richness eligibility before acquisition; verified source registry, licensed-search interface, PRD rubric | Concurrent/paraphrased requests reuse a skill/build; unsupported/unsafe skills waitlist/refuse without crawling; insufficient sources yield a coverage message; no per-learner scrape or learner-model writes |
| M5 | Candidate concepts, independent-source support, confidence/evidence, DAG cycle removal log, transitive reduction, resource alignment and approved draft-schema export | DAG and reference checks; every edge attributed; all LLM/weak edges queued; mirrors do not count as independent support; schema validates; no live catalog visibility |
| M6 | Explorer proposal gates; CLI review of graph/resources/evidence, digest-bound approve/reject/reorder, audit; authenticated status API; quarantine/takedown and re-gating | Human action required; no Guided/Verified assignment or evidence updates; takedown removes raw objects, chunks/vectors, summaries/context, model/retrieval caches and affected evidence snippets while retaining minimal non-content audit data. Original unchanged-planner selection remains blocked pending section 2 decisions |
| M7 | Held-out DSA calibration and SQL/Git fake/live harness; `foundry/REPORT.md` | Pipeline cannot see curated DSA; separate evaluator reads it after export. Report concept precision/recall, edge precision/recall by confidence, retrieval recall@8, sampled relevance, rights, links, safety, usage/time/cost and human-review effort. Missing live credentials/reviewers yields "not measured", never fabricated passing results |

Retain S0–S12 names in reports, but S9 practice and S11 learner personalization are outside this MVP; ongoing S12 refresh automation is deferred. Do not renumber stages or count an omitted stage as successful implementation.

### Acquisition and dependency choices

Use HTTPX 0.28.1 instead of adding Scrapling for ordinary HTTP. Its installed signatures and the [current API reference](https://www.python-httpx.org/api/) agree on streaming, manual redirects, timeouts, `transport` and `trust_env`. Use a central client/transport with automatic redirects disabled and explicit proxy policy; library defaults are not an SSRF defense. Resolve and validate destinations at connection time, including DNS rebinding, IPv4/IPv6/mapped addresses, credentials/ports and every redirect. Apply the boundary to robots/TDM/license/link-health requests too. Browser requests need equivalent checks for every subresource and navigation, not only the initial URL; keep live rendering disabled until that isolation is demonstrated.

The existing installed SQLAlchemy signature supports `with_for_update(skip_locked=True)`. [GitHub's current search docs](https://docs.github.com/en/rest/search/search) confirm 30 authenticated searches/minute (10 unauthenticated) and the 1,000-result cap. Read response quota headers and back off; do not rely solely on a fixed sleep. No GitHub live searches were performed in M0.

[pgvector](https://github.com/pgvector/pgvector) requires the extension to be installed and enabled per database. The repository's PostgreSQL image alone does not prove it is available. Prefer its PostgreSQL index if permitted; otherwise return for a concrete storage decision before M3 instead of adding an unapproved vector service.

Crawl4AI, Trafilatura, Docling and an object-store SDK are later-stage additions, not M1 requirements. Before adoption, inspect their selected pinned distributions and official API/security documentation, build a fixture-based adapter proof and update the lockfile. Do not copy the attachment's sample APIs unchecked. No versions are invented in this M0 report. Production storage endpoint/bucket/identity, embedding/reranker provider and isolated parser runtime are not configured yet; live operation remains disabled until they are.

### Proposed configuration defaults

Use a Foundry-owned Pydantic configuration with `SOCRAT_FOUNDRY_` variables, reusing the current DB/provider secret mechanism. Validate caps as positive bounded values. Default disabled/offline; global kill and daily reservations live in DB controls, not a flag captured once on worker startup.

Initial proposals: 60 fetched documents per job; 2,500,000 total input/output tokens including retries/context/embeddings; 5,400 seconds cumulative elapsed wall time; 20 jobs per UTC day; 50,000,000 global daily tokens; 2 seconds minimum delay and 2 concurrent requests per domain; depth 2; 10 MB maximum decoded response body; 5 redirects; 24-hour robots cache; three failed attempts before human intervention. These are safety ceilings, not measured cost targets. Live costs additionally require an approved provider/model and pricing. Discovery defaults to English code/math, with every source registry license marked `verify`. Use real approved bot identity/contact settings before live fetching, not `socrat.example`.

### Checks after each implementation milestone

Run the full backend suite, Ruff formatting/lint and mypy, migration reversal and the milestone-specific fixtures/concurrency gates. Use an isolated temporary DB and explicit PostgreSQL test URL; never the live/demo database. Preserve unrelated baseline failures as distinct evidence; do not call the milestone clean if required gates still fail. Frontend code/build/E2E changes remain outside scope. Tests for the new pipeline make no live calls; the harness's `--live` mode is explicitly opt-in and gated by settings, budgets and reviewed policies.

Commit only the milestone's changes on a `codex/` branch, report results, and stop. Do not automatically merge or publish a pack. Human code review and content review are separate gates.

## 7. M0 verification record

Inspected executable sources, migration chain, schema exports, content layout, CI, installed package versions/signatures and the official references linked above. Loaded all three current course packs using `load(tests_root=None)` without executing generators or reference solutions. No API keys were used and no source ingestion/model calls were made.

These results describe the unchanged application, not Foundry implementation acceptance.

- Ruff lint: passed for `services/api` and `services/execution`.
- Ruff format check: failed; 17 existing files would be reformatted, 97 already formatted. No formatter was applied.
- mypy: failed; two existing errors in `services/api/src/socrat/explainer/routes.py`, lines 105 and 136 (optional thread/user types).
- First backend suite attempt: 130 passed, 24 skipped, 91 setup errors because the default Windows pytest temporary directory was inaccessible; coverage 49% was not a usable baseline. Re-run uses a fresh workspace-owned `--basetemp`; no permission or source changes were made.
- Backend suite re-run: **221 passed, 24 skipped, 3 warnings in 163.08 seconds; 88.89% coverage**, exceeding the 85% gate. The 24 skipped cases require the opt-in dedicated gVisor host. Log: `.cache/foundry-m0-pytest.log` (local, untracked).
- Frontend build/typecheck/E2E, live crawling/providers, pgvector installation, production storage, dedicated gVisor and human calibration: not exercised in M0.

Reproduce the backend checks from the repository root with the locked environment installed. Use a new workspace-owned temporary directory on this Windows machine:

```powershell
$foundryTemp = Join-Path (Get-Location).Path ('.cache/foundry-tests-' + [guid]::NewGuid().ToString('N'))
uv run --frozen pytest --basetemp $foundryTemp --cov=socrat --cov-report=term-missing --cov-fail-under=85
uv run --frozen ruff format --check services/api services/execution
uv run --frozen ruff check services/api services/execution
uv run --frozen mypy services/api/src services/execution/src
```

M0 acceptance: stack, queue, DB/config/CI/gateway, active schemas and DSA storage inspected; proposed package layout, integration scope, migration list and conflicts documented. **Reconnaissance is complete.** Implementation approval, draft-contract approval and learner-release resolution remain open. No overall clean lint/type gate or Foundry functionality is claimed.

## 8. Decisions for the owner

Before M1, approve or amend this plan, especially these proposals:

1. **Draft-only delivery:** keep the current planner, learner state, mastery and assessments untouched; replace M6's learner-selectable criterion with reviewed versioned export/status until an Explorer-compatible product/runtime contract is separately approved.
2. **Draft schema:** approve section 5's explicit incomplete/draft manifest rather than fabricate the assessment-bearing fields required by a published Course/PRD pack.
3. **Database path:** permit PostgreSQL for concurrent/live Foundry work and SQLite for portable single-worker foundations/tests; verify pgvector installation/permission before M3. No extension/database modification is requested in M0.

Before M2 live acquisition, supply approved domains/ToS decisions, a real bot/contact identity, and the storage/runtime destination. Before M3 live model work, select embedding model/dimension, reranker and budgets. Before M6 publication, name authorized independent reviewers, review capacity and the product release authority. Before M7 live calibration, approve the beta skill allow-list (proposal: DSA held-out calibration, SQL basics and Git), live spend and reviewer time. Written content partnerships can be added only when their permission evidence exists; no partnership is assumed.

Skipped: implementation, frontend changes, new infrastructure, practice/assessment generation and learner publication. Main risk: an Explorer draft cannot satisfy the current planner/release contract merely by passing a new schema.
