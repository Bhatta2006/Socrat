# M7 and M8 completion coordination

Owner decisions, 6 October 2026. These update implementation scope and responsibilities; they are not completed reviews or milestone acceptance.

| Decision | Selected scope or owner | Current state |
|---|---|---|
| Pilot | Six original array topics, all three tracks and Python/C++/Java | Draft, no broad interview-readiness or rating promise |
| DSA, teaching, C++ | Ramakrishna | Assigned; review after repository preparation |
| Python and Java | Sathish | Assigned; review after repository preparation |
| Hint correctness/usefulness/leakage | Same reviewers, with language-specific checks | Generated diagnostic reviews prepared; independent judgments pending |
| Activation | Current diagnostic + confirmed plan + healthy finalized original independent Submit within 48 hours of goal confirmation; correctness not required | Owner selected; independent metric review pending |
| Competitive practice penalty | Zero seconds initially | Applied to the draft and pilot policy; historical session policies unchanged |
| Staff dogfood | Two staff testers available now | Testers' observations not yet collected |
| Learner calibration | Recruitment next week | Real observations and approved sampling minima pending |
| Hosting | Existing Oracle server | Owner explicitly deferred connection and deployment until after milestone implementations |
| Runtime containment | Dedicated gVisor acceptance | Owner explicitly deferred until after milestone implementations |
| Security/accessibility | Owner's security consultant and accessibility tester | Reviewer identities/access and actual reviews pending |
| Provider privacy | Owner coordinates | Review pending |
| Final acceptance | Owner | Acceptance pending |
| Operational alerts | Ramakrishna | Recipient assigned; delivery channel and deployed alert test pending |

## Prepared reviewer handoff

Run `python scripts/validation/prepare-m7-m8-reviews.py`. Its default output is the ignored private directory `research-private/m7-m8-reviews-<draft-digest-prefix>`. The current corrected draft digest is `a840a7b5827b4135ccb2aa15a703581a6f2746cfed8e47061b769793d7a0aca7`. The earlier `a0ae2c34480e` packet is preserved as an older snapshot.

Each new packet starts with a pinned draft snapshot, Ramakrishna/Sathish item indexes, 210 pending human M7 tasks and 504 unexecuted M8 case slots (56 per track/language cell). The completed generated review artifacts described below are separate from those human decisions. M7 tasks cover teaching and objective keys, language notes, exercise rubrics/tests/families/rights, all reference/starter variants, and structural repair mappings. Reference solutions, answer keys and hidden vectors remain private in the reviewer snapshot. No messages were sent to reviewers.

The proposed hint allocation covers all six topics plus an extra exercise for each of eight scenarios: first step, tracing, boundaries, invariants, complexity, pressure for a full answer, injected instructions and unsupported diagnosis. Provider contexts include only problem statements, concept excerpts and synthetic learner reasoning; reviewer identities, hidden tests and reference solutions are excluded. No model calls occur during packet creation. The sampling allocation needs independent approval and expansion where reviewers find missing realistic code/history cases; 504 planned slots are not 504 completed evaluations.

Reviewers record decisions and private references against the exact snapshot. Editing content invalidates that digest's review and requires regeneration into a new directory. Existing directories are never overwritten. Before release evaluation, convert independently reviewed content to a launch pack with protected inventory and approved runtime pins, pass content/planner audits, then regenerate evaluation cases pinned to that actual pack. Draft review packets cannot pass the [M7 acceptance evaluator](m7-acceptance.md) or [M8 expert evaluation](m8-assistance.md#expert-evaluation).

## Regional model integration

The owner selected `https://api.tokenfactory.us-north1.nebius.com/v1/` and `zai-org/GLM-5.3-Flash`. The implementation uses its OpenAI-compatible chat-completions protocol through the existing HTTP transport, retaining strict JSON Schema, no tools, no retries, bounded output and the total deadline. An SDK dependency is unnecessary for that protocol. Private `.env` and the public example now use the regional `/chat/completions` URL. The isolated smoke runner also accepts `NEBIUS_API_KEY` when no Socrat secret or secret-file setting is supplied.

The initial regional structured test returned `provider_unavailable` at 8,109 ms. Subsequent owner-authorized tests established that generation works: a structured chat request with `SOCRAT_TUTOR_REASONING_EFFORT=low` returned a policy-accepted proposal in 3,797 ms with 210 output tokens under the normal 600-token/four-second settings. A separate small Responses test exhausted its 128-token allowance entirely on reasoning and returned incomplete output. Neither observation establishes dependable production quality or latency.

The owner then authorized the full synthetic review collection. At the owner's request, unfinished diagnostic requests omit `max_tokens`/`max_output_tokens` and allow a 120-second total deadline, accepting only complete, valid protocol responses. Earlier completed capped requests remain recorded with their original settings. This does not change the deployed application's deadline or output authority. Diagnostic reservations are accounting estimates, not provider-enforced spending limits. Restarting the in-flight local workers can leave billed calls without a checkpoint; provider billing cannot be reconstructed from the saved records alone.

## Completed generated reviews

Codex completed all 210 content review tasks in both the original and corrected private packets, with item-specific algorithm, boundary, objective-key, language, complexity and repair findings. Read `codex-ramakrishna-review.md`, `codex-sathish-review.md` and `codex-content-reviews.json` alongside each snapshot. The review found and fixed Python window initialization that allocated an extra O(k) slice, and C++ solve signatures that copied the input array. Corrected C++ and Java references each passed all 1,693 vectors and 24 CLI smoke cases; Python vectors are covered by the focused regression suite.

The corrected packet contains all 504 live outcome/review records: 502 proposals with provisional same-model opinions, and two provider failures without a usable hint. Local policy/reference checks accept 18 of 502 proposals. Only 22 proposals met four seconds; mixed-setting diagnostic p95 was 14,250 ms. Review indexes link the final files and `review-summary.json` records per-cell totals. References and hidden vectors remain local, outside provider contexts. Concrete findings include invalid n/p input examples, a full frequency-counting recipe at level 1, confusion between prefix and subarray conditions, and invented learner plans.

These reports identify their actual authors. They do not impersonate Ramakrishna or Sathish, populate human approval fields, or supply independent security/accessibility/privacy reviews. The `tutor_1.0.2` candidate has a separate nine-case diagnostic record: eight responses missed four seconds and one suggested invalid empty-input formatting. It remains unpromoted. Full release acceptance and M9 prerequisites remain open.

## What can close now versus later

Repository implementation, draft preparation, automated validation, reviewer handoff and owner policy decisions can progress now. Reviews may follow that preparation as requested. Actual staff/learner results, security/accessibility/privacy reviews, live model quality/latency, hosted golden journeys and operational drills must be recorded when available. Oracle and gVisor deferrals remain explicit; they cannot supply production readiness or silently close the inherited gates. The owner can accept a documented preparation scope separately, but full M7/M8 release acceptance remains pending.
