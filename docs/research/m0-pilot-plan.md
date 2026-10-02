# M0 pilot plan and facilitator checklist

**Updated:** 2026-10-02

**Owner and facilitator:** Sathish, Socrat

**Target completion:** 2026-10-12

**Status:** Plan prepared; privacy review, recruitment, sessions, synthesis, and approvals remain. No sessions have occurred.

## Confirmed arrangements

- Fifteen adults in India, five per launch track; online and in person, guided by Sathish, unpaid.
- Written notes only; no audio, video, or screen recordings.
- Private Google Drive storage, with private pilot records deleted 30 days after actual completion.
- Reviews will happen with reviewer identities kept private. No completed approval has been supplied.
- Owner reconfirmed DSA for Foundations, Interview, and Competitive learners in Python, C++, and Java, with bounded AI help and deterministic progress decisions. Full multi-role scope and metric approval remains pending.

## Recruitment allocation

These are targets, not completed sessions. They cover all nine combinations and give five participants per language.

| Track | Python | C++ | Java | Total |
|---|---:|---:|---:|---:|
| Foundations | 2 | 2 | 1 | 5 |
| Interview | 1 | 2 | 2 | 5 |
| Competitive | 2 | 1 | 2 | 5 |
| Total | 5 | 5 | 5 | 15 |

Include at least three Foundations learners with no programming experience and at least three people who use or request an accessibility adjustment. Ask what would help without collecting diagnoses. Avoid recruiting entirely from friends, employees, or technical early adopters. The owner confirmed these requirements are achievable.

## Before sessions

1. Obtain privacy approval for the [notice and consent](pilot-recruitment-and-consent.md). Confirm the exact business identity and Google Drive access/processing details privately.
2. Create separate private contact and session-note folders. Restrict access and disable public sharing. Keep participant records outside Git.
3. Copy the [session template](pilot-session-record-template.md) into private storage for each participant and assign opaque IDs such as `P001`.
4. Arrange an online meeting or venue individually. Disable recording/transcription and avoid tools that automatically retain session content.
5. Run the prototype using its [instructions](../../prototypes/concierge/README.md). For remote sessions, screen-share and operate it on the participant's instructions; log every facilitator action. This does not replace independent browser usability testing. Do not expose the local server publicly.
6. Record the prototype commit/version and run model/contract checks before sessions begin.

## Each session: 60–75 minutes

Follow the full [concierge protocol](concierge-pilot.md), with breaks and agreed adjustments.

1. Read the notice and record consent privately. Say: "We are testing the prototype, not you. Some parts are incomplete."
2. Before pitching Socrat, ask: "How do you decide what to practise? What happens when you get stuck? How do you know you are improving?"
3. Walk through goal, routing, diagnostic, daily plan, practice/help, evidence, and recovery. Let the participant choose and explain before you explain the intended answer.
4. Ask: "What goal did you choose, and what would you do next?" Record the answer without coaching.
5. Ask: "What does solving this with hints show? What would solving a fresh task without help show?" Record whether they distinguish assisted practice from independent proof.
6. Ask: "Would you choose this workflow or your current one? Why?" Record their actual choice, not polite agreement. Optional follow-up interest is separate.
7. Record confusing steps, trust concerns, accessibility issues, and every explanation or workaround. Coached key answers cannot count toward exit thresholds.

## Private tracking

Keep one row per participant: ID, track, language, experience, adjustment requested, consent, session date, prototype version, valid/invalid reason, four metric results, findings, and facilitator interventions. Contacts belong in a separate list. Replace invalid sessions and preserve their invalid reasons privately. Do not commit names, raw notes, meeting links, or reviewer identities.

## Closeout

1. Complete the [synthesis](pilot-synthesis-template.md) with approved anonymous aggregates: at least five valid sessions per track, four per language, and one per track/language cell.
2. For fifteen participants, require at least 12 showing the problem unprompted, 10 preferring the loop, 12 explaining their goal and next action, and 11 distinguishing assisted from independent evidence. For a larger sample use the [metric contract](../product/metric-contract.md) and document denominators.
3. Fix/retest Critical findings. Fix/retest High findings or formally remove affected scope. Assign owners and rationale to every material finding.
4. Obtain five role approvals using the [private review record](m0-private-review-record-template.md). Publish only role, reviewed version, decision, date, and opaque private-record reference.
5. Update affected contracts and rerun checks. Only after all evidence passes, review the [M0 gate](../delivery/milestones/m0-gate.md), accept approved ADRs, and change the machine contract to approved.
6. Record actual completion/deletion dates. Completion on 12 October means deleting private pilot records by 11 November 2026. Retain only the anonymous aggregate; reviewer approval records are separate and need their own agreed retention/access rules.

## Evidence to provide for final review

Provide anonymous track/language counts, beginner/accessibility coverage counts, the four metric totals and denominators, findings/retest outcomes, prototype version, and each role's decision/date/private evidence reference. Identities and raw notes stay private. Promised sessions and reviews are not completed evidence.
