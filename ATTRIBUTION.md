# Attribution

> **Draft. Requires legal review before publication.**

Socrat writes its own lessons, quizzes and problems. It links to external learning
resources, and it adapts material only from sources whose license allows it, with credit.

The authoritative list is data, not this file:

- `content/sources/registry.yaml` records every source, its license, whether that license
  has been verified on the source's own page, and how Socrat may use it (adapt, share-alike
  lane, link only, per item, or not until verified).
- Any lesson, quiz item, problem or atom pack adapted from a source declares it in a
  `provenance` block, and catalog loading rejects adaptation from a source that is
  unverified or does not allow it.
- The public page `/attribution` (API `GET /api/v1/attribution`) shows both lists.

## Current state

- No shipped content adapts third-party text. Everything is written by Socrat.
- Non-commercial, no-derivatives and all-rights-reserved sources (for example USACO Guide,
  the Competitive Programmer's Handbook, CS50, MIT OpenCourseWare, LeetCode, Codeforces and
  video channels) are linked only.
- Licenses marked unverified in the registry were reported by secondary sources and must be
  checked on the source's own page before any adaptation.

Questions or corrections: open an issue with the source and the record it concerns.
