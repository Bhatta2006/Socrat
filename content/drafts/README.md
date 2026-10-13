# Drafted judge problems

Problems waiting for human review live here as `<course>/<id>.yaml`, using the same schema
as `content/courses/<course>/problems/`. Drafts also need a `brute` force and a
`small_generator`, so the quality gates can cross-check the reference solution.

1. Draft one with Claude (needs `SOCRAT_ANTHROPIC_API_KEY`):
   `python scripts/content/draft_problem.py --course dsa --concept two-pointers --difficulty medium --idea "…"`.
   You can also write one by hand.
2. Run the gates locally: `python scripts/content/validate_problems.py --drafts-only`.
3. Review it in the app at `/admin` → **Review queue** (your account must be in
   `SOCRAT_ADMIN_SUBJECTS`). Run the gates, read the statement, hints and solutions, then
   approve the draft or request changes.
4. Approving moves the file into the course, records the reviewer in its `review:` block
   and links it from its concept. Then run `python scripts/content/build.py` and commit.

Sidecar files (`*.validation.json`, `*.review.json`, `*.draft.json`) are working state and
are not committed.
