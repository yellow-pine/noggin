# Contributing

Thanks for stopping by. noggin is a small hobby project, run in the open.

## How work runs

- Work starts from a GitHub issue (a ticket). Open one before a big change so the shape can be agreed first.
- The cycle, in order: grilling (interview only, nothing is built) → research and domain modelling as needed → plan/spec → TDD → code review → PR → retro.
- One PR per concern. Keep it small.
- A spec gets one integration branch with one PR into main. Each ticket is built in its own worktree on its own
  branch, with a normal PR into the integration branch opened on the first push; whoever works the ticket keeps that
  PR green and merges it when done, which deletes the branch. Every branch on GitHub has a PR, except parked work.
- Vocabulary lives in `GLOSSARY.md` and the decisions in `docs/adr/`; use those words and record a new decision as a new ADR.
- Hardware facts and calibration lessons are in `docs/build-notes.md`. Never flash firmware with esptool (see ADR 0002).

## Code

- Feature-first layout: `eyes/`, `noggin/`, `reactions/`, `model/`. Tests sit beside the code they test (`test_*.py` in the same folder).
- Smallest thing that works; no options or abstractions nobody asked for.
- Run `make check` before opening a PR. CI runs the same.

## Licence

noggin is licensed under PolyForm Noncommercial 1.0.0 (`LICENSE.md`). By contributing you agree that your contribution is licensed under the same terms, with Yellow Pine as the licensor.

Questions: hello@yellowpine.com.
