# A new ADR keeps its number until main has taken it, then one command renumbers it

> Decided on 2026-11-02 while Cansin was away, #398 (its "Decision (made while away)" comment). Research:
> docs/research/2026-11-02-adr-numbering.md.

Two PRs drafted at once both took the next ADR number (0012 against the Starlight PR's), and one was renumbered by
hand, references and all. Every numbering tool (adr-tools, MADR) picks the number from the drafter's checkout; the
number can't be picked at merge here, since main takes no bot commit and we run no merge queue. So a draft takes the
next free number as before, and two things catch the clash:

- **A test fails on a taken number.** `scripts/test_adr_number.py` fails when two ADRs share a number. Code runs it on
  the PR merged into main as of its last push, so a PR pushed after main took its number goes red. Two PRs green at
  once, neither pushed after the other landed, both merge (PRs need not be up to date, #283): then main's own Code run
  goes red, and the one that landed second is fixed forward with the same command, its squash commit's parent as the
  base.
- **One command renumbers.** `.venv/bin/python scripts/adr_number.py docs/adr/NNNN-slug.md [base]` fetches main,
  moves the draft to the number after the highest on main and in the branch, and rewrites the old number on the lines
  the branch added since it left the base (`ADR NNNN`, `docs/adr/NNNN`, the file name), leaving main's own references
  alone.

## Considered options

- log4brains' dates for names (`YYYYMMDD-slug.md`, no numbers): no clash at all, but renames all 14 ADRs and ~190
  references ("ADR 0005"), for a race a re-push or one command settles.
- Numbering at merge (a bot renumbers on main, or a merge queue): main rejects a bot's push, and a queue for one rare
  clash slows every PR.
- Requiring PRs up to date with main (strict status checks): closes the race, but every merge would send every open
  PR back through its checks, which #283 chose against.
