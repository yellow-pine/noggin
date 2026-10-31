# noggin

Animatronic Mech that reacts to Claude Code. See README.md.

## Directives from Cansin

- Interviewing or grilling me: ALWAYS the AskUserQuestion tool, never a markdown list of questions.
- Record my directives in this file. Keep it short: pointers, not restated facts.
- Development cycle: grilling is interview-only, never build during it. Then the mattpocock skills cycle (research / prototype / domain-modeling as needed, plan, tdd, code-review, pr). Separate PRs for separate concerns.
- Every branch gets its own PR straight against main with auto-merge on (`gh pr merge --auto --squash`); no integration or feature branches grouping tickets.
- Standards and well-maintained open-source libraries first: wherever one covers the job, use it instead of custom code; always for security, protocols, parsing and numerics. Small glue stays custom (ponytail).
- Install nothing into ~/.claude or launchd without an explicit go.
- Feature-first layout, never function-first; tests beside the code.
- Keep it minimal (ponytail is active). Smallest thing that works.
- The process is "noggin" or "the noggin service", never "daemon".
- No remote-control build. Both Cores are on Wi-Fi, addressed directly by the noggin service; USB-C only for flashing and as fallback (ADR 0005). One pack and switch board per shield is a planned edit (docs/model-notes.md), not in the model yet.
- The digital model of the Mech is "the model" (folder model/), never "twin".
- Don't spend effort on dataset/reference license checks; Cansin takes that on.
- Ground truth for the model, in order: Cansin's build (photos, measurements), then our model (parts, engine, reports, tests). PurpleShark and the Bambu files are credits (README) and history (docs/research) only. Planned edits go in notes only, never into the model, until they stabilise. Record every conflict with both sources; inference only fills what none settles, marked inferred.
- When a dev-cycle step starts, write its name to `~/.claude/.cycle-step` (the status line shows it).

## Where things are

- Vocabulary: `GLOSSARY.md`. Architecture decisions: `docs/adr/`. Behaviour table: `README.md`.
- Hardware, calibration lessons, how to talk to the Core: `docs/build-notes.md`. Never flash firmware with esptool.
- Morty face modules (3 stages, parts to buy): `docs/face-design.md`; source will live in `face/`.
- Model pictures (Blender from the engine poses; look, views, GIFs): `docs/model-notes.md`; `make render`, `make gifs`.
- Primary-source research (hooks, serial, launchd, eye kinematics): `docs/research/`.
- PurpleShark's PDFs/STLs/configs and the GazeBase cache: `docs/references/` (gitignored, local only).
- Checks: `make check` (CI runs it plus shellcheck). Board: `make flash`, `make start`/`stop`. Tuning: `noggin/noggin set|pose|exercise`.
