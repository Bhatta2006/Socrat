# M7 limited pilot

Owner direction, 6 October 2026: start with a limited pilot, research suitable public curricula, choose reviewers later, defer unavailable learner/staff/staging evidence, and propose the metric/penalty policy. Dedicated-host M6 acceptance remains deferred. **This prepares content for review; it does not authorize a live release or pass the M7 gate.**

## Curriculum and reading

Use [Striver A2Z](https://takeuforward.org/prep-hub/strivers-a2z-dsa-sheet) as the primary sequence reference. Its syllabus progresses through basics, arrays, hashing and later patterns; its beginner audience still needs programming fundamentals. Use [NeetCode's roadmap](https://neetcode.io/roadmap/) as an Interview pattern companion. This selection is our recommendation, not a publisher endorsement. Neither entire curriculum is a two-week pilot promise. Publisher access varies; some practice/course features require payment.

For language readiness, link to [CS50 Python](https://cs50.harvard.edu/python/), [dev.java basics](https://dev.java/learn/language-basics/) and the [Standard C++ getting-started FAQ](https://isocpp.org/wiki/faq/newbie). Check variables, conditions, loops, arrays, functions and integer stdin/stdout before DSA practice. C++'s publisher page blocked the automated fetch; check learner access before rollout. These are optional external links. External completion creates no Socrat mastery fact. No publisher problem statements, videos or solutions are copied into the draft.

The original [authoring draft](../../contracts/content/m7-arrays-pilot-draft.json) follows this scope:

| Topic | Prerequisite | Original practice |
|---|---|---|
| Array scans/state | Language readiness | Sum, positive count, alternating sum, adjacent jump, sign switches, first minimum, first descent, positive streak |
| Linear search | Scans | First/last/count matches; nearest target with stable ties |
| Frequency counting | Scans | Distinct values, equal-index pairs, first unique value |
| Prefix sums | Scans | Prefix totals, first target prefix length, balanced cut |
| Two pointers | Linear search | Sorted pair search, palindrome, read/write sorted compaction |
| Fixed windows | Prefix sums | Maximum sum, zero-sum count, adjacent-change count per window |

There are 54 original lessons (six concepts across three tracks and three languages), 24 exercises with 72 Python 3.12/C++20/Java 21 variants, 1,693 boundary/random test vectors, and six unreviewed structural repair proposals. Foundations emphasizes traces and state; Interview includes recognition, correctness and complexity; Competitive emphasizes constraints and independent low-stakes practice. Each lesson has distinct exact retrieval/exit checks. Language notes cover indexing, integer widths and container pitfalls. These are original drafts, not independently reviewed teaching material.

Family grouping is conservative: first/last/count target tasks share a family, as do rolling-sum max/count tasks. Eighteen candidate families are not proof of structural novelty. Every lesson, exercise, repair and penalty stays `uncalibrated`. Eight-minute root and twelve-minute later exercise estimates are candidates. The two-week horizon is a planner-rehearsal target, not a calibrated learner completion duration.

The draft deliberately uses a separate offline schema, with **no execution runtime pins**, protected assessment inventory or released target routing. It cannot be ingested as a SkillPack. Reference solutions and hidden vectors belong in authoring storage; do not expose this JSON in a learner API or browser bundle. The report emits counts/digest and requirements, without keys or sources.

## Proposed pilot policy

The machine-readable [policy proposal](../../contracts/product/m7-pilot-policy.json) remains `proposed_pending_review`.

- **Activation:** confirmed goal, completed/current diagnostic, confirmed plan, and first healthy finalized original independent Submit admitted within 48 hours of goal confirmation. Correctness is not required; hint level must be zero. Qualify only after signed finalization, using admission time. Run, pending/operational failures, upsolve-only work, invalidated evidence and withdrawn packs do not qualify. This matches the implemented owned-goal candidate and PRD's Submit milestone.
- **Cohorts:** exclude test, staff, synthetic, deleted-before-eligibility and known-corrupt records with reason codes. Segment by track/language. Account deduplication and aggregate reporting remain future work; the owned-goal export does not implement a global cohort.
- **Practice penalty:** propose **60 seconds** per healthy incorrect original timed Competitive Submit. It changes reported penalized practice time, preserves retries and leaves the deadline unchanged. Exclude Run, timeout, operational failure, untimed practice and upsolve. This small cost is a product hypothesis to review during the pilot, not an empirically established optimum or contest ranking rule.

The older plan-start metric remains recorded in the historical candidate contract. The proposed Submit definition supersedes it only after explicit metric review/versioning; do not rewrite published historical cohorts. Reviewers will be assigned later. No reviewer identities, approvals or sampling minima are fabricated.

## Authoring and technical checks

Run with the API package on `PYTHONPATH`:

```text
python scripts/content/build-m7-pilot.py
python scripts/content/build-m7-pilot.py --check
python scripts/validation/export-m7-contracts.py
python scripts/validation/check-m7-pilot-references.py --language python
python scripts/validation/check-m7-pilot-references.py --language cpp
python scripts/validation/check-m7-pilot-references.py --language java
python scripts/validation/check-m7-pilot-references.py --language cpp --host-compiler C:/msys64/mingw64/bin/g++.exe
python scripts/validation/check-m7-pilot-references.py --language java --host-compiler .cache/m7-jdk21/jdk-21.0.12.1+1/bin/javac.exe
python -m pytest services/api/tests/test_learning_pilot.py -q
```

The reference checker uses locally available official compiler images, resolves their immutable digests and records compact reports under ignored `.cache`. Its container mode runs only the fixed repository-authored draft without networking, with read-only inputs and bounded resources. An explicit `--host-compiler` supports trusted local C++20/Java 21 checks; this mode is for original repository reference programs and must never run learner code. Python regression tests also check the full stdin/stdout program for every vector on the repository's Python 3.12 environment. C++/Java compile against C++20/Java 21 and check all vectors through a batch `solve` harness plus one stdin/stdout smoke per program. Brute-force definitions produce expected values independently of optimized algorithms. Small tests do not establish complexity bounds, instructional quality or hidden-test adequacy. Compiler checks do not exercise the execution worker, signatures or gVisor.

The completed reference checks used Python 3.12.10, local GCC 16.1 in C++20 mode and a portable [Microsoft OpenJDK 21](https://learn.microsoft.com/en-us/java/openjdk/download) archive, version 21.0.12.1. Its SHA-256 matched the publisher's `192441a9d27da813bada974bb88b4cf64d37a9589ed37f204374d411ca5ce07f`. It was extracted only under ignored `.cache`; the system Java installation was not changed. All 1,693 vectors passed in each language, with twenty-four additional CLI smoke checks each for C++ and Java. Docker was unresponsive, so container/worker checks are not inferred from these host results.

## Deferred promotion and acceptance

Before publication: assign independent reviewers; review original-content rights, all objective keys, language semantics, family groupings and structural mappings; add separate protected diagnostic/assessment families and limited goal targets; bind approved immutable worker runtimes; convert reviewed content to a launch SkillPack; run both static and fourteen-day planner audits. Inventory must be expanded if a supported history/schedule exhausts safe practice. Do not weaken the audit to release the seed bank.

The owner explicitly deferred real learner duration calibration, staff dogfood, human accessibility review and staged nine-cell golden records. Preserve their [acceptance contract](m7-acceptance.md) for future collection. Duration error must eventually be at most 20% and material exercise defect rate strictly below 2% per cell, using a reviewed sampling plan. Dedicated-host M6 acceptance and earlier external gates remain separate. M7 acceptance is **open with these deferrals**, even when repository checks pass.
