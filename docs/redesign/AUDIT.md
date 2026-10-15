# Socrat redesign: audit

Phase 0 of the "Learn it. Then prove it." redesign (`UI-redefining` spec). Taken on branch
`redefined` at `c26accd`, from the running demo. Screenshots are in `docs/redesign/before/`
(`{dark,light}/{phone,tablet,desktop}/{page}.jpg`, captured by `scripts/web/capture-redesign.mjs`).

The companion "Current UI/UX and Redesign Handoff" document the spec refers to is not in the
repository. The behaviour rules below were taken from the code and the end-to-end tests, which
encode the same rules: course-scoped search, topic-scoped company questions, checkpoint gates,
evidence-based progress and the playground's sandbox and no-preset guarantees.

## 1. Visual inconsistencies

| Area | Finding |
| --- | --- |
| Palette | Three palettes coexist. The app uses emerald primary, amber for streaks, green for success and sky blue for streak freezes (`globals.css`, `today/page.tsx`). Landing and login use a separate daisyUI theme (lime primary, violet secondary) in `landing.css` and `login.css`. |
| Brand | The wordmark is a sparkle icon in an emerald square (`shell.tsx`). The landing page and login draw their own versions. |
| Type | Geist for everything. Page titles are 30–36 px semibold, which is no stronger than card titles. Eyebrows use primary-coloured caps. |
| Depth | Gradients (`bg-gradient-to-br` on the Today hero), a dotted-grid background, `backdrop-blur` on headers and the mobile nav, and coloured shadows (`shadow-primary/20`) appear in 10 files. |
| Hero | The Today hero is a tinted card of the same weight as the cards around it. Two "explore" cards sit above it and compete with it. |
| Raw colour | 54 raw hex values in 4 component files, mostly the landing scene and login. |
| Celebration | `canvas-confetti` fires on goal completion, lesson completion and checkpoint passes (10 files). Achievement badges appear on Progress. Both are banned by the style lock. |
| Labels | Mixed names: "Plan" and "Roadmap", "Library" and "Practice library", "Concept playground" and "Visual playground", "Assessments" and "Weekly assessment", "Sign in" and "Sign out". UI copy says "concept"; the spec says "skill". |

## 2. Mobile discovery

- The bottom nav has Today, Plan, Library, Assessments and Progress. Playground and Company
  questions can only be reached through cards and links. Focus sprint can only be reached from
  the library page.
- The mobile nav is translucent with blur, and the floating tutor button overlaps the hero
  card at 390 px (`before/light/phone/today.jpg`).
- Search is a narrow field in the header with no visible label at 390 px.

## 3. Accessibility

- Focus rings use `ring-ring/50`, a 50% alpha emerald ring, which is faint on dark cards.
- Status relies on colour in places: `band-dot` is a coloured dot with a text label beside it,
  but heatmap cells and the week strip are colour only.
- Difficulty badges use green, amber and red tints. In dark mode, amber text on its tint is low
  contrast.
- Several icon-only buttons rely on `aria-label`, which is fine, but disabled buttons have no
  adjacent explanation (for example Play under reduced motion, which shows only a disabled
  button).
- The view-transition slide and the unlock glow are reduced under `prefers-reduced-motion`. The
  `Ring` draw animation and `NumberTicker` honour it. Confetti checks it via `celebrate.ts`.

## 4. Token usage

| Token | Uses | Files | New meaning (spec 4.3) |
| --- | --- | --- | --- |
| `success` | 96 | 23 | Foreground plus check icon and label |
| `warning` | 45 | 12 | `--attention` |
| `streak` | 72 | 9 | Neutral surface with line icon |
| `destructive` | 120 | 26 | `--attention`, outlined |
| `text-primary` | 79 | 32 | Fails 4.5:1 as text on dark cards once primary is violet `#7D39EB` (3.1:1). Text uses a new `--brand-text` token: lilac in dark, violet in light. |
| `sky-*` | 14 | 3 | Removed (freeze indicator becomes neutral) |

## 5. Status mapping to backend data

Sources: `services/api/src/socrat/mastery/model.py` (`ConceptState`, `band`),
`planner/engine.py` (roadmap `status`), `learn/views.py` (`lesson_done`, `quiz_done`,
`review_due`, `recent[].assisted`, `solves`).

`mastered` means the weighted Beta estimate is ≥ 0.8 with confidence ≥ 0.55. Assisted
successes still add (reduced) weight, so mastery is **not** purely independent evidence. Per spec
section 6, rule 2, the lime filled state is labelled **Mastered**, not "Shown independently". The word
"independent" is used only where the backend records it: `recent[].assisted == false`, and
`solves.independent_solves`, which counts accepted code submissions with assistance level 0.

| Visual state | Roadmap item (`/plan`) | Band (`/progress`, concept and lesson views) |
| --- | --- | --- |
| Not seen yet | `upcoming` and not `lesson_done` | `not_started` |
| Locked until {checkpoint} | `locked` (`locked_by`) | concept view `locked` |
| Read | `upcoming` or `in_progress` with `lesson_done` and not `quiz_done` | — |
| Assumed from placement | `assumed` | `likely_known` |
| Practised with help | `practiced`, or `in_progress` with `quiz_done` or other evidence | `developing` |
| Mastered (lime) | `mastered` | `strong` |
| Review due (lime dotted) | `review_due` (shown as a badge next to the base state) | `next_review` ≤ now |
| Needs practice | — (no roadmap status) | `needs_practice` |

Data the spec mentions that does not exist, so the matching elements are dropped:

- Hint ladder with timed unlocks. `hint_count` exists, but hints are tutor turns with no unlock
  timer.
- An "Independent attempt" mode on problems.
- Cancelling a playground generation. There is no cancel endpoint, and the request is
  idempotent by `request_id`.
- Prerequisite edges within a module on the roadmap. The plan view has no edge list, so the map
  is drawn as "Order in module".
- Per-skill independent evidence counts.
- A projected milestone date per module.
