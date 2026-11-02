# A new ADR keeps its number until main has taken it, then one command renumbers it

> Decided while Cansin was away, #398 (the choice in its "Decision (made while away)" comment). Research:
> docs/research/2026-11-02-adr-numbering.md.

Two PRs drafted at once both took the next ADR number (0012 against the Starlight PR's), and one was renumbered by
hand, references and all. Every numbering tool (adr-tools, MADR) picks the number from the drafter's checkout; the
number can't be picked at merge here, since main takes no bot commit and we run no merge queue. So a draft takes the
next free number as before, and two things catch the clash:

- **A test fails on a taken number.** `scripts/test_adr_number.py` fails when two ADRs share a number. Code runs it on
  the PR merged into main, so a PR whose number main has taken since it was drafted goes red; on main it catches the
  rare pair of PRs that were green at once (fixed forward, #283).
- **One command renumbers.** `python3 scripts/adr_number.py docs/adr/NNNN-slug.md` moves the draft to the number
  after the highest on main and in the branch, and rewrites the old number on the lines the branch added (`ADR NNNN`,
  `docs/adr/NNNN`, the file name), leaving main's own references alone.

## Considered options

- log4brains' dates for names (`YYYYMMDD-slug.md`, no numbers): no clash at all, but renames all 14 ADRs and ~200
  references ("ADR 0005"), and two ADRs of one day still sort by slug, not by when they landed.
- Numbering at merge (a bot renumbers on main, or a merge queue): main rejects a bot's push, and a queue for one rare
  clash slows every PR.
