# Domain glossary

This glossary is normative. Product copy may use friendlier language, but stored entities, events, APIs, analytics, and tests must preserve these meanings.

| Term | Normative meaning | Must not mean |
|---|---|---|
| Goal | A learner-confirmed capability target with track, threshold/outcome, language, target date or no-date state, and time budget | A free-text wish or guaranteed employment/rating result |
| Goal template | The versioned field and evidence contract for Foundations, Interview, or Competitive intent | A course or static syllabus |
| Goal track | The learner’s declared outcome family: Foundations, Interview, or Competitive | Current placement or UI marketing segment |
| Active policy | The deterministic instruction/assessment policy currently governing the learner | A permanent identity; an interview learner may temporarily use a foundations bridge |
| Target coverage | The versioned concepts, difficulty/rating range, languages, and assessments that are released for a goal | Whatever an LLM claims it can teach |
| Skill pack | A versioned, domain-neutral package containing concepts, prerequisite graph, evidence contracts, content metadata, assessment blueprints, and policy overlays | Executable application code with unrestricted privileges |
| Concept | The smallest independently evidenced capability node suitable for prerequisite and mastery decisions | A video, lesson page, or broad topic label |
| Competency | Observable application of one or more concepts at a declared context and performance level | Content completion |
| Prerequisite edge | A versioned directed requirement that must be ready before dependent new instruction | A loose recommendation inferred at request time |
| Curriculum | A versioned, goal-specific DAG projection of required and optional concepts with rationale and feasibility | A day-by-day immutable schedule |
| Daily plan | A dated, capacity-bounded set of learning blocks selected from eligible curriculum needs | A backlog or full curriculum |
| Learning block | A bounded activity such as retrieval, micro-instruction, guided practice, independent challenge, review, assessment, or recovery | An arbitrary chat interaction |
| Exercise | A released practice task with concept mapping, constraints, language variants, reference solutions, tests, evidence mode, exposure policy, and rollback version | Unreviewed generated text |
| Item | A scorable prompt instance in practice, diagnostic, or assessment | Necessarily a coding problem; it may be trace/explain/select/implement |
| Attempt | One logical learner effort against a versioned item; runs and edits belong to the attempt until finalization or expiry | Every code-run button press |
| Run | One isolated execution of code and tests within an attempt | A scored submission by itself |
| Submission | A learner action requesting final evaluation of the current attempt | Any autosave or run |
| Evidence event | An immutable record that may inform learner state after validity and mode checks | A mutable aggregate or raw analytics click |
| Evidence quality | A deterministic multiplier/status reflecting independence, assistance, item validity, operational health, and scoring confidence | A moral judgment about the learner |
| Independent evidence | Valid work performed without disallowed hints/solution exposure for that item and mode | Work merely marked “independent” by the learner |
| Assisted evidence | Valid work completed after policy-permitted assistance; useful for learning but weighted separately from independent proof | Invalid or worthless work |
| Operational failure | Runner, network, provider, content, or system failure that prevents a fair learning judgment | Learner failure; it always has zero negative evidence weight |
| Mastery estimate | A versioned deterministic estimate of current concept capability derived from valid evidence | A credential, certainty, or content completion percentage |
| Confidence | A measure of evidence sufficiency/diversity supporting a mastery estimate | The same value as mastery |
| Retention factor | A scheduling/uncertainty adjustment based on evidence age and delayed checks | Automatic nightly loss of historical mastery |
| Mastered | A state requiring configured mastery and confidence thresholds, independent/diverse evidence, prerequisite readiness, unseen assessment, and retention/provisional rules | “Watched,” “completed,” or “got one answer right” |
| Misconception | A versioned, observable error pattern with detection evidence and repair mapping | A personality label |
| Diagnostic | A staged placement process choosing items to reduce uncertainty about goal-relevant prerequisites | An exam claiming complete knowledge |
| Assessment | A protected, independent evidence mode using unseen parallel forms and deterministic scoring where possible | Practice with hidden labeling |
| Parallel form | A separately exposed assessment form matched on blueprint and calibrated difficulty | The same problem with renamed variables |
| Socratic hint level | A policy-bounded assistance tier that progresses from elicitation toward explanation | An unrestricted chatbot response length |
| Solution exposure | Output semantically sufficient to reconstruct the target solution beyond the allowed assistance level | Any educational explanation |
| Candidate envelope | The deterministic set of currently eligible options an advisor may rank | The whole content catalog |
| Advisor | A non-authoritative component that may propose a choice from an approved candidate envelope | An agent that writes curriculum or learner state |
| Policy version | An immutable identifier for the exact rules and thresholds applied to a decision | An application release number alone |
| Reason code | Stable machine-readable explanation of a material deterministic outcome | Unstructured model prose |
| Content version | Immutable released representation of a concept/item and its language/test assets | A mutable database row |
| Quarantine | Immediate prevention of new use/scoring while preserving the artifact and affected-attempt history for audit and repair | Deletion |
| Meaningful session | A session containing at least one finalized valid learning action defined in the metric contract; page views alone never qualify | Login, reminder open, or passive reading alone |
| Activated learner | A qualified learner who confirmed a goal, completed the diagnostic, and started the first daily plan within 48 hours | Any registered account |
| Independently Verified Competency (IVC) | A concept meeting the defined mastery, confidence, independent/diverse evidence, assessment, prerequisite, and retention/provisional conditions | A badge issued for completion |
| Learning incident | A defect that may have changed content validity, evidence, mastery, or learner decisions | Only an infrastructure outage |
| Release coverage | The explicit track/language/difficulty matrix for which enough valid content and assessment inventory exists | Aspirational roadmap coverage |

## Naming rules

- Use `learner`, not student, when referring to the product user.
- Use `exercise` for an authored practice asset and `attempt` for learner work.
- Use `run` only for isolated code execution.
- Use `assessment` only when assistance is disabled and exposure controls are active.
- Use `estimated mastery` or a named band in learner copy; never imply formal certification.
- Use `waitlist` when requested coverage is unavailable; never silently downgrade or fabricate.
- Use `Python`, `C++`, and `Java` in copy; use `python`, `cpp`, and `java` as stable machine IDs.

