# noggin

Animatronic Mech that reacts to Claude Code. See README.md.

## Directives from Cansin

- Interviewing or grilling me: ALWAYS the AskUserQuestion tool, never a markdown list of questions.
- Record my directives in this file. Keep it short: pointers, not restated facts.
- Development cycle: grilling is interview-only, never build during it. Then the mattpocock skills cycle (research / prototype / domain-modeling as needed, plan, tdd, code-review, pr). Separate PRs for separate concerns.
- Every branch gets its own PR straight against main with auto-merge on (`gh pr merge --auto --squash`); no integration or feature branches grouping tickets.
- PR titles are Conventional Commits: the required `PR Title` check and release-please read them (CONTRIBUTING.md, ADR 0010).
- Standards and well-maintained open-source libraries first: wherever one covers the job, use it instead of custom code; always for security, protocols, parsing and numerics. Small glue stays custom (ponytail).
- Never a paid service or paid tier (plugins, early access, hosted search); free and open-source only.
- Install nothing into ~/.claude or launchd without an explicit go.
- Feature-first layout, never function-first; tests beside the code.
- Keep it minimal (ponytail is active). Smallest thing that works.
- The process is "noggin" or "the noggin service", never "daemon".
- No remote-control build. Both Cores are on Wi-Fi, addressed directly by the noggin service; USB-C only for flashing and as fallback (ADR 0005). One pack and switch board per shield is a planned edit (docs/model-notes.md), not in the model yet.
- The digital model of the Mech is "the model" (folder model/), never "twin".
- Don't spend effort on dataset/reference license checks; Cansin takes that on.
- Ground truth for the model, in order: Cansin's build (photos in docs/references/build-photos, local only; measurements), then our model (parts, MuJoCo, reports, tests). The designer's and vendor's files are credits (`docs/credits.md`) and history (docs/research) only. Planned edits go in notes only, never into the model, until they stabilise. Record every conflict with both sources; inference only fills what none settles, marked inferred.
- I can't measure (no calliper): a size my build doesn't settle is a best guess from its behaviour or photos, then the model's nominals, marked inferred.
- Hardware never gates a merge: Core and Link PRs merge on green, and I try them on the physical Mech after.
- Blender authors every picture of the Mech (README, docs, PR pictures; diagrams are Mermaid in the Markdown); the web viewer draws Blender's glTF with the look Blender writes into it (ADR 0008).
- No real photos in git, the README or the site until staged photos exist; Blender pictures and the viewer stand in.
- Sources only in git: CI builds every generated output and the site serves it (ADR 0009).
- README is for contributors: setup, checks, CI. Building and using the Mech live on the site (#279).
- Derived, not listed: whatever the code can deduce (gesture names, servo ports, the eye program's files, Stage and document ids) is read from its one source; a copy that must stay gets a test against it (ADR 0011, test_derived.py).
- Keep everything current: the newest stable release at least 14 days old, security fixes at once; Dependabot's cooldown enforces the 14 days, so review judges a bump on its merits, never rejecting or flagging it for being newer; the Core's firmware through the vendor's tools only (ADR 0012).
- When a dev-cycle step starts, write its name to `~/.claude/.cycle-step` (the status line shows it).

## Where things are

- Vocabulary: `GLOSSARY.md`. Architecture decisions: `docs/adr/`. Behaviour table: the site's home (`docs/index.md`) and `docs/use/gestures.md`, built by `macros.py` from the code (numbers in docs: ADR 0009).
- Building the Mech (parts, Stages, wiring, flashing, calibration lessons): `docs/build/`; running it (noggin service, hooks, gestures, tuning): `docs/use/`. esptool only for read-only queries, never a write (ADR 0012).
- The site: Astro Starlight in `site/` (ADR 0013), home `docs/index.md`, nav `site/astro.config.mjs`, vendor and designer names on `docs/credits.md` and the buy list only (test_vocabulary.py).
- Morty face modules (3 stages, parts to buy): `docs/face-design.md`; source will live in `face/`.
- Model pictures (Blender, from MuJoCo's trajectories; look, views, GIFs): `docs/model-notes.md`; `make render`, `make gifs`; CI builds the README's (`make pictures`) for the site's /images.
- Web viewer (three.js page at the site's /viewer): GLBs `web/`, page and module `site/src/`, ADR 0008; `make web` builds the GLBs, `make site` the whole site.
- Primary-source research (hooks, serial, launchd, eye kinematics): `docs/research/`.
- The designer's PDFs/STLs/configs and the GazeBase cache: `docs/references/` (gitignored, local only).
- Checks: `make check`; CI's jobs and time budget: CONTRIBUTING.md. Board: `make flash`, `make start`/`stop`. Tuning: `noggin/noggin set|pose|exercise`.
