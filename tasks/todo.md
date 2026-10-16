# Content system tasks

M0 approved (decisions D1–D12 in `docs/implementation/content-system-m0.md`). M1 done; see `docs/implementation/content-system-m1.md`.
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
- [ ] 6. Pattern schema, loader, cross-reference validation
- [ ] 7. Quiz family / bank item / generator spec; wrap existing 234 items read-only
- [ ] 8. Project schema and JSON contracts
- [ ] 9. Runtime tables migration with downgrade test
- [ ] Checkpoint M2

## M3 quiz-engine
- [ ] 10. Config + rating math
- [ ] 11. Pools and band mapping
- [ ] 12. Selection and ladder guarantees
- [ ] 13. Modes, stop rules, cold start, roll-up
- [ ] 14. API behind `adaptive_quiz`, evidence via `mastery.apply`
- [ ] 15. Simulator and property tests
- [ ] Checkpoint M3

## M4 item-generators
- [ ] 16. Framework and verifier
- [ ] 17. Defects, traces, stories, counterexamples
- [ ] 18. Three proof families in three languages
- [ ] 19. Verifier negative tests; 100 items per family
- [ ] Checkpoint M4

## M5 pilot-content
- [ ] 20. DSA batch 1 (variable window, at-most-k, lower/upper bound)
- [ ] 21. DSA batch 2 (answer predicate, unbounded coin change, top-k)
- [ ] 22. Zero batch (accumulator, traverse-and-filter, frequency count)
- [ ] 23. CP batch (difference array, fast power, subset enumeration)
- [ ] 24. Length lint and full verification
- [ ] Checkpoint M5

## M6 pattern-planner
- [ ] 25. Priority scoring module
- [ ] 26. Pattern triggers behind `pattern_planner`
- [ ] 27. Session templates and hard-constraint property tests
- [ ] 28. Golden tests for three learner states
- [ ] Checkpoint M6

## M7 item-calibration
- [ ] 29. Stats job and flag rules
- [ ] 30. Status transition CLI with human approver
- [ ] 31. Markdown report without PII
- [ ] Checkpoint M7
