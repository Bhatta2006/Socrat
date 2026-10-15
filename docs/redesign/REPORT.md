# Socrat redesign report: "Learn it. Then prove it."

This report covers the UI redesign built from the `UI-redefining` spec, on branch `redefined`,
dated 2026-10-15. It covers what changed, how it was verified, what was dropped because the
backend has no data for it, and where the build deviates from the spec and why.

Related documents:
- `docs/redesign/AUDIT.md`: the starting state.
- `docs/redesign/DESIGN-SYSTEM.md`: tokens, components and the status mapping.
- `docs/redesign/before/` and `docs/redesign/after/`: screenshots of 14 pages at 390, 768 and
  1440 px in dark and light. Regenerate them with `node scripts/web/capture-redesign.mjs <dir>`
  while the demo is running.

## What changed

### Foundations
- **Palette:** violet, lilac, cream and ink on matte ink and lilac-tinted surfaces. Coral means
  "needs attention". Lime is reserved for proof states. Emerald, amber, green and sky are
  removed. Gradients, blur, coloured shadows and the dotted grid are gone.
- **Type:** Geist Sans Bold for display, Figtree for body and JetBrains Mono for code.
  Figtree and JetBrains Mono are vendored under OFL. There is a `type-*` scale from 11 px
  labels to the 112 px landing headline.
- **Focus and motion:** one focus ring everywhere (2 px `--ring`, 2 px offset). Motion is
  limited to fades, 8 px rises and a press scale. A new in-app **Reduce motion** setting
  (Settings › Appearance) is applied before first paint.
- **Code editor:** the syntax palette matches the spec in both themes.
- **Generated visuals:** they receive the new token values through the unchanged compiler. The
  lime proof colour is kept out of generated documents, and a test now asserts this.
- **Brand:** a new mark and wordmark (two offset half-discs) appear on every surface and in the
  favicon (`app/icon.svg`). The sparkle mark is gone.

### Components
- The shadcn primitives were restyled in place: pill buttons with 44 px targets, 28 px cards
  in six tones, outlined chips, 52 px inputs, a segmented control, 28 px dialogs on a solid
  scrim, bottom sheets with a drag handle, 56 px table rows and attention-styled alerts.
- New shared components live in `components/socrat/`: the status icon, label and legend, the
  wordmark, illustrations and the Soc tutor drawing, the arrow button, empty, error, locked and
  success states, the skill map, week strip, Practice segmented navigation and the copy-code
  block.
- A development-only gallery at `/dev-gallery` shows every component. It returns 404 in
  production.

### Shell and navigation
- **Six destinations:** Today, Skills, Practice, Playground, Evidence and Settings. Every route
  keeps its path. `lib/routes.ts` is the single source of canonical names.
- **Desktop:** a 248 px sidebar that collapses to a 72 px rail, plus a field-style "Search
  Socrat" button with the platform's shortcut.
- **Tablet:** the rail only.
- **Phone:** a five-item bottom nav. Settings, theme and log out move to the avatar menu.
- **Practice:** Problems, Company questions and Focus sprint are one place with three views,
  joined by a segmented control of real route links.
- **Search:** results use the canonical names. Old names (progress, plan, library, assessments)
  still work as search keywords. Course scoping is unchanged.
- **Tutor:** the Soc launcher is a 56 px round button 16 px above the phone nav. Pages with
  their own "Ask Soc" control show it on phones only, and focus returns to whatever opened the
  tutor.

### Pages
| Page | Main changes |
| --- | --- |
| Landing | Flat geometric hero, "Learn it. Then prove it.". Read, Check and Prove cards introduce the status system. Real component frames are labelled "Sample data". Three path cards, native FAQ, lilac final call to action. The WebGL ribbons, gsap and daisyUI are removed. |
| Log in | Lilac story panel and form panel. "Continue with Google". Development sign-in sits in a dashed "Development only" card. |
| Onboarding | Back button, progress bar and "Step n of 6". A live weekly-time summary. A new review step with Edit links before "Create my plan". Choices survive a reload within the session. |
| Placement | "Submit answer" and "Not sure yet" have equal weight. Skipped topics show as **Assumed from placement**, with a note that they are assumptions, not evidence. |
| Today | One violet hero (the next activity), review-due and Playground cards, the next milestone from the real module counts, assessment state, today's session, practice picks, skills to learn next, course ring, and an Ask Soc card on desktop. |
| Skills | A violet current-module hero, the skill map with a Map/List toggle, expandable modules with status labels and badges, the locked checkpoint state, collapsible schedule, plan reasons and guides, and the legend. |
| Lesson | Violet header, the Read → Check → Practice stepper, a 68-character reading column, "Explain it differently", a Playground card that passes the topic only, "Mark lesson as read" and "Take concept check" with "Reading does not count as mastery", key reminders, pitfalls, and a sticky support column. |
| Quiz and checkpoint | Focus header with a thin bar. Each answer row shows shape, label and colour (Selected, Correct, Incorrect, Correct answer). Results lead with "n of m correct", topics to revisit and links to Skills and Evidence. Checkpoint misses are shown as shapes, not hearts. |
| Problem workspace | Top bar with title and chips. **Run tests** is an outlined violet button with a play icon; **Submit solution** is filled violet with an arrow circle. The action row is sticky on phones. Results read "n of m tests passed", with cream check rows and coral triangle rows. A labelled "Ask Soc" button, a locked state in the statement pane, and reset behind a confirmation. |
| Problems | Violet recommendations hero, Focus sprint card, practice level, search plus skill, difficulty and status filters, "More filters" (a bottom sheet on phones), removable filter chips with "Clear all", a table on desktop and cards on phone, pagination at top and bottom, and distinct empty states. |
| Company questions | Always-visible explainer with unlocked counts only. Master and detail on desktop; list then detail on phone, with the selection in the URL. "Nothing unlocked yet" and "No questions match these filters" are separate states. |
| Focus sprint | Violet "3 problems, 45 minutes" hero. A neutral timer with a "Hide timer" toggle that switches to "5 min left". Screen-reader announcements at 15, 5 and 1 minutes only. Finishing early needs confirmation. History is listed. |
| Weekly assessment | Four states: not ready (locked), available (violet hero), in progress (focus mode with "No tutor or learning help during this assessment" and "Saved {time}"), and completed (score, statuses by topic, "Practice this" and "Explore in Playground", history chart). |
| Evidence | Violet completion hero. Stat cards for skills mastered (the screen's one lime focal element), reviews due, needs practice and problems solved without help. Mastery by module with actions on weak skills. Evidence timeline ("independent" or "with help"). Heatmap captioned "Activity shows time spent. It does not measure mastery.", placed after mastery. Achievement badges are removed. |
| Playground | Compose screen ("Ask about a concept."), with depth as a segmented control and review chips that fill in the topic only. Generating shows the real phases, an elapsed timer and "Stay on this page until it is ready". The result has a request bar, a dominant canvas with an attached dock, and Explanation and Saved panels. Generation errors and preview errors are handled separately. The truthful disclosure line comes with an info popover. |
| Settings | Theme tiles with previews, Reduce motion, profile and schedule with "Saved." and the time, a confirmation before switching course, export progress and result, Account, and a separate Danger zone. |
| Admin | Same tokens, an "Admin" chip, Metrics and Review queue tabs, and attention styling instead of red and green. |
| Error and 404 | Shared states and the `empty` illustration. |

Confetti (`canvas-confetti`), achievement badges, `gsap`, `daisyui` and the ribbon scene are
removed from the code and dependencies.

## Verification

All checks were run locally on Windows against the native demo (`scripts/dev/start-demo.ps1`)
using `PW_CHANNEL=msedge`. The repository's Playwright version expects a Chromium build that
is not downloaded on this machine.

| Check | Result |
| --- | --- |
| `npm run typecheck`, `npm run build` | Pass |
| First-load JS budget (`scripts/web/bundle-report.mjs`) | All routes under 300 KB; largest 236 KB (`/problems/[id]`) |
| e2e, desktop | 20 passed, 1 skipped (pre-existing: a live server config overrides that fixture) |
| e2e, mobile (iPhone 13) | 15 passed; 6 are desktop-only by design |
| Accessibility (axe, WCAG 2.1 A/AA, 14 routes, light and dark) | Pass, 0 serious or critical issues |
| Keyboard walkthrough (focus ring on every stop, one `h1`, no skipped heading levels) | Pass |
| New: no horizontal overflow at 320, 390, 768 and 1440 px on 12 routes | Pass |
| Visual regression (key pages, light and dark, 1400 and 390 px) | Baselines regenerated; 12 of 12 pass |
| `services/api/tests/test_learning_scope.py`, `test_explainer.py` | Pass (19 tests). The browser preflight test needs `SOCRAT_EXPLAINER_BROWSER_CHANNEL=msedge` on this machine for the same Playwright reason. |
| `scripts/explainer/*.test.mjs`, `tests/editor-diagnostics.test.mjs` | Pass (6). The diagnostics test needs Node's `--experimental-strip-types` flag on Node 22.12. |

The new checks found real defects, which were fixed:
- **Contrast:** translucent text on the violet hero, and ink chips on violet sections.
- **Overflow:** horizontal overflow on Today, Problems and Evidence from grid items sizing to
  their content.
- **Keyboard:** a scrollable heatmap that keyboard users could not reach.
- **Search:** a search for "progress" no longer found the renamed page, so old names now work
  as keywords.

Not run in this pass:
- A manual 200% and 400% zoom pass. The 320 px automated check covers reflow at 400% on a
  1280 px screen.
- A forced-colours pass. Status shapes switch to `CanvasText` in forced-colours mode, but this
  has not been checked in a browser.
- A real AI generation in the Playground. The Playground e2e tests use the compiled fixture
  visual. A live generation needs the explainer checker service and provider credentials, which
  the native demo does not start.

## Dropped because the data does not exist

| Spec element | Why it was dropped |
| --- | --- |
| "Shown independently" for the lime state | Mastery also counts assisted successes, at reduced weight. The state is labelled **Mastered**. "Independent" is used only where the backend records it. |
| Hint ladder with timed unlocks, lock icons on hints | Hints are tutor turns with no unlock timer. The tutor's real help-level indicator is kept. |
| "Independent attempt" chip and lime line on problems | The backend has no independent-attempt mode. |
| Cancelling a playground generation | There is no cancel endpoint. The page says to stay on it, because the stream stops if the learner navigates away. |
| Request snippet in saved visual rows | The saved-visual list returns only the title and date. |
| Prerequisite edges on the skill map | The plan view has no edge data. The map is labelled "Order in module". |
| Projected date per module or milestone | Only the course finish date exists. Module progress is shown as real counts. |
| Status icons in command search results | Search metadata has no mastery band, and the backend was not changed. |
| Study dots on past days in the week strip | `/today` gives only `studied_today`. Past days are shown without dots instead of guessed from the streak. |
| "One independent attempt lights this skill" subtitle | One attempt does not produce mastery. The recommender's own reason is shown instead. |

## Deviations from the spec, and why

- **Display font is Geist Sans Bold, not General Sans.** The General Sans licence (ITF FFL v2)
  allows self-hosting but forbids redistributing the files "through a repository". Committing
  them to this GitHub repository would break that. The spec names Geist as the fallback. To
  switch later, add General Sans privately through the build and change `--font-display`.
- **Violet as text uses lilac in dark mode, practised rings use `#9A63F2` in dark, and light
  charts use darker colours.** These keep the spec's contrast rules: 4.5:1 for text and 3:1 for
  UI, as detailed in DESIGN-SYSTEM.md.
- **Hero primary actions are labelled ink pills ("Start lesson") rather than an icon-only round
  arrow.** The spec's own accessibility rules (priority 2) require visible text on primary
  actions. The round `ArrowButton` exists for secondary use.
- **Tablet (768–1023 px) uses the icon rail with no bottom nav.** The spec gives both "<1024:
  bottom nav" and "tablet: icon rail"; I followed the explicit tablet rule.
- **The problem workspace has no third "Ask Soc" tab.** The tutor is a dialog that keeps its
  conversation across pages. A labelled "Ask Soc" button opens it from the action row instead.
- **Review chips filter out the backend's non-weak fallback suggestion.** The overview returns
  "the next topic in your plan" when nothing is weak. The spec limits these chips to real weak
  concepts.
- **Course switching confirms, then opens onboarding.** It still uses the existing flow and
  rules.
- **Generated visuals are given the card colour as their background.** This removes the seam
  between canvas and card. All other token names and values are unchanged, and nothing is added
  to the frame's message channel.

## Behaviour preserved

- Course-scoped search and library; topic-scoped company questions.
- Checkpoint gates and locked previews.
- Evidence-based progress.
- The tutor's help ladder and the "show solution" confirmation.
- Assessment assistance restrictions.
- Drafts saved on the server, plus editor preferences.
- The Playground sandbox and CSP, the exact request payload, failures that keep the request,
  reporting that removes the visual, and saved-visual reopening.
- Development sign-in is still gated by the server, which refuses it outside localhost.

No API contract, learning rule or unlock logic was changed. The only backend file touched is
`services/api/tests/test_explainer.py`, which now asserts the new palette.

## Follow-ups

1. Run a manual zoom (200% and 400%) and forced-colours pass in Chrome and Safari.
2. Generate a real Playground visual in both themes with the checker service from
   `compose.yaml`.
3. Optional backend additions that would unlock dropped elements: prerequisite edges in the plan
   view, mastery bands in search metadata, request text in saved visuals, per-day activity in
   `/today`.
4. The visual baselines are Windows-specific (`__screenshots__/win32`). CI on Linux needs its
   own baselines.
