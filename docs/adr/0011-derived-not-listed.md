# Derived, not listed

> Decided with Cansin on 2026-11-01 ("whatever can be deduced from the code should be deduced from it"); #304 does
> the code, #305 CI and #306 the docs and tests.

A list the code already holds is never typed out again: the gesture names, the servos on each Core's ports, the
eye program's files, the Stage and document ids. Every copy was one more place to forget when a gesture or a servo
moved, and some had already drifted (the wiring page's second Core). So each list has one source, and everything
else reads it:

- **Gestures**: `Eyes.GESTURES` in eyes/eyes.py. The Mac reads the names with `ast` (eyes/eyes.py imports
  `machine`): `noggin/core.py` `GESTURES`, which the noggin service's demo and manual commands use.
- **Servo ports**: `CHANNELS` in model/geometry.py, the Cores by name in `noggin/core.py` `CORES` (Core 1 the eyes,
  Core 2 the neck). The setup wizard writes core.json from it.
- **The eye program's files**: what eyes/boot.py imports from eyes/, followed through their imports
  (`noggin/core.py` `MODULES`); `make mpy-list` prints them for `make mpy`, `make flash-usb` and the release
  workflow, and the noggin service flashes the same files over Wi-Fi.

Where a list cannot be read at its place, a test holds the copy to the source instead: the eye program stays
self-contained on the Core, so eyes/eyes.py keeps its own GPIO-to-servo `NAME` and a test checks it against
`CHANNELS`; tables that pair each name with something only that place knows (the Director's busy seconds, the
behaviour table's words) are tested to name exactly the source's names. test_derived.py fails when a workflow or the
Makefile names two of a list's members, or a doc three on one line (two is prose: "pan and tilt"), outside an
allow-list that says why that place spells them; the ADRs and research notes keep the words of their day.

## Considered options

- Generating the copies (a build step writing eyes/eyes.py's `NAME` from `CHANNELS`): rejected, a test does the same
  with no build step, and the eye program stays the files the Core runs.
- A config file every tool reads (`pyproject.toml [tool.noggin]` for the program's files): rejected, it is one more
  list; boot.py's imports already say what the Core runs.
