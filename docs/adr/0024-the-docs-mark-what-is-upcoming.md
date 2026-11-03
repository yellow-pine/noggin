# The docs mark what is upcoming

> Decided with Cansin on 2026-11-04, spec #889 (its grilling), ticket #894. Supersedes ADR 0019's publishing rules and
> restates its licence rule. Amends ADR 0008, 0009, 0013 and 0022.

The project is told as if it began at the Mech's Stage 1: the Mech built from another designer's parts is forgotten (its
methods survive as guidance, never its numbers), and there is one Mech. A newcomer must tell a step they can do from one
that is only planned, so every page says what the code does today and marks what an open issue will change.

- **Issues are fact.** Every open GitHub issue is a decision the docs follow; where two disagree, the newest decision
  wins and the docs tell that one alone. A stale issue body is edited to the newest decision, with Cansin's go.
- **Code decides what is done.** What the code does today reads in plain present tense, with no mark. A mark never
  shows done work as upcoming: an issue whose change has landed is closed or trimmed to what is left.
- **The marks**, plain Markdown that reads the same on GitHub and on the Site, each naming its issue as `#N` linked to
  it:
  - a value an open issue changes: `~~what it is~~ *what it will be (#N)*`;
  - a capability still to come: `*Upcoming (#N): …*`;
  - a whole upcoming section: it opens with a `> [!NOTE]` alert naming its issue.

  A single `~` in prose is escaped or avoided, since the Site's Markdown strikes text between single tildes.
- **A gap gets an issue before a mark.** Something the docs need and no issue covers is filed first, its title a
  Conventional Commit (#767), then marked, so every mark links an issue.
- **Where marks go.** Every reader-facing page marks the open issues that change it. CI and tooling issues are marked
  only on the CI/CD page and in CONTRIBUTING.md, never on a page a builder reads.
- **The Roadmap page** (under Model) lists every mark grouped by its issue, each linking the page and anchor it sits on:
  the Site's Markdown plugin collects the marks as it builds, so the Roadmap is derived, never listed (ADR 0011).
- **Main's sync check.** Main's Checks fails when a mark names a closed issue, read from GitHub with the workflow's
  token, so the PR that closes #N must clear #N's marks (or main fixes forward, #283). The slim PR gate does not run it:
  PRs stay fast and need no network (#696). Without the token the check is skipped.
- **The licence rule stays** (ADR 0019's reason, restated): the designer's models are licensed against any derivative,
  so nothing in the repo, the Site, the README or a release carries the designer's geometry or dimensions; the Mech is
  designed clean-room from its requirements. Others' meshes join only under their own licences (ADR 0023).

ADR 0019's publishing rules go with today's Mech: the `next-` names, the guard that published only `next-` files, and
the rule that today's Mech is shown nowhere. What the Site publishes is the Mech's documents, as the Model makes them.

## Considered options

- Docs that describe the plan as if built: a newcomer buys parts for a Stage that does not exist.
- Docs that describe only the code: the decided changes, often days away, are invisible, and every page is rewritten
  when each lands.
- Custom syntax (a directive or a component per mark): the Site could style it, but GitHub would show the raw syntax,
  and the repo's Markdown is read on both.
- The sync check on every PR: catches a stale mark before merge, but needs the network and a token on the slim gate,
  and a PR can't know which issue its merge closes until it does.
