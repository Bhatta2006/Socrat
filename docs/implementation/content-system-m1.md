# Content system M1: provenance and hygiene

Status: **complete, awaiting review.** Branch `content-system`. Plan and decisions:
[content-system-m0.md](content-system-m0.md).

## What was built

- **Provenance** (`catalog/schema.py`): optional `Provenance` / `SourceRef` on concepts, quiz
  items, problems and atom packs. Absent means a legacy record. Adapted records must cite a
  source; other origins cannot. `review` is never filled by tooling.
- **Source registry and license gate** (`content/sources/registry.yaml`, `catalog/sources.py`):
  Appendix A as data. Catalog load rejects `origin: adapted` content that cites an unknown,
  unverified or non-adaptable source, or a license the source does not carry.
- **Legal drafts and attribution page**: `LICENSE`, `NOTICE.md`, `ATTRIBUTION.md` (all marked
  for legal review); public `GET /api/v1/attribution` and `/attribution`, linked from the landing footer.
- **Inventory** (`scripts/content/inventory.py`): tracked CSV export with the Appendix B columns;
  `rights_or_license` and `review_record` are never empty.
- **Link health** (`scripts/content/link_health.py`): offline by default; `--live` uses
  robots.txt, per-host delay, a Socrat User-Agent, HEAD→GET fallback and a CSV report.

## How to run

```
uv run python scripts/content/inventory.py --check          # rights/review completeness
uv run python scripts/content/inventory.py --out content-inventory.csv
uv run python scripts/content/link_health.py --live --out .cache/link-health.csv
uv run pytest services/api/tests/test_provenance.py services/api/tests/test_sources.py \
  services/api/tests/test_inventory.py services/api/tests/test_link_health.py
```

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| Every existing content file still loads | Pass | `test_every_existing_content_file_still_loads_without_provenance`; full suite 260 passed |
| Validator rejects adapting from an unverified source | Pass | `test_gate_rejects_adaptation_from_an_unverified_source`, `test_loading_content_runs_the_license_gate` (on-disk tree fails `load()`) |
| Inventory has no silently empty rights fields | Pass | `test_no_record_has_an_empty_rights_or_review_field`; empty `rights_or_license` cells 1,801 → 0 on the real export; same 16,824 record IDs, no other column changed |
| API responses unchanged | Pass | Provenance is pack-level on atoms, so session atom JSON keeps its shape; new endpoint is additive |
| Lint, types, tests | Pass | ruff format/check clean; mypy (Linux) clean; pytest 260 passed, 88.90% coverage; e2e 39 passed; atom validation clean; `/attribution` 218.9 KB (budget 250) |

## Decisions and assumptions

- Provenance models live in `catalog/schema.py` next to `Review` (a separate module would import
  in a cycle); M0 named `catalog/provenance.py`.
- Registry `verified` status is taken from content.md Appendix A (✔, single license) and is
  labelled "not re-checked here". Nothing was verified online in this milestone.
- Unknown licenses may be `link-only` or `verify`; non-commercial, no-derivatives and
  all-rights-reserved are always `link-only`.
- The inventory port covers the CSV only; the narrative status report from the audit script was
  not ported.
- LICENSE is a proprietary "all rights reserved" draft for Socrat-original material.

## Needs a human

- **Legal review** of LICENSE, NOTICE.md, ATTRIBUTION.md and the registry classifications.
- **License verification** on each source's own page before any `adapt`/`share-alike-lane` use;
  update `last_verified_at` and `verified_from` when done.
- A full dependency license report (NOTICE.md says it has not been produced).
