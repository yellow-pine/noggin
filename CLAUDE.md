# noggin

Animatronic Mech (Bambu CyberBrick, PurpleShark's eyes / pan-tilt / mouth series) that reacts to Claude Code. Public: github.com/yellow-pine/noggin.

## Directives from Cansin

- Interviewing or grilling me: ALWAYS the AskUserQuestion tool, never a markdown list of questions.
- Record my directives in this file. Keep it short: pointers, not restated facts.
- Development cycle: grilling is interview-only, never build during it. Then the mattpocock skills cycle (research / prototype / domain-modeling as needed, plan, tdd, code-review, pr). Separate PRs for separate concerns.
- Install nothing into ~/.claude or launchd without an explicit go.
- Feature-first layout, never function-first: `eyes/`, `reactions/`, `noggin/`; tests beside the code. Later `pan_tilt/`, `mouth/`.
- Keep it minimal (ponytail is active). Smallest thing that works.
- The process is "noggin" or "the noggin service", never "daemon".
- No remote-control build; the Core is driven over USB-C from this Mac.
- Don't spend effort on dataset/reference license checks; Cansin takes that on.
- Status line shows the current dev-cycle step from `~/.claude/.cycle-step` (one line, e.g. `noggin:tdd`); update it when a step starts.

## Where things are

- Vocabulary: `GLOSSARY.md`. Architecture decisions: `docs/adr/`. Behaviour table: `README.md`.
- Hardware, calibration lessons, how to talk to the Core: `docs/build-notes.md`. Never flash firmware with esptool.
- Primary-source research (hooks, serial, launchd, eye kinematics): `docs/research/`.
- PurpleShark's PDFs/STLs/configs and the GazeBase cache: `docs/references/` (gitignored, local only).
- Checks: `make check` (CI runs the same). Board: `make flash`, `make start`/`stop`. Tuning: `noggin/noggin set|pose|exercise`.
