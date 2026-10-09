# Presenting the local Socrat demo

Run `npm ci`, `scripts\dev\doctor.ps1`, then `npm run dev:demo` from PowerShell. Open http://localhost:3000. Install optional C++20/JDK21 tools using the doctor's commands, then restart. The original sample pack and local sandbox are not reviewed for release. No production gate or release approval is created.

Choose Beginner (Python, zero implementation evidence), Interview prep (Java, real sample sessions), Competitive (C++, real sample sessions), or Start fresh. The experienced sample histories use normal goal/diagnostic/assessment/planning/session services and execute original reference programs through the native backend. Missing toolchains skip the corresponding sample history; no execution result is fabricated.

For a fresh learner: save your adult-confirmed profile, choose goal/language/experience/schedule, review and confirm the normalized goal, complete the starting check, review and confirm the two-week plan. Take the baseline assessment when Today asks for it, or use its single 24-hour deferral. Start a session, work through retrieval, explanation and a guided trace, then open the editor. The goal fixes the language for the whole attempt.

In the coding workspace, try an invalid program and Run samples to see a real compiler error and Problems entry. Fix it, Run samples or custom input, then Submit. Only verified submissions feed learning evidence; sample runs and reading do not prove mastery. Independent/assessment autocomplete is disabled. Hint requests and exposed explanations carry assistance metadata. Submitted source is read only. Escape then Tab leaves CodeMirror; Ctrl+F searches, Ctrl+/ comments, and the controls adjust font size and contrast.

Complete the exit check and reflection, then open Progress. Independent and assisted work are displayed separately. Assessments compare protected forms; confidence and estimated capability are not credentials. Demo controls move the isolated database clock for weekly/retention checks and missed-day recovery. A clock jump changes due dates, not scores or mastery. The scope is all learners in that demo database.

Settings offers reminders/quiet hours, reduced motion, JSON export and deletion with a private receipt. Deletion revokes sessions and exposes actual remaining cleanup work; it must not promise instantaneous provider/backup erasure. Do not share private receipts or `.env.local`.

Run `npm run test:demo` against the running native stack for desktop (1440×900) and mobile (390×844) click-only journeys in all languages. Screenshots and browser videos go to `docs/demo/screens/`; the JSON result goes to `.cache/demo-walkthrough-results.json`. The separate original 64-test suite uses its own non-demo API and database: stop the demo before `npm run test:e2e`.

Resetting a sample learner erases that learner using normal privacy services. To repeat clean bootstrap verification, use a new clone/directory; generated local state is excluded from Git. See [verification](VERIFICATION.md) for what has actually passed and any remaining limits.
