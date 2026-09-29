# M0 concierge pilot protocol

## Purpose

Validate the problem, language, goal model, deterministic routing, daily-loop concept, assistance boundary, and evidence model before M1 implementation. This pilot does not estimate production learning efficacy and must not be reported as such.

## Required sample

Fifteen valid sessions minimum:

- five Foundations learners, including at least three with no prior programming experience;
- five Interview learners across intern/new-grad and experienced targets;
- five Competitive learners, including novice and intermediate/advanced targets;
- all nine track × language cells represented at least once;
- at least four participants using each of Python, C++, and Java;
- at least three participants who use or request an accessibility accommodation;
- avoid recruiting only friends, employees, or highly technical early adopters.

If a participant fits multiple tracks, recruit against the single goal they genuinely intend to pursue now. Record secondary interests but do not count one person twice.

## Ethics, consent, and data minimization

- Recruit adults 18+ only.
- State that this is research for an unfinished product, not instruction, employment advice, or a scored assessment.
- Obtain explicit consent separately for participation, recording, and follow-up contact.
- A participant may skip any question or stop without penalty.
- Store participant identity/contact separately from session notes; use `P001`–`P015+` IDs in analysis.
- Do not collect employer-confidential interview questions, private contest credentials, demographic attributes not needed for sampling, or unnecessary raw code history.
- Delete recordings on the stated schedule after synthesis; retain redacted observations and decisions according to the pilot notice.

The product/privacy owner must fill the actual retention period and controller/contact details before recruitment. That is a launch blocker for the pilot.

## Prototype fidelity

The prototype must support the same conceptual sequence for each participant:

1. qualification and track/language selection;
2. structured goal confirmation;
3. a short staged diagnostic sample;
4. placement and feasibility explanation with reason codes;
5. one proposed daily plan;
6. one practice task with the staged hint interaction;
7. an independent-check example;
8. a progress/evidence explanation;
9. missed-day recovery scenario.

The facilitator may operate hidden controls (“Wizard of Oz”) but cannot pretend model output or scoring is automated. Every manual action is logged.

## Session structure (60–75 minutes)

### 1. Context interview — 10 minutes

Ask without pitching:

- Tell me about the last time you tried to learn or practice DSA.
- How did you decide what to do next?
- Where did you get stuck, and what did you do?
- How did you know whether you were improving?
- What did you stop doing, and why?

Capture concrete past behavior. Do not accept “I would use” as proof of a present problem.

### 2. Qualification and goal — 10 minutes

Ask the participant to use the prototype unaided. Observe:

- whether the three goal choices are mutually understandable;
- whether beginners feel included;
- whether target and time questions are answerable;
- whether the normalized goal feels accurate and non-promissory;
- whether waitlist/bridge/feasibility language feels honest.

### 3. Diagnostic and routing — 10–15 minutes

Use a track/language-appropriate mini-set. The purpose is comprehension of adaptive placement, not a valid mastery estimate. Ask the participant to explain why the next item changed. Reveal the reason after their answer.

### 4. Daily loop and help — 15 minutes

Give one realistic problem. Require an attempt before the first hint. Demonstrate at most three hint levels and ask:

- Did the help preserve something for you to figure out?
- At what point would it feel like the system solved the problem?
- Would you trust the system to classify this result as independent or assisted? Why?

### 5. Evidence and recovery — 10 minutes

Show a provisional mastery/evidence view and a missed-day replan. Ask the participant to explain:

- what the product knows;
- what remains uncertain;
- why a lesson view did not increase mastery;
- what changed after the missed day.

### 6. Value and close — 10 minutes

- Compare this workflow with what you use today.
- Which single part would you keep? Which would you remove?
- What would make you stop trusting it?
- Ask for a behavioral commitment: join a 14-day follow-up pilot, provide a preferred start window, or decline.

Do not ask “Would you pay?” in isolation. If pricing is shown, ask the participant to choose between a concrete plan, current alternative, waitlist, or no action.

## Observation record

Create one append-only record per participant:

| Field | Value |
|---|---|
| Participant ID | |
| Track / language cell | |
| Recruitment source | |
| Prior DSA behavior | |
| Accommodation used/requested | |
| Recording consent | yes/no |
| Problem demonstrated unprompted | yes/no + evidence |
| Goal restated correctly | yes/no + quote/paraphrase |
| Next action understood | yes/no |
| Assisted vs independent understood | yes/no |
| Routing outcome and comprehension | |
| Critical confusion | |
| Trust breaker | |
| Current alternative | |
| Concrete follow-up commitment | |
| Facilitator interventions | |
| Severity-tagged findings | |

Never paste secrets, contact details, or unnecessary verbatim sensitive material into the shared result document.

## Finding severity and disposition

| Severity | Definition | Required action |
|---|---|---|
| Critical | Could misroute, fabricate coverage, misrepresent mastery, expose protected data/content, or systematically exclude a launch group | Fix and retest before M0 pass |
| High | Blocks goal/next-action comprehension or destroys trust for a track | Fix or formally remove affected scope before M0 pass |
| Medium | Causes friction or recurring misunderstanding with a workaround | Assign owner and target milestone |
| Low | Preference/copy polish without decision impact | Backlog with evidence |

Every material finding receives one disposition: `accept`, `change`, `defer`, or `reject`, with owner and rationale. “Interesting” is not a disposition.

## Pilot exit calculation

The session is valid only if the participant matches recruitment criteria, completed through the evidence section, and was not coached into the key answers. Replace invalid sessions; preserve them in the log with the invalid reason.

M0 pilot passes only when:

- sample coverage requirements are met;
- thresholds in the [metric contract](../product/metric-contract.md) are met;
- no unresolved Critical finding remains;
- each High finding is fixed and retested or results in explicit scope removal;
- prototype changes are reflected in the normative contracts;
- Product, Learning Design, and Design sign the synthesis.

## Files to attach before gate review

- recruitment screener and consent notice actually used;
- participant coverage table without direct identifiers;
- session evidence records;
- finding register and dispositions;
- prototype version/hash/screenshots;
- metric calculation output;
- signed synthesis with go/change/stop decision.
