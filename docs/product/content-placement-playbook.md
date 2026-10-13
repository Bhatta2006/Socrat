# Socrat Content Placement & Engagement Playbook

**Purpose:** Define what content learners see, where and when it appears, and how the product creates genuine moments of achievement so learners enjoy the platform *and* actually get better.
**Audience:** Learning design, content authors, product design, frontend, and QA.
**Companion to:** V1 PRD (§8 journey, §13 daily engine, §14 tutor, §15 practice, §21 dashboard, §22 retention).

---

## 0. Design stance (read this first)

1. **Content is small; practice is big.** Concept material is roughly 10–20% of any session. Everything else is retrieval, guided practice, independent work, and reflection.
2. **Reward evidence, not activity.** Every celebratory moment must be backed by a real signal (an independent solve, a retention pass, a mastery band change). Never celebrate a page view, a click, or time spent.
3. **"Feel good" means competence, progress, and closure.** The learner should regularly think: *"I could not do this last week, and now I can."* That feeling is the retention engine. Confetti is not.
4. **"Hooked" means "wants to come back because they are visibly improving."** Not compulsion, not fear of losing a streak, not slot-machine variability.
5. **Respect the PRD constraints:** no XP, no coins, no avatars, no leaderboards, no badge economy. Streaks count *planned days honored* (rest and reschedule count). Passive viewing never changes mastery.
6. **Engagement is a guardrail, learning is the goal.** If an engagement tactic raises time-in-app but lowers independent solve rate, remove it.

---

## 1. Content atom library

Everything the learner sees is built from a small set of reusable atoms. Authors write atoms, not "lessons"; the planner assembles them.

| Atom | Purpose | Size limit | Interaction | Counts as evidence? |
|---|---|---|---|---|
| **Hook line** | Why this matters, framed as a problem the learner has felt | 1–2 sentences | None | No |
| **Concept card** | Introduce one idea | ≤120 words + 1 code block or diagram | Expand "why" on demand | No |
| **Worked example** | Show a full solution with reasoning | ≤25 lines of code, annotated | Step through annotations | No |
| **Faded example** | Bridge from watching to doing | Same as worked, 1–2 blanks | Fill the blank, check | Light (guided) |
| **Step-through visualizer** | Make algorithm state visible (pointers, stack, queue, recursion tree) | ≤12 steps | **Predict the next state, then reveal** | No |
| **Trace task** | Practice mental execution | 1 snippet, ≤15 lines | Fill a trace table | Yes (tracing) |
| **Predict the output** | Fast retrieval | 1 snippet, ≤10 lines | Select/type answer | Yes (retrieval) |
| **Debug the bug** | Build error-spotting and invariants | 1 snippet with one defect | Fix with minimal change | Yes (debugging) |
| **Micro-lesson** | Repair a specific misconception | 60–90 s read, ≤1 diagram | None, then a fresh problem | No |
| **Pattern card** | Teach recognition ("when you see X, consider Y") | ≤80 words + 2 mini-examples | Classify 3 problems | Light |
| **Problem** | Core practice unit | Per exercise spec | Edit, run, submit, hint | Yes |
| **Exit explanation** | Check understanding in own words | 1 prompt, ≤3 sentences | Free text or structured | Yes (explanation) |
| **Reflection tap** | Learn what felt hard | 1 tap + optional sentence | Controlled choices | Scheduling only |
| **Optional clip** | Motivation or overview where licensed | ≤120 s | Play/skip | No |

### Authoring rules for all atoms
- **One idea per atom.** If it needs "and also", split it.
- **Problem-first language.** Open with the situation, not the definition.
- **Show before telling, then tell.** A concrete example precedes the abstraction.
- **Language-neutral intent, language-specific code.** Prose is shared; code blocks come from per-language adapters (Python, C++, Java). Never auto-translate code; each variant is validated.
- **No decoration.** Every image, animation, and sentence must carry meaning.
- **Accessible by default:** text alternatives for visuals, keyboard-operable steppers, never color-only meaning.

### Format hierarchy (what to build first)
1. Text + code (cheapest, versionable, per-language)
2. Step-through visualizer (highest value for DSA; reusable across languages)
3. Interactive checks (predict, trace, debug)
4. Micro-lessons for the top 30 misconceptions
5. Optional video clips (last; only if data shows lift)

---

## 2. Placement rules (what appears when)

Content is **triggered by learner state**, not shown in a fixed order.

| Trigger | What to show | Why |
|---|---|---|
| First visit to a new concept (learner has some baseline) | Hook line → **attempt first** (one easy problem) → then concept card | Productive struggle improves retention |
| First visit to a new concept (beginner) | Hook → worked example → faded example → problem | Reduces overload and early failure |
| Prerequisite is strong, concept is easy | Skip explanation; go straight to problem | Redundant exposure is a boredom trigger |
| Learner fails the same misconception twice | Micro-lesson + targeted problem (max one detour per session) | Fix the cause, not the topic |
| Learner requests a hint | Hint ladder; never swap in content to avoid the attempt | Preserve independence |
| Learner solves correctly but slowly | Strategy/recognition card, not remediation | Slow-correct is not failure |
| Learner solves 2 diverse items independently | Pattern card + harder variant | Reward mastery with progression |
| Syntax-only compile failures (3×) | Language micro-skill card + scaffolded repair | Don't mistake syntax friction for DSA failure |
| Retention check due | 2–5 min retrieval warm-up at session start | Spaced repetition |
| Return after absence | "How much time do you have?" → shortened plan; one retrieval + one win | Easy re-entry |
| End of session | Exit explanation → **session summary card** (see §5) | Closure and visible progress |

### Hard placement constraints
- No new instruction for a concept whose prerequisite is locked.
- At most **one** new idea introduced per session block.
- At least **one independent attempt** in every non-recovery session.
- In independent challenges and assessments: no concept cards, no hints, no solutions.
- Content never appears as an unbounded scroll; each block has a visible time estimate.

---

## 3. Track variants

| Dimension | Foundations (beginner) | Interview | Competitive |
|---|---|---|---|
| Opening | Hook with an everyday analogy | Hook with a real interview scenario | Hook with a contest situation |
| Explanation share | 20–30% | 10–20% | 5–15% (repair only) |
| Visualizers | Used heavily, slower pace | Used for new patterns | Used for advanced structures only |
| Tone | Encouraging, small steps | Direct, professional | Terse, performance-oriented |
| Success zone | 75–85% | 65–80% | 50–70% (stretch) |
| Signature content | Syntax micro-skills, tracing basics | Pattern cards, complexity trade-offs, "explain your approach" | Timed sets, upsolve reviews, counterexample drills |
| Win moments emphasize | First working program, first independent solve | Pattern recognized, timed solve | Rating-band step, faster solve vs. target |

---

## 4. Session templates

All timings are guidance; real durations are calibrated after pilot data.

### 20 minutes
1. Retrieval (3) · 2. Micro-concept or worked example, only if needed (4) · 3. One problem (11) · 4. Exit check + summary (2)

### 30 minutes
1. Retrieval (4) · 2. Concept card + visualizer (5) · 3. Guided problem (9) · 4. Independent problem (9) · 5. Exit + summary (3)

### 45 minutes
1. Retrieval (4) · 2. Concept/worked example (7) · 3. Guided problem (12) · 4. Independent challenge (17) · 5. Exit explanation (4) · 6. Summary + next-session preview (1)

### 60 minutes
As 45, plus a second independent problem with a *different structure* (never a longer lecture).

### 90 minutes
Two focused blocks with a 5-minute break prompt. Competitive track: one timed mini-contest + upsolve block.

### Rhythm rule
Alternate **effort types** within a session: recall → understand → apply with support → apply alone → explain. Never schedule two heavy independent problems back-to-back without a lighter block between them (except in contest practice).

---

## 5. Achievement moments (the "good feeling" system)

Every moment below is **triggered by real evidence** and **explains what changed**. They are grouped by time scale so learners receive a steady rhythm of progress without inflation.

### 5.1 Micro moments (seconds to minutes)

| Moment | Trigger | What the learner sees |
|---|---|---|
| **Clean first run** | Code compiles/runs without error on first try | Brief inline note: "Compiled first try." (no fanfare) |
| **Sample tests pass** | All visible tests pass | Tests turn green with a one-line recap of which cases covered what |
| **Prediction landed** | Correct prediction in a visualizer/trace | "You predicted that step correctly." |
| **Insight reveal** | Correct pattern recognized or key idea stated | One sentence: "This same idea solves [2 problems you've already seen]." |
| **Hint-free recovery** | Learner fixes a failing case with no hint | "You found that bug yourself." |

### 5.2 Block moments (end of a problem or check)

| Moment | Trigger | Content |
|---|---|---|
| **Independent solve** | Hidden tests pass, hint level ≤ 2 | Evidence line: "Solved independently. That counts toward Binary Search." |
| **Complexity named** | Correct complexity explanation | "You correctly explained why this is O(log n)." |
| **Faster than last time** | Solve time below own prior median on same concept | "About 30% faster than your earlier binary-search solves." |
| **Repair complete** | Previously failed misconception passes on fresh item | "Last week's boundary mistake didn't show up today." |

### 5.3 Session moments (end of day)

The **Session Summary Card** is the most important reward in the product. It always contains:
1. **What you did** (2–3 items, specific).
2. **What changed** (one skill state movement with evidence count, or an honest "evidence still building").
3. **What's next** (tomorrow's session, one line, already chosen).

Example:
> **Today:** 1 retrieval check, 1 guided problem, 1 independent problem.
> **What changed:** Hash Maps moved from *Developing* to *Capable* (4 independent solves, 2 assisted).
> **Tomorrow (30 min):** One mixed problem combining hash maps and arrays.

If nothing moved, say so plainly and describe the useful evidence gained: *"No band change today, but you now have a consistent independent pattern on arrays."* Never invent progress.

### 5.4 Weekly moments

| Moment | Trigger | Content |
|---|---|---|
| **Weekly assessment result** | Unseen mixed assessment submitted | Concept-by-concept evidence, strongest gain, one honest gap, next-week plan |
| **Retention confirmed** | Delayed check passed | "You still have this after 7 days." |
| **Planned days honored** | Learner met their own schedule | Count of planned days kept (rest days count) |
| **Plan adjusted for you** | Adaptation fired | One sentence naming the evidence that triggered it |

### 5.5 Milestone moments

| Moment | Trigger |
|---|---|
| **First independent solve** | First hint-free hidden-test pass |
| **First concept mastered** | Meets full mastery definition |
| **Baseline vs. now** | Final or mid-program assessment: before/after independent solve rate |
| **Foundations to DSA unlock** | Language-readiness gate passed (beginners) |
| **Band step** | Competitive learner reaches next released difficulty band |
| **Program complete** | Final assessment viewed: evidence report, remaining gaps, honest next step |

### 5.6 Visual treatment
- Skill map nodes animate a **state change** (e.g., ring fills, label changes) when a band moves. Meaning is also conveyed via text, never color alone.
- Small, fast, tasteful motion (≤1 second). No full-screen confetti except for rare milestones (first independent solve, first mastered concept, program complete).
- Sound is off by default.

---

## 6. Feedback copy standards

### Principles
- **Specific beats generic.** Say what the learner did.
- **Evidence-linked.** Tie praise to a real signal.
- **Process over trait.** Praise strategy and persistence, not "you're smart."
- **Honest in failure.** Neutral, forward-looking, no shame.
- **Short.** One or two sentences.

### Copy bank

| Situation | Use | Avoid |
|---|---|---|
| Independent solve | "Solved without hints. That counts as independent evidence." | "Amazing!!! You're a genius!" |
| Fixed own bug | "You traced the failing case and fixed it yourself." | "Great job!" |
| Wrong answer | "That case returns 3, expected 2. What does your loop do on the second element?" | "Incorrect." |
| After level 3+ hint | "Good progress. You'll try a similar one on your own next." | "You needed a lot of help." |
| Slow but correct | "Correct. The next step is recognizing the pattern faster." | "That took too long." |
| Retention fail | "This needs a refresh. It's normal to forget after a week." | "You forgot this." |
| Missed days | "Welcome back. Here's a [20]-minute restart." | "You broke your streak." |
| No band change | "Evidence gained, no band change yet." | Fake progress bars |

### Tone by track
- **Foundations:** warm, reassuring, concrete.
- **Interview:** collegial and professional.
- **Competitive:** concise, data-forward.

---

## 7. Keeping learners engaged (mechanics)

1. **Keep the difficulty in the success zone.** Wrong difficulty is the biggest cause of boredom (too easy) or quitting (too hard).
2. **Make the next step visible.** Always show what's next and how long it takes.
3. **Vary the activity type** within every session (§4 rhythm rule).
4. **Prediction before reveal.** Ask the learner to commit to an answer, then show the result. Surprise from being wrong or right is engaging and memorable.
5. **Short loops.** A feedback event at least every 3–5 minutes.
6. **Real insight beats rewards.** "This idea unlocks three other problems" is a stronger hook than a badge.
7. **Safe choice.** Offer choices of representation (text-first, trace-first) or order of two problems; never a choice to skip practice.
8. **Closure.** End every session on a summary, never mid-task, so the day feels complete.
9. **Anticipation, honestly.** Preview tomorrow's session so there's a reason to return: "Tomorrow: your first problem combining two patterns."
10. **Do not manufacture urgency.** No countdowns, fake scarcity, or loss-aversion tricks.

---

## 8. First seven days: emotional arc script

The first week determines whether the learner believes the product works.

| Day | Goal | Content design | Target feeling |
|---|---|---|---|
| **0 (Diagnostic)** | Placement without anxiety | Low-pressure items, "no wrong placement" framing, evidence-count results | "It understands where I am." |
| **1** | **First independent win within 20 minutes** | Easy-but-real problem at the learner's level; instant feedback | "I can do this." |
| **2** | Visible skill change | Concept card + visualizer; session summary shows first band movement or evidence | "I'm actually progressing." |
| **3** | Mild challenge | Slightly harder problem; hint ladder demonstrated as helpful, not a crutch | "Help is there when I need it." |
| **4** | Consolidation | Retrieval warm-up recalls Day 1–2 (first spaced repetition) | "I remember this." |
| **5** | Pattern insight | Pattern card linking two earlier problems | "Things are connecting." |
| **6** | Stretch | One tougher independent task | "I can handle harder things." |
| **7** | **Weekly assessment + reflection** | Unseen mixed items; results show concrete gains vs. baseline | "I can prove I've improved." |

### Day-1 rule
If a learner hasn't produced a successful independent attempt in their first session, treat it as a **design failure**, not a learner failure: lower difficulty, add a worked example, and re-sequence.

---

## 9. Handling boredom, frustration, plateaus, and absence

| State | Signals | Response |
|---|---|---|
| **Bored** | Fast clean solves, skipped explanations, low challenge rating | Remove redundant guided items, raise difficulty one band, add transfer problems |
| **Frustrated** | Repeated failures, long idle time, abandoned attempts | Offer a choice: prerequisite refresher or simpler analogous problem. Never "show answer" first |
| **Overwhelmed** | Multiple syntax errors, session abandonment | Shrink block size, drop a difficulty band, lower novelty, offer a lighter day |
| **Plateau** | Flat mastery for 2+ weeks | Change representation, add a project-like integrated task, show evidence of what *has* improved |
| **Fatigued** | Late-session accuracy drop | Suggest ending after the independent attempt; defer optional content |
| **Returning after absence** | Missed ≥2 planned days | "How much time do you have?" → shortened plan, one retrieval + one guaranteed-winnable problem |
| **Help-dependent** | High share of level ≥3 hints | Require a stated plan before next hint, add no-solution challenge, celebrate independent recoveries |

---

## 10. Content quality bar

Every atom must pass this checklist before publication.

### Correctness and pedagogy
- [ ] Technically correct; reviewed by a domain expert
- [ ] One clear learning objective, mapped to a concept version
- [ ] Prerequisites declared and satisfiable
- [ ] Examples are minimal, representative, and original (or licensed)
- [ ] No accidental solutions to assessment items
- [ ] Misconceptions it targets are tagged from the controlled taxonomy

### Language adapters
- [ ] Python, C++, Java code compiles/runs and produces identical behavior
- [ ] Idioms are native to each language (not literal translations)
- [ ] Missing variants are marked unavailable, not silently translated

### Experience
- [ ] Reading time within limit
- [ ] Works on laptop and responsive mobile for reading
- [ ] Keyboard and screen-reader operable; meaning not color-only
- [ ] Tone matches track guidelines

### Operations
- [ ] Rights and license recorded
- [ ] Version, owner, reviewer, and changelog present
- [ ] Rollback ID and quarantine path exist
- [ ] Learner "report an issue" link works on every atom

---

## 11. Authoring templates

### Concept card
```yaml
id: concept_card.binary_search.v1
concept: binary_search
track_eligibility: [foundations, interview, competitive]
objective: "Explain why binary search halves the search space and where boundary errors come from."
hook: "Finding a name in a phone book doesn't mean checking every page."
body_md: |
  Binary search works on a **sorted** range. Compare the middle element to the target,
  then discard the half that cannot contain it. Repeat until found or the range is empty.
why_expand_md: |
  Each step halves the remaining range, so n elements need about log2(n) steps.
language_adapters: [python, cpp, java]
misconceptions_targeted: [binary_search_boundary]
est_read_seconds: 45
```

### Step-through visualizer
```yaml
id: visualizer.binary_search.trace.v1
type: predict_then_reveal
steps:
  - state: {lo: 0, hi: 7, mid: 3}
    prompt: "arr[mid] is 9 and the target is 14. Which pointer moves?"
    options: ["lo = mid + 1", "hi = mid - 1"]
    correct: 0
    explain: "9 < 14, so the target must be to the right of mid."
```

### Micro-lesson
```yaml
id: micro.binary_search_boundary.v1
misconception: binary_search_boundary
trigger: "two failures on boundary conditions"
body_md: |
  The most common mistake is an infinite loop caused by `mid` never excluding itself.
  Always move a pointer **past** `mid` (`mid + 1` or `mid - 1`).
followup: fresh_problem_same_misconception
max_read_seconds: 75
```

### Achievement moment
```yaml
id: moment.independent_solve.v1
trigger: attempt.score >= 0.9 AND hint_level <= 2 AND mode == practice
evidence_required: problem_attempts.id
copy: "Solved without hints. That counts toward {concept_name}."
visual: tick_animation_short
confetti: false
```

---

## 12. Worked example: "Binary Search" content pack (interview track, 30 min)

**Retrieval (4 min).** *Predict the output:* a short loop over a sorted list that returns the index of a value. One Python/C++/Java variant per learner choice.

**Hook (10 s).** "Finding a word in a dictionary: you never read every page."

**Concept card (2 min).** ≤120 words: sorted range, compare middle, discard half. One annotated snippet:

```python
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

**Visualizer (3 min).** Predict-then-reveal over 6 steps on a sample array. Learner commits to "which pointer moves?" before each reveal. Insight moment after step 6: *"Each step cut the remaining range in half."*

**Guided problem (9 min).** Find the first index where a condition becomes true; hint ladder available. Targets boundary mistakes.

**Independent problem (9 min).** Different structure (search in a rotated array, easier variant). No hints, no solutions.

**Exit explanation (2 min).** "Why does this loop terminate?" (structured prompt, rubric-scored).

**Session Summary Card.**
> *Today:* 1 retrieval, 1 guided, 1 independent problem.
> *What changed:* Binary Search moved to *Developing* (3 evidence items; 1 independent).
> *Tomorrow (30 min):* Same pattern, new structure, plus a recall check from Hash Maps.

**If the learner fails the independent problem on a boundary condition:** show the boundary micro-lesson, schedule a fresh variant tomorrow, and use the copy "Boundary conditions trip up most learners. One more targeted problem tomorrow."

---

## 13. Measuring whether this actually works

Run these before locking the design (maps to PRD §34).

| Question | Test | Primary metric |
|---|---|---|
| Text + visualizer vs. video for concept intro | A/B on the same concept | Transfer-problem success 48–72 h later |
| Attempt-first vs. explain-first | A/B for learners with a baseline | Independent next-problem solve rate |
| Session Summary Card on/off | A/B | D7 retention and next-session start rate |
| Evidence-linked vs. generic praise | A/B | Voluntary assessment starts, return rate |
| Predict-then-reveal vs. passive stepper | A/B | Retrieval accuracy at 7 days |
| Exit explanation on/off | A/B | 7-day retention |

### Guardrail metrics (must not worsen)
- Independent solve rate and retention (learning)
- Hint-level ≥3 rate and abandonment
- Anxiety or "feels judged" feedback in interviews
- Content defect rate

### Leading indicators (diagnostic only)
- Time to first independent solve (target: Day 1)
- Share of sessions ending with a viewed summary card
- Share of learners who start tomorrow's session within 36 hours
- Qualitative: "What made you come back?" in week-one interviews

Do **not** optimize watch time, session length, or notification opens.

---

## 14. What we will not do (ethical guardrails)

- No fake progress, inflated bands, or celebration without evidence.
- No variable-ratio reward mechanics, loot-box-style surprises, or engagement-maximizing randomness.
- No loss-framed streak pressure, countdown timers, or public shaming.
- No paywall or upsell at a moment of struggle.
- No celebrating assisted solves as independent ones.
- No hiding a plateau; always show what the evidence says and what to do next.
- No dark patterns in reminders: consented, quiet-hours-respecting, easy to disable.

---

## 15. Implementation checklist (first pass)

- [ ] Build the atom schema and per-language adapter support (PRD §11.2, §16)
- [ ] Ship the step-through visualizer component with predict-then-reveal
- [ ] Author starter atoms for the top 10 concepts per track
- [ ] Author micro-lessons for the top 30 misconceptions
- [ ] Implement trigger-based placement rules (§2) in the planner
- [ ] Build the Session Summary Card and skill-state change animation
- [ ] Write the copy bank and run it through a tone review
- [ ] Run the Day-1 and first-week script in the concierge pilot
- [ ] Instrument achievement-moment events with evidence IDs
- [ ] Launch the A/B tests in §13 once traffic allows

---

*Principle to remember:* the learner should finish each session thinking "I did real work and got measurably better." If a feature doesn't support that sentence, cut it.
