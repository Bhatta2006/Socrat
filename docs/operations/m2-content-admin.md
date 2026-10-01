# M2 content operator guide

This guide covers the local and future staging API workflow for the skill-pack kernel. The [content standard](../product/content-standard.md) remains the human release bar. Importing a manifest does not release it.

The internal operator screen is at `/admin/skill-packs`. Sign in with a named operator account first. It lists versions, accepts manifest JSON, shows the immutable digest and required reviews, and exposes only actions associated with the signed-in account's roles. The API remains authoritative for all authorization and state changes. Staff without a content role see an access message. The screen does not grant roles or create content; authors prepare manifests through the versioned content workflow.

## Identity and roles

Sign in through the configured identity path first. An administrator with direct database access grants roles to an existing `users.id` by inserting into `content_operators`; the application has no role-grant endpoint. Record the grant in the operator change ticket and use separate named accounts for author, reviewers, and release owner. Supported roles are `author`, `domain_reviewer`, `learning_reviewer`, `accessibility_reviewer`, `rights_reviewer`, `language_reviewer`, `assessment_reviewer`, and `release_owner`.

```sql
INSERT INTO content_operators (user_id, role) VALUES (:existing_user_id, :role);
```

The author cannot review or publish their own version. A release needs domain, learning, accessibility, and rights reviews, plus language review when adapters exist and assessment review when an assessment blueprint or assessment item exists. Any rejection blocks that version; corrections require a new version. Review notes are retained with reviewer identity and time.

All mutating requests require the exact configured `Origin`, the signed-in session cookie, and `X-CSRF-Token` from `GET /api/v1/me`. The API returns stable error codes and request IDs. Do not put source content, personal data, or credentials in review notes or quarantine reasons.

## Workflow

| Step | Endpoint | Result |
|---|---|---|
| Discover | `GET /api/v1/admin/skill-packs` | Operator-only version inventory |
| Own roles | `GET /api/v1/admin/content-roles` | Signed-in account's content roles; drives operator-screen controls |
| Import | `POST /api/v1/admin/skill-packs` | Validates the strict schema and DAG; creates a unique draft version and digest |
| Inspect | `GET /api/v1/admin/skill-packs/{id}` | Full manifest, required reviews, recorded decisions and notes |
| Review | `POST /api/v1/admin/skill-packs/{id}/reviews` | Body: `{"role":"domain_reviewer","decision":"approve","note":"..."}`; reviewer must hold that role |
| Publish | `POST /api/v1/admin/skill-packs/{id}/publish` | Requires `release_stage: candidate`, all applicable reviews, and a matching digest; activates one version per pack |
| Quarantine item | `POST /api/v1/admin/skill-packs/{id}/items/{item_key}/quarantine` | Body: `{"reason":"..."}`; item is excluded immediately from the general runtime loader |
| Quarantine pack | `POST /api/v1/admin/skill-packs/{id}/quarantine` | Body: `{"reason":"..."}`; hides the version and follows its recorded predecessor chain to the prior non-quarantined release when available |

`GET /api/v1/skill-packs` exposes only active published-pack metadata. `GET /api/v1/skill-packs/{key}/versions/{version}` exposes metadata for a still-released pinned version. General runtime loading excludes assessment items and quarantined items. No public endpoint serves hidden tests or full assessment payloads.

## Contract and release preparation

The [sample DSA manifest](../../contracts/skill-packs/dsa-sample.json) seeds draft graph and track coverage. The [non-DSA manifest](../../contracts/skill-packs/non-dsa-fixture.json) is a structural test only. Regenerate both and the exported schema with `python scripts/content/build_sample_packs.py`; CI tests detect schema drift. Their `release_stage` is `draft`, so the API rejects publication even if reviews are entered.

For a real release, create a new semantic version; do not overwrite an imported version. Complete the concept, rights, language, assessment, accessibility, deterministic test, and canary checks in the [content release checklist](../product/content-standard.md#release-checklist). Move `release_stage` to `candidate` only when evidence is ready for independent review. M2 does not claim that the sample pack passes those checks.

Contract version 2 requires one coverage cell for every declared track/language combination (or one language-neutral cell for a track with no language adapters). Draft cells cannot appear in a release candidate; unavailable cells need a reason. The public catalogue lists only released cells. A release candidate also includes `release_evidence` references with an artifact URI, SHA-256 digest, and summary for rights, accessibility, concept and exercise quality, assessment separation, a prepublication canary, and language coverage when a language is released. Reviewers inspect the artifacts behind those references; placeholder references used by automated fixtures are never release evidence. When a new version removes a concept key, it must map that key to current concepts or explicitly retire it, citing the active predecessor version. Existing contract-version-1 records remain readable, but cannot be newly published.

The runtime eligibility loader returns no pack for draft or unavailable cells. For released cells it omits quarantined and assessment items, other-track concepts, and items without that language variant. A language-neutral item can be used in any released cell of its track.

Quarantine preserves the manifest, reason, actor, and audit/outbox trail. When learner attempts exist in later milestones, follow the content standard's evidence-repair procedure before scoring affected attempts. Quarantine alone does not recompute learner state.
