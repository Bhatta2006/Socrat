# M7 acceptance records

The owner requested completing M7 content and acceptance while keeping the sixth item, dedicated-host M6 runtime acceptance, deferred. M7's repository checks and the human/deployed acceptance records are tracked separately. Runtime deferral does not provide reviewed content, learner calibration, staff dogfood or staging evidence.

## Decisions and evidence required

Latest owner decisions, 6 October 2026: Ramakrishna is assigned DSA/C++/teaching and hint review; Sathish is assigned Python/Java review. Reviews follow repository preparation. The owner selected the proposed activation definition and zero initial penalty, pending independent review. Two staff testers are available, learners are to be recruited next week, and Oracle staging/runtime acceptance remain explicitly deferred. See the [completion handoff](m7-m8-completion.md). These decisions supersede the earlier assignment and sixty-second proposal deferrals below, without approving content or measurements.

The owner chose a limited pilot with newly authored content and public curriculum research. The [limited-pilot guide](m7-limited-pilot.md) records the six-topic scope, original draft bank and publisher links. The older two-concept authoring fixture cannot support full V1 DSA promises. All three tracks need Python, C++ and Java variants, with reviewed lesson/check content and genuinely distinct practice families and repairs. Changing family identifiers on copies is not a content bank. Draft preparation does not approve content or released goal promises.

Reviewer assignments are explicitly deferred by the owner. When reviewers are available, name the content author and independent content, language, accessibility and release reviewers. Record review decisions against the exact pack digest and retain private references. Technical verification supports these decisions; generated metadata and automated test fixtures are not review records.

The owner requested a recommendation. The [pilot policy proposal](../../contracts/product/m7-pilot-policy.json) selects the PRD's current-diagnostic/confirmed-plan/independent-Submit candidate within 48 hours, with explicit cohort exclusions, and proposes a sixty-second wrong-Submit practice penalty. Both remain pending independent product/metric review. The older plan-start contract is historical candidate wording, not a second interchangeable activation definition. A proposed value and the same value in synthetic tests do not establish launch calibration.

The owner explicitly deferred unavailable staging, real learner/staff measurements and human accessibility evidence. When available, execute the nine track/language golden journeys against the reviewed bank and record the actual environment and owners. Review keyboard navigation, focus, screen-reader announcements, code editing, zoom/reflow, contrast, saved history and untimed practice. Expanded local desktop/mobile journeys are regression evidence using synthetic inventory; they do not replace this review. Record execution capability explicitly while dedicated-host runtime acceptance remains deferred.

Approve a sampling plan before collecting duration and dogfood data. Choose minimum eligible normal-session observations and distinct attempted exercises per cell; this tool supplies no supposedly calibrated default. Measure session active time consistently with the owned-goal telemetry, excluding pauses and worker/queue wait. Keep timed sessions, incomplete sessions, invalid records, test/staff/synthetic records, deleted-before-eligibility records and known-corrupt records out of learner duration calibration. Staff sessions are appropriate for the separate staff dogfood exercise audit.

## Private evidence contract and evaluator

The [evidence schema](../../contracts/schemas/m7-acceptance-evidence.schema.json) is versioned `m7_acceptance_1.0.0`. Keep populated evidence files in access-controlled storage, outside the public repository. Use opaque session identifiers and review identifiers. Do not include names/emails of learners, code, responses, transcripts or provider payloads. Review references point to records that authorized owners verify; the evaluator does not fetch or authenticate them.

An evidence file declares the immutable `pack_digest`, `author_id`, explicitly approved sampling minima, `activation_definition`, four overall review decisions (`content_review`, `penalty_review`, `metric_review`, `release_review`), and the nine `cells`. Each cell declares `track`, `language`, `golden_environment`, golden/accessibility/language reviews, duration observations with a `duration_reference`, and distinct attempted exercise identifiers with a `dogfood_reference` and confirmed material defect identifiers. Each review decision is `pending`, `approved`, or `rejected`, with a reviewer identifier and a reference for non-pending decisions. An author's own approval cannot satisfy an independent review.

Run with the API package on `PYTHONPATH`:

```text
python -m socrat.learning.acceptance path/to/launch-pack.json path/to/private-evidence.json
```

The evaluator checks exact content identity, launch/session content, the static and production-planner audits, explicit review decisions, deployed golden records, language/track inventory, distinct samples and reviewed sampling minima. Every cell must meet median normal-session duration error **at most 20%** and confirmed material exercise defect rate **strictly below 2%**. Duration error is `abs(actual_seconds / 60 - planned_minutes) / planned_minutes`. Dogfood counts each attempted exercise once in each cell; the defect numerator must be a subset of that inventory. Protected assessment inventory cannot be used to satisfy practice coverage. One failing cell cannot be hidden in an aggregate.

The output contains counts, rates, content digest and gap codes. It omits individual identifiers and private review/measurement references. Exit status is nonzero for invalid input or unresolved evidence. `recorded_evidence_ready` means the supplied records satisfy these checks; it is not an independent approval or a production publication command. Named owners must verify the source records and sign the gate. The output explicitly labels M6 runtime acceptance deferred. New launch publication still follows the authenticated editorial workflow.

Regenerate schemas with `python scripts/validation/export-m7-contracts.py`. Synthetic approved records exist only in evaluator tests and never establish M7 acceptance.
