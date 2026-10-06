# M8 gate

**NOT YET PASSED.** Repository implementation can be tested locally. Live model/learner exposure remains disabled by default.

Owner follow-up, 6 October 2026: the DSA/language reviewers also review hints, the owner coordinates provider privacy and final acceptance, and Ramakrishna is assigned operational alerts. Codex content reviews and owner-authorized live synthetic hint reviews are recorded in the private packets. Regional Nebius chat generation works with low reasoning effort; one structured proposal passed the normal deadline. The broader diagnostic findings do not establish independent model quality or dependable latency. Oracle staging and dedicated gVisor acceptance remain deferred until after milestone implementations. See [completion coordination](../../operations/m7-m8-completion.md).

| Requirement | Repository evidence | Remaining release acceptance |
|---|---|---|
| Core usable without LLM | Curated hint path and independent model/tutor switches; existing learning/execution paths remain available | Deployed outage and rollback exercise |
| Hint/assessment boundaries | Server-owned mode, released-content/session checks, progressive ceilings, reviewed-only solutions, Submit assistance pins | Independent security review and deployed concurrency checks |
| Leakage/correctness per cell | Conservative validators, adversarial fixtures and private nine-cell expert evaluation contract | Actual reviewed model/prompt/content sample: at least 500 cases, approved per-cell sampling minima, <3% premature leakage and material error, p95 <5 seconds; no assessment access |
| Bounded shadow advisor | Production planner envelope, permutation validation, immutable comparison, no mutation path | Expert preference and later independent-outcome analysis; production application remains prohibited |
| Budget/latency/rollback | Call/token limits, conservative reservations, total network deadline, prompt switch, cohort rollout, private counters and alert rules | Approved provider/model price ceiling, provider privacy/retention review, live alert delivery and latency/cost evidence |
| Content and UI | Optional versioned authored hints, existing pack release review, text rendering and assisted labels | Real hint/solution review and human accessibility review |

The evaluation checker reports `recorded_evidence_ready`, never approval. Input authenticity, sampling, named reviewers and approvals must be verified independently. Automated synthetic tests and supplied booleans are not human review evidence. Earlier milestone gates remain as recorded in their respective documents.
