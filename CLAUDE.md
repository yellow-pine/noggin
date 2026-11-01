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
- Ground truth for the model, in order: Cansin's build (photos, measurements), then our model (parts, MuJoCo, reports, tests). The designer's and vendor's files are credits (`docs/credits.md`) and history (docs/research) only. Planned edits go in notes only, never into the model, until they stabilise. Record every conflict with both sources; inference only fills what none settles, marked inferred.
- Blender authors every picture of the Mech (README, docs, PR pictures; diagrams are Mermaid in the Markdown); the web viewer draws Blender's glTF with the look Blender writes into it (ADR 0008).
- Sources only in git: CI builds every generated output and the site serves it (ADR 0009).
- No real photos anywhere public (README, site) until staged ones exist; Blender pictures and the viewer instead.
- README is for contributors: setup, checks, CI. Building and using the Mech live on the site (#279).
- When a dev-cycle step starts, write its name to `~/.claude/.cycle-step` (the status line shows it).

## Where things are

- Vocabulary: `GLOSSARY.md`. Architecture decisions: `docs/adr/`. Behaviour table: the site's home (`docs/index.md`) and `docs/use/gestures.md`, built by `macros.py` from the code (numbers in docs: ADR 0009).
- Building the Mech (parts, Stages, wiring, flashing, calibration lessons): `docs/build/`; running it (noggin service, hooks, gestures, tuning): `docs/use/`. Never flash firmware with esptool.
- The site: home `docs/index.md`, nav `mkdocs.yml`, vendor and designer names on `docs/credits.md` and the buy list only (test_vocabulary.py).
- Morty face modules (3 stages, parts to buy): `docs/face-design.md`; source will live in `face/`.
- Model pictures (Blender, from MuJoCo's trajectories; look, views, GIFs): `docs/model-notes.md`; `make render`, `make gifs`; CI builds the README's (`make pictures`) for the site's /images.
- Web viewer (three.js page at the site's /viewer): `web/`, ADR 0008; `make web` builds it, `make site` the whole site.
- Primary-source research (hooks, serial, launchd, eye kinematics): `docs/research/`.
- The designer's PDFs/STLs/configs and the GazeBase cache: `docs/references/` (gitignored, local only).
- Checks: `make check`; CI's jobs and time budget: CONTRIBUTING.md. Board: `make flash`, `make start`/`stop`. Tuning: `noggin/noggin set|pose|exercise`.
