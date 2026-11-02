# noggin

Animatronic Mech that reacts to Claude Code. See README.md.

## Directives from Cansin

- Interviewing or grilling me: ALWAYS the AskUserQuestion tool, never a markdown list of questions.
- Record my directives in this file. Keep it short: pointers, not restated facts.
- Development cycle and PR workflow: CONTRIBUTING.md. Grilling is interview-only: it builds nothing, and reads docs/adr on each decision before asking.
- The main session coordinates: it grills, files tickets, briefs and relays. Every fix on a PR (a conflict, a re-run, a review thread, a label on the PR) goes to that PR's `implementer` (SendMessage while it lives, else a fresh one).
- Standards and well-maintained open-source libraries first: wherever one covers the job, use it instead of custom code; always for security, protocols, parsing and numerics. Small glue stays custom (ponytail).
- Never a paid service or paid tier (plugins, early access, hosted search); free and open-source only.
- Install nothing into ~/.claude or launchd without an explicit go.
- Feature-first layout, never function-first; tests beside the code.
- Every title, a PR's or an issue's, whoever or whatever writes it, is a Conventional Commit (CONTRIBUTING.md, #767).
- Names say "default branch" (GitHub's term), never "main red"; our labels take GitHub's default style, lowercase with spaces (#791).
- Keep it minimal (ponytail is active): the smallest thing that works.
- The process is "noggin" or "the noggin service", never "daemon".
- No remote-control build. Both Cores are on Wi-Fi, addressed directly by the noggin service; USB-C only for flashing and as fallback (ADR 0005). The Mech keeps one pack and the Y lead (the pack per shield was dropped, #51).
- The digital model of the Mech is "the model" (folder model/), never "twin".
- We check the licence of anything the Mech adopts (designs, code) before adopting it; dataset and reference licences stay Cansin's.
- The next Mech (#51) is designed clean-room from its requirements; no dimension comes from today's designer-derived parts.
- Cosmetic parts (face plates, shells, anything facing out) are PLA Pure in Milky Pink, Apricot, Pure White or Absolute Black, held to the skeleton by magnets, so a character is a swappable shell set on one shared skeleton; every other part is black PETG.
- Ground truth for today's documents in the model, in order: Cansin's build (photos in docs/references/build-photos, local only; measurements), then our model (parts, MuJoCo, reports, tests). The designer's and vendor's files are credits (`docs/credits.md`) and history (docs/research) only. Planned edits to today's Mech stay in notes until they stabilise; the next Mech is designed in the model, in its own documents beside today's, clean-room: our envelopes of owned hardware and our own new parts, never today's printed parts or their dimensions (#629). Record every conflict with both sources; inference only fills what none settles, marked inferred.
- I can't measure (no calliper): a size my build doesn't settle is a best guess from its behaviour or photos, then the model's nominals, marked inferred.
- Hardware never gates a merge: Core and Link PRs merge on green, and I try them on the physical Mech after.
- PRs merge on the slim gate; everything heavy runs on main, which fixes forward (#696, CONTRIBUTING.md).
- Blender authors every picture of the Mech (README, docs, PR pictures; diagrams are Mermaid in the Markdown); the web viewer draws Blender's glTF with the look Blender writes into it (ADR 0008).
- After a merge that changes the next Mech's look, the main session opens its new pictures and motion for me: the live Pictures page once deployed.
- No real photos in git, the README or the site until staged photos exist; Blender pictures and the viewer stand in, once ADR 0019 lets them.
- Today's Mech is shown nowhere public (site, README, releases, CI artifacts) until the clean-room Mech exists (ADR 0019, #640).
- Sources only in git: CI builds every generated output and the site serves it (ADR 0009).
- README is for contributors: setup, checks, CI. Building and using the Mech live on the site (#279).
- Derived, not listed: whatever the code can deduce (gesture names, servo ports, the eye program's files, Stage and document ids) is read from its one source; a copy that must stay gets a test against it (ADR 0011, test_derived.py).
- Keep everything current: the newest stable release at least 14 days old, security fixes at once; Dependabot's cooldown enforces the 14 days, so review judges a bump on its merits, never rejecting or flagging it for being newer.
- GitHub tools run their advanced, config-as-code setup (a workflow or a `.github/` file), every default off, $0 tiers only.
- Security alerts (code scanning, Dependabot): fix what code can, one PR per tool; dismiss only what waits on time, policy or an upstream release, with the reason, linked to a re-check issue.
- When a dev-cycle step starts, the main session writes its name to `~/.claude/.cycle-step` (the status line shows it); subagents name their steps in their reports.
- Research subagents run the mattpocock-skills:research skill.

## Where things are

- Vocabulary: `GLOSSARY.md`. Architecture decisions: `docs/adr/`. Behaviour table: the site's home (`docs/index.md`) and `docs/use/gestures.md`, built by `macros.py` from the code (numbers in docs: ADR 0009).
- Building the Mech (parts, Stages, wiring, flashing, calibration lessons): `docs/build/`; running it (noggin service, hooks, gestures, tuning): `docs/use/`. The Core's firmware through the vendor's tools only, esptool for read-only queries (ADR 0012).
- The site: Astro Starlight in `site/` (ADR 0013), home `docs/index.md`, nav `site/astro.config.mjs`, vendor and designer names on `docs/credits.md` and the buy list only (test_vocabulary.py).
- The next Mech's skeleton and character shells (planned, #51): `docs/face-design.md`.
- Model pictures (Blender, from MuJoCo's trajectories; look, the panels): `docs/model-notes.md`; `just render`, `just pictures next` (what the site publishes, ADR 0019).
- Web viewer (three.js page at the site's /viewer): GLBs `web/`, page and module `site/src/`, ADR 0008; `just web` builds the GLBs, the site serves the next Mech's alone (ADR 0019); `just site` the whole site.
- Primary-source research (hooks, serial, launchd, eye kinematics): `docs/research/`.
- The designer's PDFs/STLs/configs and the GazeBase cache: `docs/references/` (gitignored, local only).
- Checks and CI: CONTRIBUTING.md. Board: `just flash`, `just start`/`stop`. Tuning: `noggin/noggin set|pose|exercise`.
