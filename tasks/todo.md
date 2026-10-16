# Content system tasks

M0 approved (decisions D1–D12 in `docs/implementation/content-system-m0.md`). M1–M6 done; see `docs/implementation/content-system-m1.md` … `content-system-m6.md`.
Verification for every task: the commands in `tasks/plan.md` plus the task's own check.

## M1 provenance
- [x] 1. Provenance and SourceRef models; optional `provenance` on Concept, QuizItem, Problem
  - Acceptance: all current YAML loads unchanged; digest unchanged when no file uses the field
  - Verify: `uv run pytest services/api/tests/test_core_engine.py services/api/tests/test_provenance.py`
  - Files: `catalog/provenance.py`, `catalog/schema.py`, tests
- [x] 2. `content/sources/registry.yaml` (Appendix A) and license gate
  - Acceptance: ◻ entries are `unverified`; an `origin: adapted` fixture citing one fails with a clear message
  - Verify: `uv run pytest services/api/tests/test_provenance.py -k gate`; CI runs the validator
  - Files: `content/sources/registry.yaml`, `catalog/sources.py`, `scripts/content/validate_sources.py`
- [x] 3. LICENSE, NOTICE.md, ATTRIBUTION.md (drafts) and `/attribution` page
  - Acceptance: each file says "draft, legal review required"; page renders the attribution list
  - Verify: `npm run typecheck`, `npm run build`, bundle budget
  - Files: root docs, `apps/web/src/app/attribution/page.tsx`
- [x] 4. Inventory generator in `scripts/content/inventory.py`
  - Acceptance: every row has `rights_or_license` and `review_record` set, `unknown` where unknown
  - Verify: `uv run python scripts/content/inventory.py --check`
  - Files: `scripts/content/inventory.py`, test
- [x] 5. Link health (extend `check_links.py`, `link_health.py` entry point)
  - Acceptance: offline by default with fixtures; `--live` does HEAD→GET, delay, robots, own UA; CSV out
  - Verify: `uv run pytest services/api/tests/test_link_health.py`
  - Files: `scripts/content/check_links.py`, `scripts/content/link_health.py`, fixtures, test
- [x] Checkpoint M1: full suite, lint, types; commit; report; wait for approval

## M2 content-schemas
- [x] 6. Pattern schema, loader, cross-reference validation
- [x] 7. Quiz family / bank item / generator spec; wrap existing 234 items read-only
- [x] 8. Project schema and JSON contracts
- [x] 9. Runtime tables migration with downgrade test
- [x] Checkpoint M2

## M3 quiz-engine
- [x] 10. Config + rating math
- [x] 11. Pools and band mapping
- [x] 12. Selection and ladder guarantees
- [x] 13. Modes, stop rules, cold start, roll-up
- [x] 14. API behind `adaptive_quiz`, evidence via `mastery.apply`
- [x] 15. Simulator and property tests
- [x] Checkpoint M3 (e2e not run: stale local `socrat.e2e.db` at revision 0011)

## M4 item-generators
- [x] 16. Framework and verifier
- [x] 17. Defects, traces, stories, counterexamples
- [x] 18. Three proof families in three languages
- [x] 19. Verifier negative tests; 100 items per family
- [x] Checkpoint M4 (e2e not run: stale local `socrat.e2e.db`)

## M5 pilot-content
- [x] 20. DSA batch 1 (variable window, at-most-k, lower/upper bound)
- [x] 21. DSA batch 2 (answer predicate, unbounded coin change, top-k)
- [x] 22. Zero batch (accumulator, traverse-and-filter, frequency count)
- [x] 23. CP batch (difference array, fast power, subset enumeration)
- [x] 24. Length lint and full verification
- [x] Checkpoint M5 (e2e not run: stale local `socrat.e2e.db`; packs need human review)

## M6 pattern-planner
- [x] 25. Priority scoring module
- [x] 26. Pattern triggers behind `pattern_planner`
- [x] 27. Session templates and hard-constraint property tests
- [x] 28. Golden tests for three learner states
- [x] Checkpoint M6 (e2e not run: stale local `socrat.e2e.db`)

## M7 item-calibration
- [ ] 29. Stats job and flag rules
- [ ] 30. Status transition CLI with human approver
- [ ] 31. Markdown report without PII
- [ ] Checkpoint M7
