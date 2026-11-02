# just runs the recipes, not Make

> Decided with Cansin on 2026-11-02, #492 (the research is its body: Make, just and Task side by side).
> Amended 2026-11-02 (#547): the older ADRs' commands to run are `just` recipes; their history keeps `make`.
> Amended 2026-11-02 (#611): Claude Code's own deny list in `.claude/settings.json`, not a hook of ours, keeps the
> heavy recipes for CI.

The Makefile had grown to 44 targets with one real file dependency; the rest were commands. About 33 of its 54 commits
on main edited the one shared `.PHONY` line, so two PRs adding a target clashed, and the Claude Code hook found the
heavy targets with a regex over rule headers. So the commands live in a `justfile` and run with
[just](https://just.systems):

- **One pin.** just comes with the dev dependencies (`rust-just` in pyproject, locked in uv.lock), so CI runs
  `uv run just <recipe>` and needs nothing else installed; the CI images drop `make`.
- **No `.PHONY`, groups instead of a regex.** A recipe that takes the heavy lock is in `[group('heavy')]`;
  Claude Code's deny list names each recipe in it, and tests read the group from `just --dump --dump-format json` to
  hold the list and every recipe that uses the lock to it.
- **Comments are the help.** `just --list` shows each recipe with the comment above it.
- **Arguments after the recipe, variables before it**: `just view noggin-neck`, `just BLENDER=blender pictures`.
- **Up to date stays ours.** just has no timestamps (its `[cache]` is unstable); `ours` keeps its `.key`, the
  trajectories their stamps, and the MicroPython build checks for its binary.

The ADRs before this one keep the `make` words of their day where they record what was done; where they say
what to run, they name the `just` recipe.

## Considered options

- Make with one `.PHONY` per target: the smallest change, but the hook's regex and the merge clashes on inserts stay.
- Task (Taskfile.yml): checksums we can't use (`ours` hashes an import graph, not globs), parallel dependencies that
  would race `venv`, task variables that win over the command line, and a hook that would have to regex YAML.
