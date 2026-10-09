# M2 content authoring and administration

## Validate a pack offline

From the repository root, with the locked Python environment available:

```powershell
$env:PYTHONPATH = 'services/api/src'
uv run python -m socrat.skillpacks.cli validate contracts/fixtures/skill-packs/dsa-1.0.0.json
uv run python -m socrat.skillpacks.cli validate contracts/fixtures/skill-packs/clear-writing-1.0.0.json
```

The command reports the content digest, deterministic prerequisite order, and explicit code-language coverage. It never executes imported source. JSON Schema export is `uv run python -m socrat.skillpacks.cli schema contracts/schemas/skill-pack.schema.json`; semantic DAG and reference rules additionally require the Python validator.

Fixture runtime digests are synthetic identifiers, not runnable image references. The fixtures have uncalibrated content and no real runtime or human approval evidence. Both are marked `purpose: fixture`, so even synthetic publication cannot expose them in the learner catalogue. Their sample scope is not the full V1 curriculum.

## Authoring contract

Use the [generated schema](../../contracts/schemas/skill-pack.schema.json) and [fixtures](../../contracts/fixtures/skill-packs/) as structural examples. Every pack carries versioned metadata, provenance, concepts, prerequisite rationale/mastery thresholds, goals/tracks, exercise inventory, modality/language variants, assessment blueprints, bounded policy primitives, and optional concept migration mapping.

Practice and assessment families must remain distinct; baseline and final families cannot overlap. Unsupported modalities, arbitrary plugins, unknown references, omitted overlay prerequisites, cycles, duplicate IDs, non-finite thresholds, and unsupported policy primitives are rejected. Semantic versions are immutable identifiers; a changed payload requires a new version. Migration sources must exist and reference known old concepts; targets must exist in the new version. A mapping is a proposal, not an automatic learner-state rewrite.

## Editorial access

No editor is enabled by default. The deployment setting `SOCRAT_CONTENT_ADMIN_IDENTITIES` is a JSON list of exact issuer/subject pairs. Keep actual identities in private deployment configuration. Matching a subject from another issuer grants no access. Normal learners and AI have no editorial permission.

For a local developer rehearsal only, configure two synthetic identities before starting Compose:

```powershell
$env:SOCRAT_CONTENT_ADMIN_IDENTITIES = '[{"issuer":"local-development","subject":"content-author"},{"issuer":"local-development","subject":"content-reviewer"}]'
docker compose up --build
```

These identities are synthetic accounts for demonstration, not real reviewers. Never enable development login in staging/production. Real staging roles must be approved, assigned to managed OIDC identities, and supplied consistently through protected deployment configuration for every activation/rollback; otherwise access defaults off.

## Administration API

All paths are relative to the application origin. Sign in as an approved editor, obtain the per-session CSRF token from `GET /api/v1/me`, and send exact `Origin` and `X-CSRF-Token` headers on every mutation. Retain the session cookie securely.

| Method/path | Operation |
|---|---|
| `POST /api/v1/admin/skill-packs` | Import the complete pack JSON; identical reimport returns the same record without duplicate events |
| `GET /api/v1/admin/skill-packs` | List up to 1,000 version summaries |
| `GET /api/v1/admin/skill-packs/{key}/versions/{version}` | Read a pinned payload, digest, coverage, graph order, and review history |
| `POST /api/v1/admin/skill-packs/{key}/versions/{version}/actions` | Explicit lifecycle or rollback operation |
| `GET /api/v1/skill-packs` | Assessment-safe active launch manifests only; fixtures are excluded |

An action body contains `action`, `evidence_reference` (opaque private review record ID), `reason`, and `verified_languages` (required complete language list at the language-verification stage). Raw review notes, names, credentials, and sensitive URLs must not be pasted into these fields. Imported payloads have no edit/delete API.

Example language-review body, to be submitted only after actual verification:

```json
{
  "action": "language_verified",
  "evidence_reference": "private-language-review-record",
  "reason": "All declared language variants reviewed against the content standard.",
  "verified_languages": ["python", "cpp", "java"]
}
```

## Review and release

The explicit sequence is `draft → technical_review → learning_review → language_verified → staged → released`. Action names match the target state except publication uses `publish`. The technical review covers domain correctness, learning review covers evidence/assessment validity, language review attests all declared languages, staging covers accessibility/copy and conflicts, and publication is the release owner's decision.

The importing author cannot perform any approval or publication step. An authorized independent reviewer may cover multiple documented responsibilities; record the actual responsible reviewers and evidence privately. The kernel enforces state order and identity independence, but does not replace expert judgment or execute reference solutions. Unknown/unverified rights block publication.

Mutations, review rows, audit entries, and outbox events commit together. Outbox events identify the immutable version by its opaque resource ID. Review records cannot be updated/deleted; corrections append evidence through an appropriate new action/version.

## Quarantine and rollback

Use `quarantine` with a reason/evidence reference to withdraw a suspect version. If it is active, the previous release becomes active only if still released and integrity-valid; otherwise the active pointer becomes empty. Nothing substitutes unreleased or quarantined content.

Use `activate` to explicitly roll back to another previously released version of the same pack. `retire` withdraws a version without editing its source. Quarantined/retired versions cannot reactivate; repair creates a new version and repeats review. Old payloads remain available to authorized editors for evidence replay, not new learner selection.

Learner attempt repair and automatic report-based quarantine belong to later learner/evidence milestones. M2 provides the content withdrawal boundary but does not claim learner state has been recomputed.

## Schema and recovery

Run `uv run alembic upgrade head` as a reviewed migration step. Revision `0002` adds content tables while retaining M1 data. Restore tools default to `0002`; historical archives can use explicit revision `0001`. Do not downgrade a live database to make an old image pass readiness: that would discard M2 content. Use a compatible application rollback and the [staging runbook](m1-staging-runbook.md).

Run `uv run pytest --cov=socrat --cov-fail-under=85`, Ruff, and mypy. CI supplies `SOCRAT_TEST_POSTGRES_URL` for isolated PostgreSQL release-concurrency and outbox checks. Local runs without that service explicitly skip those checks. Acceptance tests simulate reviews; they do not constitute production content approval.
