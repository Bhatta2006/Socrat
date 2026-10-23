# Socrat evaluation

Method: three learner personas walked through the live app (desktop 1440px, dev build, simulated login), then a UI audit. Severity: **B** blocker, **F** friction, **P** polish.

## Phase 1: Beginner ("Asha", never written code)

Flow covered: landing, no-signup try-it, login, 6-step onboarding, Today, first lesson, "More simply", concept check, practice problem, tutor hint, submit, Today again, Playground.

**What works:** onboarding is short and clear; study-time step has good defaults; "More simply" gives a real plain-English rewrite; quiz feedback explains each answer; the tutor's hint was a good guiding question; the runner shows expected vs actual; streak and minutes update.

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| 1 | F | Landing try-it | "I don't know where to start" gets a sliding-window hint ("which two numbers leave the sum…"). A true beginner can't use it; the first reply should restate the problem in plain steps. |
| 2 | F | Onboarding step 4 | Python / C++ / Java with no "recommended for beginners" nudge. |
| 3 | P | Onboarding | Moving between steps leaves the page scrolled mid-page, so the progress bar and Back are cut off at the top. |
| 4 | F | Lesson 1 content | A "from zero" first lesson contains O(k) cost notes, "judge", "boundary cases" and a newline-counting check question. Jargon too early. |
| 5 | F | Lesson | Code samples are copy-only. No "Run this" button, so a beginner can't try the code where they read it. |
| 6 | F | Lesson | "Read" stays "Not read yet" after reading unless the learner finds "Mark lesson as read". Status panel reads "Needs practice" after a 1/5 check, which feels punishing. |
| 7 | F | Concept check | Q5 tests `sep=` and `end=`, which the lesson never taught. Result page says "More practice is on its way" with no concrete next step or button besides a small "Continue". |
| 8 | P | Concept check | URL is `/quiz/quiz/...` (duplicated segment). "Next question" sits at the very bottom edge of the viewport. |
| 9 | **F** | Today | After finishing the lesson check and a problem, the hero card still says "Start lesson, learn the idea first". Progress only shows lower down ("2 of 4 done"). The main CTA is stale. |
| 10 | F | Problem page | After Run or Submit the result appears far below the fold with no auto-scroll. After a first solve the only top-of-page signal is a small "Solved" chip; no celebration, no "Next problem" button, only a "Back to Today" text link. |
| 11 | F | Problem page | The Ask Soc panel covers the test output, so a learner can't see the failing result while asking about it. "Show solution" is visible from the first message. |
| 12 | P | Problem page | Left description column ends early and leaves a large empty area while the right column scrolls. Run/Submit are duplicated top and bottom. |
| 13 | F | Practice basics | Starter code uses `int(input())` which was never introduced. |
| 14 | F | Playground | Generation took about 85 s. Only "stay on this page" is shown, with no cancel and no way to leave safely. The example placeholder (binary search) is advanced for a beginner. |
| 15 | F | Playground output | Explanation panel text has broken wrapping and odd indentation mid-sentence; it also uses "rebinds" and "literal". |
| 16 | **F** | Login (my change) | After removing the decorative shapes, the left panel on `/login` is a large empty lavender block. Needs a replacement (Soc avatar or short copy). |
| 17 | P | Today | Skill-map card is sparse: three dashed circles with large empty space; the 10-step product tour is long (skippable). |

## Phase 2: Moderate learner ("Mohan", knows some DSA, wants a steady plan)

Flow covered: onboarding (DSA course, "studied some DSA"), adaptive placement, Today, Skills roadmap, Practice (library, focus sprint, company sprint), Evidence, global search, Tries lesson, Settings.

**What works:** onboarding level options adapt to the course; placement has "Not sure yet" and says it isn't marked wrong; the roadmap shows weekly milestones and a finish date; Settings is complete (schedule, course switch, data export, delete account); the problem library has skill, difficulty and status filters plus company sprints.

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| 18 | **B** | Placement | Five answers (3 correct) mark about 40 skills as "assumed", including Graphs, DP and Binary trees. Far too aggressive; the learner is dropped at Tries. |
| 19 | **B** | Evidence / Skills | Assumed skills are counted as done: Evidence says "79% complete, 31 of 39 skills" next to "0 mastered, 0 solved". Skills shows "3/4 done" and full progress bars for modules never studied. Today says "0 skills mastered". Three screens, three stories. |
| 20 | **B** | Plan vs content | Roadmap schedules Graphs, DP (1D/2D), Union-Find, Topological sort and Weighted shortest paths, but the problem library has **0 problems** for each of those skills (and 0 for Tries in the list, 1 on the lesson page). |
| 21 | F | Practice | Library says "1,582 problems unlocked from the skills you have finished" when none are finished. Most rows are LeetCode links that leave the app and aren't judged, while landing page claims "112 judged problems". Judged and external problems are mixed with no clear separation. |
| 22 | F | Navigation | Sidebar "Practice" goes to `/library`; `/problems` is a 404 (with Practice highlighted) and there is no `/problems` index. Page titles, URLs and nav labels disagree (Evidence = `/progress`, Skills = `/plan`, Practice = `/library`). |
| 23 | F | Global search (Ctrl K) | Searching "graph" returns "Lexicographically…" problems (substring match) and no lesson or skill for "Graphs, BFS and DFS". Results are only Pages and Problems. |
| 24 | F | Onboarding / logout | The name step prefilled the previous learner's name after logout and login without a reload, so a new account was saved with another person's name (Mohan's account is named "Asha Beginner"). Client state isn't cleared on logout. |
| 25 | F | Today vs Skills | Same day, two durations: Today says 30 min, Skills "Next two weeks" says 25 min. |
| 26 | P | Sidebar | Collapsed icon-only rail by default for this account, no visible labels. |
| 27 | P | Skills | The module hero card (after removing the decorative shape) has a large empty right half. |
| 28 | P | Company sprint | Company names are title-cased wrongly: "Tcs", "Ibm", "De Shaw", "Phonepe", "Tiktok", "Servicenow", "Jpmorgan". |
| 29 | P | Dev login | Submitting a new name while already signed in does not make clear that the previous session was replaced (dev-only). |

## Phase 3: Topper ("Tara", competes regularly) and UI audit

Flow covered: onboarding (Competitive Programming, "I compete regularly"), placement (5/5 correct), Today, Skills, Practice library, Focus sprint, logged-out access and deep links, quiz refresh, then a UI audit (desktop 1440px and 502px mobile, dark and light themes, keyboard focus, basic accessibility).

**What works:** placement questions are genuinely contest-level (knapsack, Euler tour, LOG, Dijkstra, 0-1 BFS); dark theme is clean and consistent; logged-out visitors are redirected to login on every protected page; focus rings are visible; no unnamed buttons, unlabeled inputs or images without alt text on pages checked; mobile has a sticky Run/Submit bar on problems and a bottom nav.

| # | Sev | Where | Finding |
|---|-----|-------|---------|
| 30 | **B** | Placement | 5 of 5 correct marks **54 of 54 skills** "assumed". Result screen says "Your plan starts from the beginning", contradicting the perfect score. |
| 31 | **B** | Today / Skills | Topper is stranded. Today: "Done for today", course 100%, projected finish Oct 23, 0 mastered. Skills: current module is the beginner "First steps" (3/3, 0 min left). Nothing to study and no contest content offered. |
| 32 | **B** | Focus sprint | "Start sprint" fails with "Something went wrong: finish a concept check on a topic first". Normal precondition shown as an error, and unreachable for the learner placement just told to skip everything. |
| 33 | F | Practice | Topper sees "Foundations, about 950, 75% to Builder" (same as the moderate learner) and "Recommended: finish your first lesson". Placement doesn't affect the practice level. "12,765 problems unlocked from skills you have finished" with none finished. |
| 34 | F | Deep links | Opening a lesson from another course (`/learn/dsa/tries` as a contest learner) shows "Something went wrong (not_found)" with the raw code instead of a friendly 404 or "switch course" prompt. |
| 35 | F | Login | After logging in, the visitor always lands on Today; the page they originally requested is lost. |
| 36 | F | Quiz | Reload during a concept check returned to Question 1 (not fully verified; answer state may not persist). |
| 37 | F | Mobile Practice tabs | Tab bar clips "Focus sprint" and shows a bare native horizontal scrollbar. |
| 38 | F | Mobile problem page | Title truncates ("Echo a readi…"); the editor sits below a long description, so Run is a sticky bar but the code isn't visible when pressing it. |
| 39 | P | Placement | Submit button jumps vertically between questions when the question wraps to two lines. |
| 40 | P | Practice (desktop) | "Foundations about 950" wraps awkwardly; the "Recommended for you" and Focus sprint cards are mostly empty space. |
| 41 | P | Mobile Today | Floating Soc button overlaps cards just above the bottom nav; the tour dialog covers the greeting on first load. |
| 42 | P | Landing | Logged-in users are always redirected to Today and can't view the home page. |

## Fix status (updated after the first fix pass)

Done: #18/#30/#31 placement now keeps the last 15% of the path unassumed (`SKIP_CAP` in `placement/engine.py`); #19 assumed skills no longer count as finished (API `progress.assumed`, Today, Skills, Evidence); #20 lessons with no judged problems say so and link to external problems; #9 a finished concept check marks its lesson read; #10 results scroll into view and success has a "Continue to Today" button; #4/#7 lesson 1 jargon removed and `sep`/`end` taught before the quiz asks; #32 sprint precondition shows "Not ready for a sprint yet" with a Skills button; #34 `not_found` has a plain message; #22 `/problems` redirects to `/library`; #23 problem search matches word starts; #35 login returns to the requested page; #16/#27 login panel and module hero now show Soc.

Done in the second pass: #5 code samples in lessons have a "Try in Playground" link that prefills (never auto-runs) the Playground request; #13 the first problem explains `input()` and `int()`; #24 sign-out clears the onboarding draft kept in `sessionStorage` (the real cause of the stale name); #33 the practice level was stuck near "Foundations" because one concept outside the learner's course counted as zero and stopped the ladder climb (`library/ladder.py`, with a test); #37 mobile Practice tabs hide the bare scrollbar and keep the current tab in view.

Done in the third pass: #21 the library header says its problems are external (LeetCode, CSES, Codeforces, opened on those sites, not judged) and points to the judged problems on lesson pages; #25 Today says "goal 30 min" and Skills says "N min planned"; #28 well-known company names corrected (TCS, IBM, PhonePe, TikTok, JPMorgan and about 30 more); #38 mobile problem title wraps instead of truncating; #39 placement question title has a minimum height so Submit stays put; #40 practice level text no longer wraps oddly and the empty "Recommended" card has a button; #41 phones get bottom padding so the floating Soc button and nav don't cover the last card.

Checked and not a bug: #36 quiz progress survives a reload (Question 2 stayed Question 2). Left as designed: #26 the sidebar collapse is a saved per-browser preference; #29 dev-only login behaviour; #42 signed-in visitors going from the landing page to Today is an intentional redirect.

## Summary: fix first

1. **Placement and "assumed" skills (#18, #19, #30, #31).** Cap how many skills one short check can skip, never count assumed skills as "done" in progress numbers, and give high scorers real next content (hard problems or the next unseen topic) instead of "Done for today".
2. **Plan promises vs. content (#20).** Don't schedule modules with no judged problems, or show them as "lessons only".
3. **Make the first-run path coherent for beginners (#4, #5, #7, #9, #10, #13).** Plain-language lesson 1, runnable code samples, and a "Next problem" button after a solve; Today's hero card must follow lesson and check progress.
4. **Sprint and error states (#32, #34).** Turn preconditions into friendly guidance with a button to the needed step.
5. **Navigation clarity (#22, #23, #35).** Align URLs, labels and tabs; improve search; return to the requested page after login.
6. **Login panel (#16).** Replace the empty lavender block left by the removed decorative shapes (Soc avatar or short copy), and fill the empty hero card halves (#27).

**Not covered:** C++/Java paths, Codeforces linking, Passport sharing, reminders/PWA install, real LLM tutor mode (offline hints used), light theme on every page, and screen-reader testing. Dev build notes (banner, "1 Insight" badge) were ignored.
