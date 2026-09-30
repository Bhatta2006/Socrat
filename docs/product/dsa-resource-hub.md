# DSA resource hub — draft source index

**Status:** editorial candidate pool; no learner release.
**Snapshot:** 2026-09-30 local import of seven pinned Git repositories and the CSES task index.
**Authority:** [V1 PRD §§11, 12, 17, 21](v1-product-requirements.md), [content standard](content-standard.md), and [deterministic policy matrices](deterministic-policy-matrices.md).

The hub provides one canonical link record per known problem, separate references to solved code and explanations, a topic taxonomy, provisional difficulty, and company history. It contains metadata and links only. An imported item is `review_required`; it cannot be assigned to a learner. The M2 skill-pack release process and the content standard still determine publication.

## Snapshot inventory

| Measure | Current index |
|---|---:|
| Distinct records | 5,779 |
| Official problem links | 3,792: 3,392 LeetCode, 400 CSES |
| Other records | 1,345 solution-only, 361 implementations, 180 lessons, 101 roadmap entries |
| Source references after deduplication | 8,059 |
| Company/time-window signals | 37,714 across 429 companies |
| Taxonomy topics | 41; 16 exact keys also appear in the draft M2 graph |
| DSA candidate problem links | 3,473; all have provisional difficulty bands |
| Problem links needing topic review | 108; 211 more are out of scope, including interactive tasks |
| Missing topic classification across all record kinds | 1,208 |
| Missing difficulty band across all record kinds | 1,625 |

The [summary](../../contracts/resource-pool/dsa-resource-summary.json), [line index](../../contracts/resource-pool/dsa-resources.jsonl), [topic taxonomy](../../contracts/resource-pool/dsa-topic-taxonomy.json), and [topic × difficulty matrix](../../contracts/resource-pool/dsa-topic-difficulty-matrix.json) are the machine-readable artifacts. Matrix counts overlap when a problem has multiple topics and do not imply release coverage. Each source snapshot has a pinned Git commit or CSES page hash. The company data describes a June 2025 snapshot; its “thirty days” window means thirty days at that time, not a current hiring signal.

## How the eight sources are used

| Source | Role in the hub | Difficulty evidence | Release concern |
|---|---|---|---|
| [Striver A2Z solutions](https://github.com/Codensity30/Strivers-A2Z-DSA-Sheet) | Topic sequence and C++ solution references | Easy/medium/hard directory, provisional | No root license found in snapshot; solution must remain behind attempt gate |
| [practical-dsa](https://github.com/namphuongtran/practical-dsa) | C/C++ foundations, notes, exercises, implementations | Week position, provisional | Repository MIT; linked platform problems carry separate rights |
| [CP-Algorithms](https://github.com/cp-algorithms/cp-algorithms) | Competitive explanations and reference algorithms | Unclassified until item review | Repository CC BY-SA 4.0; index links only |
| [TheAlgorithms/C-Plus-Plus](https://github.com/TheAlgorithms/C-Plus-Plus) | C++ implementation references | Unclassified until item review | Code MIT; generated documentation has separate CC BY-SA terms |
| [DSA_Roadmap](https://github.com/maroofiums/DSA_Roadmap) | Week/topic sequencing and Python solution references | Week position, provisional | No root license found in snapshot |
| [ishaanbuildsthings/leetcode](https://github.com/ishaanbuildsthings/leetcode) | Solution references across LeetCode, CSES, Codeforces, AtCoder, and others | Inherited only when matched to a labeled canonical item | No root license found; Windows-invalid filenames are read from the Git tree without copying code |
| [CSES problem set](https://cses.fi/problemset/) | Canonical contest problem ID, link, and category | Category prior, provisional; not a problem rating | External terms require review; no statements or tests copied |
| [Company-wise LeetCode lists](https://github.com/liquidslr/leetcode-company-wise-problems) | Canonical LeetCode links, provider labels/tags, historical company frequency and windows | Provider easy/medium/hard, provisional | No root license found; company tag origin and use terms need review |

Repository files that only contain an answer are `solution` or `implementation` references. They do not become unseen practice. When an exact title matches a canonical LeetCode or CSES item, the reference is attached with `match_basis: exact_title_unverified`; an editor must confirm the identity. Other files retain their own source ID for editorial review. SQL, shell, Pandas, JavaScript, and concurrency problems in the company lists are marked `out_of_scope`; ambiguous records remain `unknown`.

## Difficulty and topic rules

- Provider `Easy`, `Medium`, and `Hard` labels map to provisional bands 2, 5, and 8. Those numbers are ordering priors, not proof that two providers' items are equally hard.
- CSES category and roadmap/practical week positions supply weaker provisional bands. CSES does not publish a uniform difficulty label in its task index. Interactive CSES tasks are marked out of scope for the current learner flow.
- Where neither label nor useful prior exists, `difficulty.band` is absent and the item goes to the review queue. Solve rate, expected time, number of steps, prerequisite depth, and implementation load must be reviewed and later calibrated from clean attempts as required by the PRD.
- Topic aliases normalize provider tags and repository section names to the 41-key taxonomy. The taxonomy stores prerequisite relationships and exact links to existing draft M2 concepts. Unmatched topics are retained for graph expansion; they are not silently collapsed into a broader released concept.
- An item needs a reviewed **primary topic** before release. Secondary tags support search and diagnosis; they do not by themselves prove prerequisite eligibility.

## Learner assignment contract

The selector in [`dsa_resource_pool.py`](../../services/api/src/socrat/dsa_resource_pool.py) accepts a versioned learner snapshot: confirmed track and language, released and ready topics, target topics, per-topic mastery and misconception signals, current difficulty, recent independent outcomes, due reviews, time budget, exposure history, and optional company preference. It follows the PRD's policy order:

1. Exclude unreleased, out-of-scope, wrong-kind, wrong-track, unsupported-language, solved/recent, unpublished-topic, prerequisite-locked, over-difficulty, and over-budget items.
2. Set a deterministic difficulty target. Three fast independent successes can raise it one band; two independent failures can lower it one band. Assisted work does not trigger either move.
3. Rank remaining IDs by goal topic, weak-concept need, observed misconceptions, difficulty fit, due review, and a bounded historical company preference for interview goals. Company frequency cannot override any hard filter.
4. Return the baseline and at most eight eligible IDs with reason codes, policy version, and a hash of the exact input/candidate snapshot.
5. An optional LLM may return only those IDs with allowed evidence references, reason codes, and confidence. A stale, invented, duplicate, or low-confidence recommendation falls back to the baseline. The model never sees solution code through this contract or writes learner state.

This is a selector contract and candidate index for M2. The learner model, exposure store, runtime language checks, and actual daily-plan integration are later milestones. There are no approved learner candidates in this snapshot, so the selector correctly returns no assignment from it today.

## Editorial workflow

Query by topic, difficulty, company, source, kind, or scope:

```powershell
.venv\Scripts\python.exe scripts/content/query_dsa_resource_pool.py --company Amazon --topic arrays --kind problem --difficulty 2 --limit 20
.venv\Scripts\python.exe scripts/content/query_dsa_resource_pool.py --scope unknown --limit 20
```

To refresh the index, clone the seven repositories at the commits recorded in the summary into an ignored local source directory, save the CSES task index HTML, and run:

```powershell
.venv\Scripts\python.exe scripts/content/build_dsa_resource_pool.py --source-root temp/dsa-sources --cses-html temp/dsa-sources/cses.html
```

Before promoting any item, a named editor must verify the canonical problem link, primary and secondary concepts, prerequisites, target track, difficulty and time estimate, source rights and attribution, accessibility, solution exposure boundary, and supported language variants. An internally served exercise additionally needs original/licensed statement, reference solutions, starter contracts, deterministic tests, and independent assessment separation. Candidate selection and independent content reviews then use the [M2 operator workflow](../operations/m2-content-admin.md). These external links do not count toward the PRD's 250 curated practice problems or 90 sequestered assessment items.
