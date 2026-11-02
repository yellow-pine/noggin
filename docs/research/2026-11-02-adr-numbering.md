# How ADR tools number a new ADR, and what that means for two PRs drafting one at once

For #398: two PRs claimed the same ADR number (0012 against the Starlight PR's, renumbered by hand). What do the
community's ADR formats and tools do, and which fits our squash-merge, auto-merge flow (CONTRIBUTING.md)?

## The tools

- **adr-tools** (npryce/adr-tools, `master` at `b3279ba`, 2020-03-30): `adr new` takes the highest number in the
  directory and adds one (`src/adr-new`, lines 96-102: `ls $dstdir | grep -Eo '^[0-9]+' ... | sort -rn | head -1`,
  `newnum=$(($maxid + 1))`, `printf "%04d"`). It reads only the local checkout, so two branches get the same number;
  it has no renumber command and no check.
- **MADR** (adr/madr, `develop` at `ba75bb1`, 2026-08-28): names files `NNNN-title-with-dashes.md`, "where `NNNN`
  indicates the next number in sequence" and "is a consecutive number" (`docs/index.md`, lines 117 and 123-125,
  ADR-0005 for the dashes). It says nothing about branches that race for a number; with categories, "numbers of ADRs
  are no longer unique throughout the repository, but locally within a category only" (line 166).
- **log4brains** (thomvaill/log4brains, `17e3202`, 2024-12-17): no numbers at all. Its README lists "No required file
  numbering schema (i.e., `adr-0001.md`, `adr-0002.md`...): avoids git merge issues" (line 47). Its own ADR
  `docs/adr/20201016-use-the-adr-slug-as-its-unique-id.md` gives the reason: `NNNN-adr-title.md` "causes an issue
  during a `git merge` when two developers have created a new ADR on their respective branch", so the slug is the id
  and the file is `YYYYMMDD-adr-title.md`, sorted by its Date field, then git's creation date, then the slug.

## What that leaves us

- Every numbering tool picks the number when the ADR is drafted, from the drafter's checkout. None picks it at merge;
  the one tool that faced the race (log4brains) dropped numbers rather than coordinate them.
- Picking at merge here would need a commit on main after the merge (a bot renumbering) or a merge queue; main's
  ruleset rejects a bot's push and we run no merge queue (CONTRIBUTING.md).
- Dropping numbers (log4brains' way) renames all 14 ADRs and rewrites about 200 references ("ADR 0005",
  "docs/adr/0013", "docs/adr/0011, 0013") across the docs, code comments, workflows and CLAUDE.md: `git grep` counts
  ~89 `ADR NNNN` and ~55 `docs/adr/NNNN` alone.
- What a PR's checks see: a `pull_request` run checks out the PR merged into main
  (`refs/pull/N/merge`, actions/checkout's default for that event), so a test over `docs/adr/` on that tree sees main's
  ADRs beside the PR's. It does not re-run when main moves later, and our PRs need not be up to date (#283): two PRs
  green at once can still both merge, and then main's own Code run fails, to be fixed forward.
