# Launch backlog

What is left before Socrat can launch as a paid product, and how to build each item to a high standard.

- **Branch:** `redefined`, as of 2026-10-10.
- **Already built:** the v2 learner app, the practice library, Codeforces sync, the tutor's tools, and the shadcn/ui redesign.
- **Readers:** the owner and the engineers (or coding agents) who will pick these items up.

Each item gives:
- **Status:** what exists today.
- **Build:** how to implement it.
- **Done when:** acceptance criteria.
- **Needs:** inputs only the owner can provide.

Priorities:
- **P0** blocks launch.
- **P1** is needed for a paid product.
- **P2** strengthens retention and quality after launch.

## Progress log

- **2026-10-15 — UI redesign, "Learn it. Then prove it.":**
  - Violet, lilac, cream and ink palette with lime reserved for mastery and review due; new brand mark, Geist display, Figtree body, JetBrains Mono code (fonts vendored).
  - Status system (shape, label, colour) mapped to roadmap status and mastery bands; six-item navigation (Today, Skills, Practice, Playground, Evidence, Settings) with a five-item phone nav.
  - Every learner page, landing, login, onboarding (now with a review step), placement and the Playground rebuilt; confetti and achievement badges removed; in-app reduce-motion setting added.
  - New layout overflow e2e test; accessibility, keyboard, visual and explainer suites updated and passing. Details: `docs/redesign/REPORT.md` and `docs/redesign/DESIGN-SYSTEM.md`.
- **2026-10-13 — Content-placement playbook, backend/content first pass:**
  - Owner-approved starter content: 30 packs / 279 atoms, covering the first ten concepts in each track, with 30 concept repairs and syntax support.
  - Added two scaffolded beginner judge problems, taking the original problem count to 85; the broader eight-per-concept inventory target remains open.
  - Added versioned, resumable sessions, prediction-before-reveal grading, independent-work restrictions, evidence-based summaries, content issue reports and learning-quality metrics.
  - Frontend integration belongs to the co-founder and is intentionally untouched. Learner pilots, calibration and traffic-dependent experiments remain open.
  - See [the implementation and UI handoff](content-placement-implementation.md).

- **2026-10-13 — Item 1 (CI readiness), local parity:**
  - Coverage is 89%, with gateway tool-loop tests using fake SDK clients.
  - Next.js is 16.4.0, patching GHSA-4jqv-mc3x-m676 and GHSA-3w37-wq28-93x7.
  - The shadcn CLI is no longer a runtime dependency, and `npm audit --audit-level=high` reports no issues.
  - Still open:
    - CI runs only on pull requests and `main`, so it has never run on this branch. Open a PR to run it.
    - The Postgres migration check needs Docker and has not been run locally.
- **2026-10-13 — Item 3 (locked topics and compounding gates):** done.
  - Module checkpoints are now gates (`planner/gates.py`, `learn/quizzes.py`).
  - Modules unlock in course order; a gate is passed, or a module counts as known through placement or mastery.
  - The adaptive staircase takes up to 10 items and ends after 3 misses.
  - Passing needs a weighted score of at least 0.8 **and** two correct answers at the module's top level.
  - A failed gate gets a 24-hour cooldown and targeted reviews.
  - Server-side `423 concept_locked` stops practice on locked concepts; lessons stay readable as a preview.
  - The UI covers the plan, quiz, lesson and problem pages.
  - Tests: unit and property tests, API flow tests, and an e2e journey.
  - **Content follow-up:** the authored quiz items only reach difficulty 3, and some modules have one or two items at their top level. Add harder items through item 5.

- **2026-10-13 — Item 4 (weekly personalised assessments):** done.
  - A new `assessments` package, migration `0003_weekly`, and the `/assessments` page.
  - The assessment opens once per local ISO week, after at least 2 topics studied in the last 7 days.
  - 12 questions, weighted by exposure × fragility (shaky topics get a fair check, strong topics get their hardest items), plus up to 3 due older topics and 1–2 unsolved Socrat coding tasks.
  - Answers are hidden until submission. Exam mode adds a 30-minute timer, and the server finishes the assessment at the deadline.
  - The tutor pauses during a live attempt.
  - The report shows per-topic results, mastery before and after, strengths, next week's focus, and the change against last week.
  - Includes a tutor tool, account export, a sidebar dot and a Today card.
  - Tests: unit and API tests, and an e2e journey.
  - **Follow-up:** reminders for a ready assessment belong to item 11.

- **2026-10-13 — Item 12 (UI polish), parts 1–6:** done.
  - The editor has an accessible light, dark and high-contrast syntax theme in Geist Mono, plus Ctrl/Cmd+Enter to run and +Shift to submit.
  - The tutor button is icon-only on phones.
  - "Open app" is hidden during onboarding, and Next's dev badge is off.
  - The landing page counts come from a public `/library/stats`.
  - The streak chip uses a light `/me/summary` instead of `/today`.
  - Parts 7–10 remain: an empty-state audit, view transitions, achievements, and visual regression tests.
- **2026-10-13 — Item 17, mostly done:**
  - Tutor tools, recommendations and the assistant context read the plan without recording revisions (`plan_for(record=False)`).
  - The demo's SQLite uses WAL with a 15-second busy timeout.
  - Plan revisions are recorded with a compare-and-swap on the enrollment's plan signature, so racing page loads log one revision. A test reproduces the race.
  - `/library` "Recommended" scores the library once per learner state (an in-process LRU of 64 score maps, keyed by a fingerprint of everything scoring reads, refreshed hourly). Rating windows are computed once per concept, not once per problem. A cache miss dropped from about 65 ms to 33 ms for 13,889 problems; paging and re-filtering reuse the map.
  - Remaining from the table: the monthly Codeforces snapshot job, the licence review of company data (owner), and a nightly `--repeat-each=5` e2e run.

- **2026-10-13 — Item 11 (retention), in-app parts:** done.
  - Earned streak freezes: one per fully met week, at most 2 banked, each covering one missed study day.
  - A no-guilt "welcome back" restart after 3 or more missed study days.
  - Still needs owner input: email and push reminders, and the weekly report email (a sending domain).
- **2026-10-13 — Item 8 (hidden CP trajectory):** done except continuation modules.
  - Focus sprints (`/sprint`, migration `0004_sprints`): 3 judged problems near level+100 from studied, unlocked topics, 45 minutes, with time-to-solve results.
  - An upsolve nudge in recommendations.
  - Upcoming rated rounds, shown only with a linked handle or a level of about 1100+.
  - Background Codeforces re-sync of stale handles, rate-limited and off in tests.
  - None of these labels the long-term goal.

- **2026-10-13 — Item 15 (accessibility), automated part:** done.
  - `tests/e2e/accessibility.spec.ts` runs axe (WCAG 2.1 A/AA) on 15 pages in light and dark mode and fails on any serious or critical issue.
  - Fixes: AA-safe light brand, success and destructive tokens; labelled progress bars; the decorative hero marked hidden from assistive tech; valid list and tab semantics; `role="img"` on the frequency bars; and Motion now honours reduced motion.
  - Remaining: a manual keyboard-only walkthrough and performance budgets.

- **2026-10-13 — Item 7 (personalised reading), mechanism:** done.
  - Lessons show 3 resources picked by the learner's band and language, ranked by Bayesian-smoothed community helpfulness and the learner's own history (opened or unhelpful).
  - The rest sit behind "More resources", with helpful and not-helpful feedback (`resource_events`, migration `0005_feedback`).
  - The weekly `content-link-check` workflow runs `scripts/content/check_links.py`.
  - Remaining: growing the catalogue to 6–10 vetted resources per concept, which needs owner approval of sources.
- **2026-10-13 — Item 9 (tutor quality), UX part:** done.
  - Thumbs up and down on tutor replies (`assistant_messages.rating`), included in the export.
  - Remaining, which spends money and needs owner approval: the eval suite, cost metering and a live Anthropic run.

- **2026-10-13 — Items 14 and 16 (owner analytics and content QA), first version:** done.
  - `/admin` is gated by `SOCRAT_ADMIN_SUBJECTS`.
  - It shows the activation funnel, the activation rate (lesson plus check within 24 hours), D1/D7/D30 retention, weekly engagement and tutor ratings.
  - It also shows checkpoint pass rates, flagged quiz items (at least 20 answers with ≥95% or ≤10% correct), and resources learners found unhelpful.
  - All of it is computed from learning tables, with no third-party tracker.
  - Remaining: a drafted-content review queue (with item 5) and dashboards over time.

- **2026-10-13 — Item 12 part 9 (achievements):** done.
  - The Progress page shows 13 badges for real skill milestones:
    - first lesson; first solve; a hard problem solved;
    - 10, 50 and 100 problems solved; 10 solved without hints;
    - first checkpoint passed; every checkpoint in the course passed;
    - a weekly check finished; a clean focus sprint;
    - 7-day and 30-day streaks.
  - Badges are derived from learning data (`learn/achievements.py`); nothing new is stored.
  - Unearned badges show progress toward the goal, and the closest ones are listed first.
  - Newly earned badges are marked "New" with a small confetti burst. "Seen" state is kept per browser.
  - No leaderboards.

- **2026-10-14 — Item 17, scheduled jobs:** done.
  - `practice-refresh.yml` runs on the 2nd of each month. It re-imports the public practice index and writes a diff report with `scripts/content/practice_diff.py` (added, removed and changed problems by field). When anything changed, it opens a review PR with the report as its body. PRs opened with the workflow token do not trigger CI by themselves, so re-run the checks or push to the branch before merging.
  - `e2e-nightly.yml` repeats the learner journeys five times nightly with retries off, and uploads traces on failure.

- **2026-10-14 — Item 15, JavaScript budget:** done.
  - `scripts/web/bundle-report.mjs` reports first-load JS per route (gzip) from the Turbopack manifests, which `next build` no longer prints. CI fails a route over 250 KB.
  - Shared JS per route fell from about 271 KB to 216–237 KB:
    - `Reveal`, `Ring` and `NumberTicker` now use CSS and `requestAnimationFrame` instead of Motion.
    - Motion loads only on the landing page, through `LazyMotion` with the `m` component.
    - The lesson's reading bar is a scroll listener.
    - The ⌘K dialog (cmdk) loads on first use, prefetched on hover or focus.
    - CodeMirror and confetti were already lazy.
  - What is left of the shared bundle is mostly React DOM (~70 KB) and the Next runtime (~45 KB).
  - Remaining: LCP and INP measured on a throttled mid-range phone profile (Lighthouse CI against a deployed build), and the keyboard walkthrough.

- **2026-10-14 — Item 15 keyboard walkthrough and item 17 heading review:** done.
  - `tests/e2e/keyboard.spec.ts` completes sign-in, onboarding, a lesson, its check, the tutor, ⌘K search and navigation with Tab, Enter, Space and Escape only, and asserts a visible focus ring at every stop.
  - It found that the tutor panel did not take focus. The panel now focuses its message box on open, closes on Escape, and returns focus to its launcher.
  - The same spec checks that 11 pages have exactly one h1 and no skipped heading levels. Top-level card titles on Library, Plan, Progress, Settings and Achievements are now h2.

- **2026-10-14 — Item 12, parts 7 and 8 (loading, empty states, transitions):** done.
  - **Loading states:** `Loading` has page-shaped variants (article, workspace, list, quiz, form and blank), so each skeleton matches its page and content lands without layout shift. The landing and login pages show a blank placeholder rather than a dashboard skeleton that would flash before the redirect.
  - **Empty states:** the audit found them already covered, including Today's done and rest-day card, the Library and Companies no-match states, Recent results, and the Assessment and Sprint first-run cards.
  - **Route transitions:** React `<ViewTransition>` in the shell crossfades the content area on navigation; the header is anchored. Links that go deeper (plan and progress concepts, Today's next activity) slide forward, and back-links slide back. Animation durations are zero under reduced motion.
  - **Unlock animation:** a module that unlocked since the learner last opened the Plan page glows twice and shows an "Unlocked" badge, with a small confetti burst.
  - **Fix:** canvas-confetti's default instance draws in a `blob:` worker, which the CSP blocks, so celebrations never rendered. It now uses a main-thread instance.

- **2026-10-14 — Item 12 part 10 (visual regression):** done.
  - `npm run test:visual` (`playwright.visual.config.ts`, `tests/visual`) screenshots the landing, login, Today, Plan, Progress, lesson and problem pages in light and dark at 1400 px and 390 px, with a 1% pixel tolerance.
  - Content that changes on its own is handled: dates, greetings and weekday rows are masked, and the daily-rotating recommendations get fixed titles so page heights stay the same. Baselines were stable over three consecutive runs.
  - Baselines are per platform. Windows baselines are committed. `visual.yml` creates the Linux baselines on a manual run with `update` ticked and commits them; nightly runs then compare and upload diffs on failure.

- **2026-10-14 — Item 5 step 7 (editor parity):** done.
  - The editor toolbar has a settings popover (font size 12–20 px, indent of 2 or 4 spaces) and "Reset to starter" with a confirmation. The reset saves at once, so a quick reload cannot bring the old code back.
  - The statement and editor panes have a resizable split: drag, or use the arrow keys on the focusable divider.
  - Preferences persist per browser (`lib/editor-prefs.ts`). Ctrl+Enter and Ctrl+Shift+Enter were already bound.
  - `tests/e2e/editor.spec.ts` covers all of it.

- **2026-10-14 — Items 5 and 16 (problem pipeline and review queue):** done, apart from the work that needs your budget and reviewers.
  - **Quality gates** (`socrat/catalog/validate.py`, `scripts/content/validate_problems.py`):
    - schema, and examples reproduced by the reference;
    - the reference agrees with a brute force on ~300 small inputs, all run in one subprocess;
    - the reference runs on the largest test in under half the time limit;
    - C++/Java references compile and agree, when present and a toolchain exists;
    - originality: library-title similarity and near-duplicate Socrat statements;
    - difficulty versus the concept tier and the size bounds.
    - Drafts run strict: a brute force is required, and duplicated statements fail.
  - **Current content:** all 83 authored problems pass, with warnings. None has a brute force yet, and there are a few notes on titles, timing and difficulty. 61 of 61 concepts still have fewer than 8 problems.
  - **Schema:** `Problem` gains optional `brute`, `small_generator`, `references` (cpp/java) and `review` (by, at, notes).
  - **Drafting** (`scripts/content/draft_problem.py`):
    - Claude drafts the problem as structured output from the concept brief and a human idea seed;
    - the gates run, and failures go back to the model as feedback (up to 3 attempts);
    - an independent call then solves it from the statement alone and must match the reference, which catches ambiguous statements;
    - the draft is filed in `content/drafts/<course>/`.
    - `--dry-run` prints the brief. Tests use a scripted model, so they make no API calls.
  - **Review queue** (`/admin` → Review queue, `admin/drafts.py`):
    - run the gates and read the statement, hints, approach and both solutions, plus the drafting record;
    - approve (blocked while gates fail or the file changed since validation) or request changes, with notes;
    - approval writes the `review:` block, moves the file into the course and links it from its concept. Then build and commit.
    - Every decision is an audit event.
  - **Remaining (needs you):** an AI budget to draft about 400 problems, reviewer time, brute forces for the 83 existing problems, and C++/Java references.

- **2026-10-14 — Item 15, page-speed measurement:** measurement done; the budget is not met yet.
  - **Real-user metrics:** `components/web-vitals.tsx` sends anonymous LCP, INP, CLS, FCP and TTFB samples by `sendBeacon` to `POST /api/v1/vitals`. Each sample carries a route pattern, value and device class only, with no user, session or URL. The endpoint accepts same-origin requests only, bounds values and caps batches (migration `0006_web_vitals`). `/admin` → Page speed shows the 7-day p75 per page against the budgets.
  - **Lab check:** `lighthouse.yml` and `lighthouserc.json` run Lighthouse on the production build with mobile simulated throttling. The assertions *warn* for now; switch them to `error` once LCP is fixed.
  - **Fixes:**
    - The landing and login pages now render their content into the first HTML instead of waiting for the session check.
    - A Next proxy (`src/proxy.ts`) redirects signed-in visitors from `/` to `/today` on the server.
    - The login form's sign-in options are fetched on the server.
    - The hero copy no longer fades in.
  - **Local Lighthouse, mobile:**

    | Page | LCP | TBT | CLS | FCP |
    |---|---|---|---|---|
    | Landing | 4.4 s | 170–400 ms | 0.046 | 1.1 s |
    | Login | 3.9 s | 90–150 ms | 0.046 | 1.1 s |

    Before the fixes, the landing page was at LCP 4.9 s and TBT 580 ms.
  - **Still open:** LCP render delay of about 3 s after first paint on both pages. The LCP element is server-rendered text, so the next suspects are:
    - font swap (Geist via `next/font`; try `display: optional` or preloading);
    - the shared 216–242 KB client bundle blocking the main thread before the text is considered painted;
    - the CSS `reveal` animation on page sections.
    Profile with a Lighthouse trace and fix before launch. The numbers come from this laptop; CI runners will differ.
- **2026-10-14 — Security fix:** the review-queue POST routes did not check the CSRF token (`require_admin` now takes `write=True`), with a regression test. An audit of every other write route found no other gaps.

## Status at handoff (2026-10-14)

**Done on `redefined`:**
- Items 3, 4, 8, 12 and 14.
- Item 5: quality gates, the drafting pipeline and editor parity.
- Item 16: the review queue.
- Item 17, except the licence review.
- Item 15: automated axe audit, keyboard walkthrough, JS budget, and field and lab measurement.
- Items 1, 7 and 11 in part.
- Item 2: the Google OIDC sign-in flow and the "Continue with Google" button already exist; they need credentials (below).

**Pending, no owner input needed:**
- Item 15: LCP is still about 3.9–4.4 s on mobile against a 2.5 s budget (see the 2026-10-14 log entry).
- Item 5: brute forces and C++/Java references for the 83 authored problems.

**Pending, needs owner input:**
- **Google sign-in (item 2):** set `SOCRAT_OIDC_ISSUER=https://accounts.google.com`, `SOCRAT_OIDC_CLIENT_ID` and `SOCRAT_OIDC_CLIENT_SECRET`, plus the redirect URL, a verified domain, and privacy and terms URLs.
- **Problem drafting (item 5):** `SOCRAT_ANTHROPIC_API_KEY`, a budget for about 400 problems, and reviewer time (about 10 minutes per problem).
- **Payments (item 10):** provider and pricing.
- **Email reminders (item 11):** sending domain and DNS.
- **Tutor evals and cost limits (item 9):** budget and model choice.
- **Production deployment (item 13):** hosting account, domain and DNS.
- **Resource catalogue growth (item 7):** the owner's resource pool.
- **Licence review of the company data (item 17).**

**Known caveats:**
- 9 C++ tests fail on the local MinGW 6.3 compiler; this is an environment issue.
- CI has not run on `redefined`, because it only runs on PRs and `main`. Open a PR to run it.
- `visual.yml` needs one manual run with `update` ticked to create the Linux baselines.
- The Postgres migration check was not run locally (no Docker).
- In the final local run, the accessibility spec failed once right after a rebuild and passed on rerun; a cold-compile timing issue is the likely cause.

## Summary

| # | Item | Priority | Owner input needed |
|---|------|----------|--------------------|
| 1 | Make CI green on `redefined` | P0 | — |
| 2 | Google sign-in and sign-up | P0 | Google OAuth client, consent screen |
| 3 | Locked topics with a compounding gate quiz | P0 | Gate pass bar (default 80%) |
| 4 | Weekly personalised assessments | P0 | Weekly reset day and timezone policy |
| 5 | Original judge problems at scale | P0 | Review capacity; target count per concept |
| 6 | Integrate the owner's resource pool | P1 | Confirm the branch snapshot is current |
| 7 | Curated, personalised reading | P1 | Approval of sources and licences |
| 8 | Hidden CP trajectory beyond recommendations | P1 | — |
| 9 | Tutor quality: evals, cost controls, memory | P1 | Monthly LLM budget; model choice |
| 10 | Payments and plans | P1 | Pricing, Stripe account, tax region |
| 11 | Retention loops: reminders, weekly report, streak protection | P1 | Email domain / push provider |
| 12 | UI polish backlog | P1 | — |
| 13 | Production hardening and deployment | P0 | Hosting account, domain |
| 14 | Analytics and activation metrics | P1 | Analytics vendor (or self-hosted) |
| 15 | Accessibility and performance audit | P1 | — |
| 16 | Content and admin tooling | P2 | Who reviews content |
| 17 | Technical debt and known issues | P1 | — |

**Suggested order:** 1 → 13 (staging) → 2 → 3 → 4 → 5 (in parallel, content work) → 10 → 11 → 9 → 6/7 → 8 → 12/15 → 14 → 16.

---

## 1. Make CI green on `redefined` (P0)

**Status:** CI (`.github/workflows/ci.yml`) runs the following:
- ruff, mypy, and pytest with an 85% coverage floor;
- Alembic on PostgreSQL;
- a web typecheck and build, and Docker builds;
- e2e on Chromium;
- `pip-audit` and `npm audit --audit-level=high`.

Locally, ruff, mypy, the web typecheck and the build pass. The only pytest failures are 9 C++ tests, caused by the local MinGW g++ 6.3, which cannot compile C++20. CI status for the latest push has not been checked; the `gh` CLI is not installed on the dev machine.

**Build:**
1. Check GitHub Actions for the two newest commits and fix every red step.
2. Run `uv run alembic upgrade head` against PostgreSQL. Migration `0002_practice` was only tested on SQLite. Check that its JSON and Boolean columns behave correctly on Postgres.
3. Check coverage: the new modules (`library/*`, `assistant/tools.py`, `assistant/gateway.py`) must keep the total ≥85%.
   - `gateway.py`'s provider classes are not exercised by tests yet.
   - Add unit tests with fake SDK clients for the Anthropic and OpenAI tool loops, covering these cases:
     - a tool call;
     - invalid JSON arguments;
     - `max_rounds` reached;
     - a refusal;
     - an empty reply followed by the retry.
4. Run `npm audit --audit-level=high` after the shadcn, motion, canvas-confetti, geist and next-themes additions.
5. E2E in CI has no LLM key, so the tutor runs offline. Make sure `PW_*` defaults match `playwright.config.ts`. The 180-second tutor timeout is harmless offline.

**Done when:** every CI job on `redefined` is green and the coverage report is ≥85%.

---

## 2. Google sign-in and sign-up (P0)

**Status:**
- The backend has generic OIDC through Authlib: `/api/v1/auth/login`, `/callback` and `/logout` in `main.py`, configured by `SOCRAT_OIDC_ISSUER`, `SOCRAT_OIDC_CLIENT_ID` and `SOCRAT_OIDC_CLIENT_SECRET[_FILE]`.
- The login page shows "Continue with Google" whenever `features.oidc_login` is true.
- Users are keyed by `(issuer, subject)`.

**Build:**
1. **Google Cloud setup.** Create an OAuth 2.0 Web client and a consent screen with the scopes `openid`, `email` and `profile`.
   - Redirect URIs: `https://<domain>/api/v1/auth/callback`, plus `http://localhost:3000/api/v1/auth/callback` for development.
   - Issuer: `https://accounts.google.com`.
2. **Identity checks.**
   - Require `email_verified` to be true.
   - Store `email` (new nullable column, unique per issuer) and `display_name` from `given_name`.
   - Never trust email alone as identity; keep `(iss, sub)` as the key.
3. **Sign-up versus sign-in.**
   - On first callback, create the user and send them to `/start`. Returning users go to `destination()`.
   - Pre-fill the onboarding name from Google so the first step is a single field.
4. **Security.**
   - Keep the `state` and nonce checks Authlib provides, and use PKCE.
   - Rotate the session on login; `establish_session` already does this.
   - Set `SameSite=Lax` on the cookie.
   - Add `accounts.google.com` to `form-action` and `connect-src` in the CSP only if needed. The redirect is a top-level navigation, so it usually isn't.
5. **Account deletion.** Export already covers user data. Deleting the user must also revoke the Google grant: call `https://oauth2.googleapis.com/revoke` with the stored refresh token if one exists. Otherwise, document that it isn't needed.
6. **Production.** Disable `dev_login`; `config.py` already enforces this outside development. In staging, put Google sign-in behind a domain allow-list until launch.
7. **UI.** The login card already renders the Google button. Add an error state when the callback fails, for example when the user cancels consent. Use `?error=` on `/login` and map it to a friendly message.

**Done when:** a new Google user reaches Today in at most three screens; a returning user lands where they left off; the e2e test uses a mocked OIDC provider (Authlib can point at a local stub issuer); CSRF and session tests still pass.

**Needs:** a Google OAuth client ID and secret for staging and production, a verified domain, and privacy-policy and terms URLs for the consent screen.

---

## 3. Locked topics with a compounding gate quiz (P0)

**Goal (owner requirement #4):** later topics stay locked until the learner passes a gate. The gate's difficulty compounds with each correct answer, so learners feel the depth and study properly before moving on.

**Status:**
- The planner (`planner/engine.py`) orders concepts by prerequisites but never locks anything.
- Quizzes are fixed-length (`learn/quizzes.py`).
- Options are already shuffled per session.

**Build:**
1. **Locking model.** A concept is locked until every prerequisite in its own course is `mastered`, or `assumed` and confirmed by a passed gate.
   - Compute this in a pure function `locks(catalog, states, gates) -> dict[concept, LockReason]` next to `build_plan`.
   - Expose a `locked` flag and reason in the `/plan`, `/today`, `/progress` and `/concepts/{id}` views.
   - Lessons on locked concepts stay readable as a preview. Quizzes and problems return `423 concept_locked`.
2. **Gate session.** Add a new activity kind, `gate:<module>`, and a new table `gate_attempts`.
   - Columns: `id`, `enrollment_id`, `module`, `started_at`, `finished_at`, `items` JSON, `answers` JSON, `difficulty_path` JSON, `passed`, `score`.
3. **Compounding difficulty.** This is an adaptive staircase:
   - Start at difficulty 2.
   - Each correct answer raises the next item's difficulty by one, up to 5. Each wrong answer lowers it by one and counts a strike.
   - Draw items from every concept in the module, never repeating an item the learner has seen in the last 14 days.
   - The gate ends after 10 items or 3 strikes.
   - Pass when the score is at least 0.8 **and** at least two correct answers were at difficulty 4 or above.
   - Grade on difficulty-weighted accuracy, `Σ(correct·d) / Σ(d)`, so easy-only streaks cannot pass.
4. **Item supply.** Gates need roughly 3× more quiz items per concept than exist now. Each concept needs at least 4 items at difficulty ≥4. Run the content pipeline from item 5 for quiz items as well, and add a content-build check that fails when a gated module lacks enough items.
5. **Retry policy.**
   - A failed gate produces a personalised remedial plan: the weakest concepts by item, using `weakest_prerequisite`.
   - A retry needs either a 24-hour cooldown or finishing the remedial activities.
   - Show the cooldown with a clear reason, not a punishment.
6. **Psychology and UI.**
   - Show the gate as a "checkpoint unlock": a lock icon on the roadmap, a progress meter of concepts mastered toward the gate, and copy that builds desire ("3 of 5 concepts ready").
   - During the gate, show a rising difficulty meter. The learner should feel the stakes and the climb.
   - Celebrate a pass (confetti, an unlocked-module animation, and the plan updating live).
   - On a fail, show what was strong, what to review, and when they can retry. Never show raw percentages alone.
7. **Planner.** Insert `gate:<module>` once the module is ready. Locked concepts render as greyed roadmap items. The projected finish must include the gates.
8. **Anti-gaming.** Do not reveal answers during a gate; reveal them at the end like checkpoints. Use per-session option shuffling, as already built.

**Done when:**
- Property tests show that the staircase never exceeds 10 items and that a pass needs at least two correct answers at difficulty ≥4.
- An e2e test locks, then fails the gate, then completes the remedial, then passes, then unlocks.
- The plan changes are explained in `PlanRevision.reasons`.

**Needs:** confirm the pass bar (default 0.8 plus two hard correct answers) and the cooldown (default 24 hours).

---

## 4. Weekly personalised assessments (P0)

**Goal (requirement #8):** every week, a test on the concepts this learner studied that week. Personalised, never the same for everyone.

**Status:**
- Evidence rows record what was studied and when.
- The `week` summary exists in `/progress`.
- There is no assessment entity.

**Build:**
1. **Selection.** On the learner's local week boundary (default Monday 00:00 in their timezone), compute the week's concepts from `Evidence` and `ActivityRecord`.
   - Weight them by the learner's exposure and their current fragility, using low `effective()` mastery and `due()` reviews.
   - Add about 20% interleaving from older concepts that are due for spaced review.
2. **Composition.**
   - 12–15 items: about 60% multiple choice at matched difficulty, about 25% harder "transfer" items, and 1–2 short coding tasks from the judge.
   - Pick coding tasks from unsolved Socrat problems on the week's concepts.
   - Seed with `(enrollment, iso_week)` so the assessment is reproducible.
   - Store it as `weekly_assessments(id, enrollment_id, iso_week, items, answers, started_at, finished_at, score, report)`.
3. **Timing.**
   - Available from the week boundary for 7 days, with an untimed default and an optional "exam mode" timer of 30 minutes.
   - The timer keeps the CP habit in view without saying so.
4. **Report.**
   - Per-concept results, mastery deltas, and "what to focus on next week". Feed the report into the planner's reasons.
   - The tutor gets a `get_weekly_report` tool.
5. **Evidence.** Use the `checkpoint` weight (1.6) for multiple choice and `code` for coding tasks. Assistance is disabled during assessments, so the tutor must be blocked: the assistant scope `assessment:*` returns a polite refusal.
6. **UI.**
   - An "Assessments" nav item with a badge when one is due.
   - Today gets a card on the boundary day.
   - The results page uses the quiz results design plus a per-concept chart and a week-over-week trend.
   - A history list shows past weeks.
7. **Notifications.** Add a "your weekly assessment is ready" reminder; see item 11.

**Done when:**
- Two learners with different weeks get different item sets; the same learner gets the same set on reload.
- The report numbers match the evidence.
- The tutor is blocked during the assessment.
- An e2e test passes, using a seeded week.

**Needs:** the week-start convention (Monday is assumed) and whether the timer is optional or mandatory.

---

## 5. Original judge problems at scale (P0)

**Goal (requirement #3):** many more problems in the in-app judge. LeetCode, CSES and Codeforces statements are copyrighted, so judge problems must be original.

**Status:**
- 83 authored problems with reference solutions.
- Tests are generated into `.cache/content-tests` by `scripts/content/build.py`.
- The editor is CodeMirror 6 with Run, Submit, custom input and diagnostics.
- The C++ runner needs C++20 (MSYS2 g++ on Windows).

**Build:**
1. **Target.** At least 8 judge problems per concept (61 concepts, about 490 problems), spread across easy, medium and hard, with hard problems rated near the concept's ladder tier (`library/ladder.py`).
2. **Drafting pipeline** (`scripts/content/draft_problem.py`):
   - Input: a concept, a target difficulty, and a short "idea" seed written by a human or taken from a pattern taxonomy.
     - Never paste an external statement.
   - The LLM drafts:
     - a statement, input/output formats and constraints;
     - examples and hints (levels 1–4);
     - the approach;
     - a Python reference solution;
     - a **brute-force** solution;
     - a test generator.
   - Use Claude with structured output against the YAML schema in `catalog/schema.py`.
3. **Validation gates** (automatic, all must pass):
   - Schema validation, and the reference agrees with the brute force on 500 random small cases.
   - The reference fits the time limit on maximum-size tests in all three languages, which needs C++ and Java references or verified translations.
   - The examples match the reference output.
   - The statement is unambiguous: a second LLM pass solves it from the statement alone and must match on samples.
   - A similarity check against the library titles and a statement-embedding near-duplicate check, to avoid copying.
   - A difficulty estimate from solve-path length and constraint size, checked against the concept tier.
4. **Human review.** Add a review queue (see item 16). Nothing ships without one human approval. Record the reviewer and date in YAML metadata.
5. **Judge quality.**
   - Special checkers for floating-point and multiple-answer outputs.
   - Per-language time multipliers.
   - Memory limits enforced in the runner.
   - Hidden-test categories: edge, max and anti-hash.
6. **Toolchains.** Document and script MSYS2 GCC ≥13 for Windows development (`scripts/dev/doctor.ps1` already prints commands). In CI and production, pin the gVisor images.
7. **Editor parity.**
   - Add a "Reset to starter" button, keyboard shortcuts (Ctrl+Enter runs, Ctrl+Shift+Enter submits) and a resizable split pane.
   - Fix the low-contrast dark-theme syntax colours (see item 12).
   - Persist font size and tab size.

**Done when:** the content build reports 8 or more validated problems per concept, every problem passes all gates, the e2e suite solves one problem per language in CI, and the review records are present.

**Needs:** reviewer time (about 10 minutes per problem) and approval of the difficulty distribution.

---

## 6. Integrate the owner's resource pool (P1)

**Status:**
- Branch `origin/codex/m2-skill-pack-kernel` contains `contracts/resource-pool/*`:
  - 5,779 records and 429 companies;
  - a taxonomy, a difficulty matrix and `dsa_resource_pool.py`.
- The current library imports company lists from the public snehasishroy repo instead.

**Build:**
1. Diff the pool against `content/practice/problems.jsonl`, keying on normalised URLs (`catalog/practice.normal_url`). Record overlaps and new items.
2. Map the pool's taxonomy to Socrat concepts in a reviewed table (`content/practice/pool_concepts.yaml`). Never map by fuzzy string alone.
3. Merge into `scripts/content/import_practice.py` as a fourth source:
   - Keep metadata and links only.
   - Keep per-source provenance in `sources.json`.
   - Prefer the pool's company frequency where it is newer.
4. Licences: many pool sources have no licence. Store only facts (titles, URLs, difficulty) and our own summaries, and never copy text.

**Done when:** the import is reproducible, provenance is recorded per record, and there are no concept-mapping gaps for pool items.

**Needs:** confirmation that the branch snapshot is the latest, and any additional files.

---

## 7. Curated, personalised reading (P1)

**Goal (requirements #2 and #10):** more resources per course, curated from the best public books and articles, and each learner sees only what they need.

**Status:**
- Each concept has 2–4 `resources` (title, URL, kind, minutes, level, languages).
- CP Handbook chapter links come from `content/practice/book.json`; the owner asked that the handbook not be paraphrased.
- TheAlgorithms implementation links exist.

**Build:**
1. **Expand the catalogue** to 6–10 resources per concept, mixing kinds (article, video, interactive, book chapter), levels (intro, core, deep) and languages.
   - Sources to evaluate: CP-Algorithms (CC BY-SA), the USACO Guide (check its licence; link only), MIT OCW, the official Python, C++ and Java documentation, and VisuAlgo for visualisers.
   - Store links and our own one-line summaries only.
2. **A personalisation rule** in `learn/views.concept_view`. Show at most 3 resources, chosen by:
   - the learner's band (intro for not started and needs practice, core for developing, deep for likely known and strong);
   - their language;
   - the format they engage with most (track opens, with a `resource_events` table);
   - not already opened.

   Put the rest behind "More resources".
3. **Feedback.** Add "Was this helpful?" (thumbs) per resource. Use it to demote unhelpful links, with Bayesian smoothing to stay robust to small samples.
4. **Link health.** Run a weekly CI job that HEAD-checks every URL and opens an issue for 4xx and 5xx responses.

**Done when:** every concept has ≥6 vetted resources; the concept view shows ≤3 picks that change with band and language; a link-check job exists.

---

## 8. Hidden CP trajectory beyond recommendations (P1)

**Goal (requirement #7):** every course quietly moves learners toward strong competitive-programmer level. **Never state this in the UI.**

**Status:**
- `library/ladder.py` estimates a rating from mastery and an optional Codeforces rating.
- `library/recommend.py` leans toward rated problems as the level rises.
- The tutor prompt shapes suggestions and stays honest if asked.

**Build:**
1. **Continuation plans.** When a course is at least 80% complete, offer "Keep growing" modules taken from the next ladder tiers outside the course, framed by the learner's goal ("Ace harder interview rounds" for DSA learners). The planner adds them as bridge modules, with the same mechanics as prerequisite bridges.
2. **Timed practice.** Add a "Focus sprint" mode: 3 problems in 45 minutes, matched to the level, scored on speed and accuracy.
   - Store it as an activity kind `sprint:<id>`.
   - It builds contest habits without naming them.
3. **Upsolve list.** Problems a learner opened or failed go into "Unfinished". Recommend revisiting them after 2 days.
4. **Codeforces calendar** (for opted-in learners only): show upcoming Div. 3 and Div. 4 rounds via `contest.list`. Only surface this after the learner has linked a handle or reached about 1200.
5. **Background sync.** Re-sync Codeforces handles nightly with a job queue (the outbox and worker pattern already exists). Respect one request per two seconds globally.

**Done when:** these features exist without any UI copy mentioning "competitive programming" outside the CP course; a test asserts that the term is absent from DSA and Zero course screens.

---

## 9. Tutor quality: evals, cost controls, memory (P1)

**Status:**
- The tutor has tool use (9 tools) and a rewritten system prompt (`assistant/prompts.py`).
- Its Socratic ladder and leak guard are enforced by the server.
- It has been tested live on Nebius Nemotron.
- The Anthropic tool path has not been tested live.

**Build:**
1. **Eval suite** (`services/api/evals/`). It costs money to run, so get the owner's approval first.
   - About 150 scripted conversations: concept questions, plan questions, "give me the code" pressure, prompt-injection attempts in code comments, off-topic requests, and wrong-tool traps.
   - Graders:
     - deterministic: leak guard, link validity (only `/learn`, `/problems` and library URLs), no bare URLs, and level-tag compliance;
     - an LLM judge: Socratic quality, accuracy, tone and personalisation use.
   - Track scores per model and prompt version in a JSON report. Gate prompt changes on no regression.
2. **Cost controls.**
   - Per-user daily token budgets on top of the message quota.
   - Log the prompt-cache hit rate (Anthropic `usage.cache_read_input_tokens`).
   - Cap tool rounds; `ai_tool_rounds` is already set to 4.
   - Use a cheaper model for lesson variants.
   - Cache lesson variants per `(concept, language, style)`, which already exists.
3. **Conversation memory.** Summarise long threads into a rolling learner note, stored on `AssistantThread`, so context stays small. Add a `get_learner_notes` tool.
4. **Safety.** A moderation pass for self-harm and abuse with a safe response, and a per-IP rate limit on `/assistant/messages`.
5. **Anthropic path.** Run the eval suite on `claude-opus-5-5` (`SOCRAT_AI_PROVIDER=anthropic`) to verify streaming tool use, server-side fallbacks and refusal handling.
6. **UX.** Add feedback (thumbs) on replies, a "Regenerate" button, copy buttons on code (only at level 5), and an inline context chip ("Using your plan and progress").

**Done when:** eval reports exist for both providers; leak rate is 0 on the pressure set; tool-call accuracy is ≥90%; median latency is <8 seconds with tools; daily cost per active user is measured and documented.

**Needs:** the monthly LLM budget, and the choice of production model and provider.

---

## 10. Payments and plans (P1)

**Status:** none. The product is meant to be paid.

**Build:**
1. **Plans.**
   - Free: Zero course, limited tutor messages, limited library.
   - Pro, monthly or yearly: all courses, gates, weekly assessments, the full tutor and the full library.
   - Offer a 7-day trial without a card if conversion data supports it.
2. **Stripe.**
   - Use Checkout and the Customer Portal.
   - Handle webhooks for `checkout.session.completed`, `customer.subscription.updated` and `deleted`, and `invoice.payment_failed`. Verify signatures and make every handler idempotent through the outbox table.
   - Add a `subscriptions` table (`user_id`, `stripe_customer`, `status`, `plan`, `current_period_end`).
3. **Entitlements.** A single `entitlements(user)` function used by routes (for example, `403 upgrade_required` with the reason) and by the UI. Never trust the client.
4. **Paywall UX.**
   - Show value before the paywall: after the first lesson plus quiz, or when a learner hits a Pro feature.
   - The pricing page uses anchoring (yearly shown as a per-month price), a feature comparison, an FAQ, and a guarantee if offered.
   - No dark patterns: cancellation is easy, through the portal.
5. **Tax and compliance.** Use Stripe Tax for the owner's region. Update the privacy policy and terms.

**Done when:** test-mode e2e covers upgrade → access → cancel → downgrade; webhook replay is idempotent; entitlements are tested at the route level.

**Needs:** pricing, the Stripe account, tax registration details and legal pages.

---

## 11. Retention loops: reminders, weekly report, streak protection (P1)

**Status:**
- Streaks, daily goals and celebrations exist in the UI.
- Archived M10 work had in-app reminders; v2 has none.

**Build:**
1. **Email** (Postmark or Resend) and optional web push (a VAPID service worker).
   - Send a reminder at the learner's chosen time on study days when they haven't studied by then.
   - Send the reminder only when the streak is at stake, with a one-click link to the next activity.
   - Respect quiet hours.
   - One-click unsubscribe, with preferences in Settings.
2. **Weekly report email:** minutes, concepts mastered, the weekly assessment result, and next week's focus. Make it beautiful and short.
3. **Streak protection.** Grant one "streak freeze" per week, earned by meeting the weekly goal. This uses loss aversion without punishing life events.
4. **Comeback flow.** After 3 or more missed days, Today shows a gentle "Welcome back" with a 10-minute restart plan instead of a backlog.
5. **Measurement.** Track D1, D7 and D30 retention and reminder click-through (item 14).

**Done when:** reminders respect timezone, quiet hours and opt-out (tested); emails pass spam checks (SPF, DKIM, DMARC); freeze logic has unit tests.

**Needs:** the sending domain and DNS access.

---

## 12. UI polish backlog (P1)

Known issues after the shadcn redesign (commit `e71a3ab`):

1. **Code editor dark theme:** keyword colours (blue and purple) have low contrast. Define a theme in `components/code-editor` from the design tokens (`--code-bg` and `--code-fg`, plus syntax colours at WCAG AA).
2. **Floating tutor button:** can cover content on small phones and overlaps list rows. Reserve bottom padding on pages that show it, and collapse it to an icon on scroll down.
3. **Onboarding header:** shows "Open app" while the learner is mid-onboarding. Hide it on `/start` and `/placement`.
4. **Dev badge:** Next's development indicator overlaps the sidebar tip. Set `devIndicators: false` in `next.config.ts`, or move it.
5. **Landing page:** the library size (13,889) is hard-coded. Serve it from a public `/api/v1/stats` endpoint.
6. **Momentum chip:** fetches `/today` on every navigation. Add a light `/api/v1/me/summary` (streak, minutes, level) with short client caching (SWR-style revalidate on focus).
7. **Empty and loading states:** audit every page for skeletons, and add illustrated empty states (an `Empty` with an icon is already used in some places).
8. **Micro-interactions:** add View Transitions between list and detail; animate roadmap unlocks.
9. **Gamification layer** (careful, evidence-based): achievements for real skill milestones (first hard problem, a 7-day streak, the first gate) shown on Progress. No leaderboards until moderation exists.
10. **Visual regression:** Playwright screenshot tests for key pages in light and dark at 1400 px and 390 px, with a tolerance threshold.

**Done when:** each item is fixed, with screenshot tests for pages 1–8.

---

## 13. Production hardening and deployment (P0)

**Status:**
- Staging infrastructure exists for OCI (`infra/oci`) with Compose, Prometheus and TLS proxy configs validated in CI.
- Production execution requires gVisor workers.
- The demo uses SQLite and the insecure local runner.

**Build:**
1. Deploy `redefined` to staging, using PostgreSQL with `alembic upgrade head` and the gVisor execution host.
2. **CSP:** check that the new UI needs no external origins. Fonts are self-hosted via `geist`; canvas-confetti runs on the main thread. Keep `script-src 'self'` and drop `'unsafe-inline'` when Next supports nonces in this setup.
3. **Rate limits:** per-user and per-IP limits on writes, the assistant, Codeforces linking (it calls an external API), and library search.
4. **Observability:**
   - Structured logs with request IDs (already present).
   - Traces for the LLM and judge.
   - Alerts on judge queue depth, LLM error rate, and Codeforces sync failures.
5. **Backups and restore drill:** the CI exercise exists; schedule real backups.
6. **Security review:**
   - Library routes (IDOR checks on marks), the tool sandbox (tools are user-scoped by construction), and export and delete coverage for the new tables (done; add tests for delete).
   - Dependency audit and a secret scan (gitleaks is in CI).
7. **Load test:** 200 concurrent learners. `/today`, `/library` (which scores 14k problems in Python per request) and the assistant SSE.
   - Cache `PracticeIndex` scoring per learner and day if needed.

**Done when:** staging serves the full journey over HTTPS, the load-test p95 is under 400 ms for page APIs, and alerts fire in a drill.

**Needs:** the hosting account, the domain and DNS.

---

## 14. Analytics and activation metrics (P1)

**Build:**
- Instrument these events through the existing outbox: signup, onboarding step completed, placement done, first lesson done, first quiz passed, first problem accepted, gate passed, weekly assessment done, tutor used, upgrade.
- Define activation as "first lesson plus quiz within 24 hours of signup".
- Use a privacy-respecting tool (self-hosted PostHog or Plausible plus server events). No third-party scripts without consent; keep the CSP strict.
- Dashboard: the funnel, D1/D7/D30 retention, minutes per active day, and tutor messages per learner.
- Follow `docs/product/metric-contract.md` for definitions.

---

## 15. Accessibility and performance audit (P1)

- Run axe on every page with `@axe-core/playwright` in e2e. Fix all serious and critical issues.
- Keyboard-only walkthrough of onboarding, quiz, problem, tutor and library, with visible focus everywhere.
- Contrast checks for both themes, including the platform tags and band dots.
- Reduced motion: confetti and animations are already gated, so verify this.
- Performance budgets: LCP <2.5 s and INP <200 ms on mid-range mobile. Lazy-load CodeMirror and motion on routes that need them. Check bundle size with `next build` output.

---

## 16. Content and admin tooling (P2)

- A protected admin area (role on `User`) to review drafted problems and quiz items, approve or reject them with notes, and see content-build validation results.
- Concept analytics: item difficulty and discrimination from learner answers (classical test theory). Flag items that 95% of learners get right or 90% get wrong.
- Concept-mapping review for library imports (items 6 and 7).

---

## 17. Technical debt and known issues (P1)

| Issue | Where | Fix |
|-------|-------|-----|
| `plan_for` writes `PlanRevision` during GET requests and tool calls | `learn/service.py` | Split into a pure `build_plan` read and an explicit `record_revision` on writes or a nightly job |
| SQLite lock contention under concurrent tool calls | demo only | Fine for development; production is Postgres. Add `busy_timeout` and WAL for the demo |
| `/library` scores every problem per request | `library/service.listing` | Precompute per-concept candidate lists; cache per learner and day |
| `content/practice/problems.jsonl` is 4.6 MB in git | repo | Keep (it is reviewable data) or move to a release artifact downloaded at build |
| Company data from a repo with no licence | `import_practice.py` | Facts only (titles, links, frequency); legal review before launch |
| Codeforces problemset snapshot ages | `import_practice.py --fetch` | Monthly scheduled import job with a diff report |
| C++ tests fail locally on MinGW 6.3 | dev machines | Document MSYS2 GCC; the doctor script already suggests it |
| One e2e flake seen once (mobile beginner journey) | `tests/e2e` | Run with `--repeat-each=5` in CI nightly; fix waits |
| `CardTitle` now renders `h3` by default | `components/ui/card.tsx` | Review heading hierarchy per page (h1 → h2 → h3) during the accessibility audit |
| Placement and quiz items: 234 authored, options were always A | content | Shuffling fixed; authors may keep the answer first. Add more items (item 3) |

---

## Quality bar for every item

- **Correctness:** unit tests for pure logic, API tests for routes (auth, CSRF, IDOR), and e2e for the learner journey. Coverage stays ≥85%.
- **Explainability:** every adaptive decision shown to learners has a plain-language reason (the `reasons` pattern in the planner and recommender).
- **Integrity:** no answers in the client before grading; server-side randomisation; assistance lowers mastery credit.
- **Licensing:** no copied statements, editorials or book text; links and facts only, with provenance recorded.
- **Hidden goal:** CP progression shapes recommendations and plans but never appears in copy outside the CP course.
- **Design:** follow `docs/redesign/DESIGN-SYSTEM.md`: tokens from `apps/web/src/app/globals.css`, the status system for every learning state, one violet hero per screen, light and dark parity, no horizontal overflow from 320 px, skeletons over spinners.
- **Privacy:** new tables appear in export and are removed on account deletion; no secrets in logs or the repository.
