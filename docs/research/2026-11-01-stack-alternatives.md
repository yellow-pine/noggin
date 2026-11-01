# The stack, and the best free alternative for each piece (2026-11-01)

Question (Cansin, 2026-11-01): list every major tech decision, library, service and tool in the repo, categorized, then
check each against the best widely used free alternatives, so we know we use the best available tool for our needs.
Hand-rolled code was audited already (docs/research/2026-10-31-standards-audit.md); this note is about the chosen
tools. Fixed by the hardware or the project, so not up for change: the CyberBrick Core (ESP32-C3) and its vendor
MicroPython build (never reflashed, ADR 0002), Claude Code and its hooks (what the Mech reacts to), macOS on the Mac.

## Inventory

### Mech and the Link
- Core program language: vendor MicroPython 1.23 on the ESP32-C3 (`[tool.noggin]`), gestures on the Core (ADR 0001)
- Deploying to the Core: mpremote over USB, mpy-cross 1.23 `.mpy` bytecode, micropython-lib `hmac` via `mip`
- The Link: signed UDP datagrams (HMAC-SHA256, seq, acks) and UDP beacon discovery over Wi-Fi, USB serial fallback
  (ADR 0005); MQTT/Mosquitto with mutual TLS rejected and parked (`noggin/broker.py`, `noggin/pki.py`)
- Wi-Fi flashing: custom `put`/`commit`/`reboot` over the Link with a boot.py rollback (ADR 0005, #108)
- Mech stand-in for tests: MicroPython unix port built in CI (`mech/`, `mech.yml`)
- Stubs: micropython-esp32-esp32_generic_c3-stubs, micropython-stdlib-stubs (pyright on Core code)

### Mac side (the noggin service)
- CPython 3.12, stdlib only at runtime plus pyserial
- Process supervision: launchd LaunchAgent (`noggin/com.noggin.plist`)
- IPC from hooks: Unix socket, POSIX `sh` hook script (`noggin/hook.sh`), hooks installed into `~/.claude/settings.json`
- Setup wizard: bash (`scripts/setup.sh`), token from `openssl rand`

### The model (CAD, simulation, geometry)
- Parametric CAD: CadQuery (OCCT), STEP/STL export; FreeCAD to open STEP (Fusion 360 retired, ADR 0004)
- Physics: MuJoCo (ADR 0007; own Python engine retired, ADR 0006)
- Convex decomposition: CoACD
- Meshes: trimesh; numerics: NumPy, SciPy
- Electrical simulation: PySpice over ngspice
- Eye-motion data: GazeBase dataset

### Pictures and the web viewer
- Rendering: Blender 5.2 (Eevee, toon look), driven by `bpy` scripts; GIFs (`make render`, `make gifs`)
- Web viewer: three.js 0.186.1 from jsDelivr (GLTFLoader, DRACOLoader, OrbitControls, LineSegments2), glTF/GLB
  exported by Blender, Draco compression (ADR 0008); glTF checked with pygltflib
- Diagrams: Mermaid 11 in Markdown

### Docs and the site
- Static site: MkDocs Material 9.7, mkdocs-same-dir, mkdocs-macros-plugin (numbers from code), pymdownx superfences;
  planned: Astro Starlight
- Hosting: GitHub Pages at yellowpine.com/noggin (ADR 0009: sources only, CI builds outputs)

### Python tooling and quality
- Package and env manager: uv (`uv.lock`)
- Tests: pytest, pytest-xdist; Linter and formatter: Ruff; Types: Pyright (basic)
- Shell checks: `sh -n`, `bash -n`, shellcheck (CI)
- Heavy-job lock: `scripts/heavy.py`

### CI, review and repo automation
- CI: GitHub Actions (check, mech, pages, queue, release, review, skills), actions pinned by SHA, merge queue
- AI review: anthropics/claude-code-action with skills from `skills-lock.json` (mattpocock/skills, ponytail), the
  `skills` CLI, weekly re-pin workflow
- Dependency updates: Dependabot (uv, github-actions)
- Release: tag-triggered GitHub Release of the Core program and wizard
- License: PolyForm Noncommercial 1.0.0

## Research

Sources, all read 2026-11-01: PyPI JSON (`https://pypi.org/pypi/<name>/json`), the npm registry
(`https://registry.npmjs.org/<name>`), the GitHub API (`gh api repos/<owner>/<repo>`, releases, commits), each
project's own docs as linked. "Latest" is the newest release on that registry today. Repo claims are `file:line` on
main at ee47452. The project's pin rule is "newest release at least two weeks old"
(docs/research/2026-11-01-web-viewer.md:5). No device was touched and nothing was installed.

### Worth acting on (ranked)

| # | Item | Verdict | Why, in one line |
|---|---|---|---|
| 1 | The site: Astro Starlight (planned) | **consider**: Starlight is the best fit of the candidates, with two gates for its spec; Docusaurus is the fallback | Every candidate needs custom glue for the numbers; Starlight adds the least weight, but wants a `title` in every page's frontmatter and its own content folder |
| 2 | Parked MQTT broker and PKI (`noggin/broker.py`, `noggin/pki.py`, paho-mqtt, CI's mosquitto) | **consider deleting** | It waits for a Core firmware that can hold TLS, and ADR 0002 forbids changing the firmware, so it can never be switched on; git history keeps it |
| 3 | PySpice 1.5 (electrical model) | **consider** spicelib, or ngspice's CLI directly | No PySpice release since 2021-05-15; we monkeypatch its stderr handling and its library path |
| 4 | Dependabot | **switch** (config only): `cooldown: default-days: 14` on both ecosystems | It puts the two-week rule in the tool; Dependabot's default wait is 3 days |
| 5 | MkDocs Material 9.7.7, while it stays | **switch** to 9.8.0 from 2026-11-07 if Starlight has not landed | 9.8.0 is "primarily a security release" |
| 6 | Workflow security | **consider** zizmor in the code job | A free static check for the workflows that hold `pull-requests: write` and the OAuth secret; low priority |

Everything else: **keep**.

### Decisions (Cansin, 2026-11-01)

1. Site: **Starlight, gated** (spec #331, migration #333). The migration proves both gates first and stops if either
   fails; Docusaurus is the fallback. The viewer becomes an Astro page with three.js from npm (Cansin), not
   `public/viewer/` as suggested below.
2. Parked MQTT broker and PKI: **delete** (broker, PKI, their tests, paho-mqtt, CI's mosquitto); ADR 0005's update
   says so.
3. PySpice: **switch to spicelib now**, in its own PR.
4. Dependabot: **add `cooldown: default-days: 14`** to both entries; the npm entry comes with the site switch.
5. MkDocs Material 9.8.0: **skip**; Starlight replaces it.
6. zizmor: **skip**; revisit if the repo takes outside contributors.
7. Python: **stay on 3.12**; revisit in 2027.

### Inventory: missing items (added by this research)

The Inventory above is left as written (beyond the Starlight line). It misses:

- Node in CI already, run unlocked through `npx`: `@mermaid-js/mermaid-cli@11.17.1` with headless Chrome draws every
  diagram (`test_site.py:76`, `:98`; the AppArmor sysctl at `.github/workflows/check.yml:52` is for that Chrome), and
  `skills@1.7.4` plus `node scripts/verify_skills.mjs` (`.github/workflows/review.yml:24-25`).
- Mermaid is pinned (11.17.2, sha384) and loaded from jsDelivr by `overrides/main.html:6` (`mkdocs.yml:15-17`).
- apt in CI: `libngspice0-dev`, `mosquitto`, `shellcheck` (`check.yml:49`); EGL/Mesa for MuJoCo's offscreen render
  (`check.yml:165`).
- Blender 5.2.2 Linux tarball, sha256-checked and cached (`.github/workflows/pages.yml:65-73`); three.js's Draco
  decoder served by the site, sha256-checked (`web/build.py:23-27`).
- ffmpeg makes the GIFs, contact sheets and Stage strip (`model/render/pictures.py:226-227`).
- `nc -U` in the hook script (`noggin/hook.sh:3`); `plistlib` checks the plist (`Makefile:32`).
- Make is the task runner; `gh` and `jq` in the workflows; `scripts/ci_budget.py` (budget) and
  `scripts/claude_approved.py` (queue gate) are custom glue.
- paho-mqtt is a dev dependency only for the parked broker's test (`pyproject.toml:26`, `noggin/test_broker.py:10`).

### Mech and the Link

- **Core MicroPython 1.23 preview, gestures on the Core**: fixed (ADR 0001, 0002). Out of scope.
- **mpremote**: keep. Locked 1.29.0, the latest (2026-08-24, MIT; https://pypi.org/project/mpremote/). It is
  MicroPython's own host tool; the standards audit kept it (2026-10-31-standards-audit.md:14).
- **mpy-cross 1.23**: keep. Latest is 1.29.0.post2 (https://pypi.org/project/mpy-cross/), but the pin must write
  .mpy 6.3 for the Core (docs/build-notes.md:56-60). No alternative compiler exists.
- **micropython-lib `hmac` via `mip`**: keep. ADR 0005 chose it on the audit's advice (standards-audit.md:59-72).
- **The Link (signed UDP, beacons, USB fallback)**: keep. The audit weighed DTLS, TLS-PSK, mTLS, MQTT, CoAP+OSCORE,
  ESP-NOW and Matter (standards-audit.md:91-105), and the board run of mTLS failed on RAM
  (2026-10-31-core-tls.md:123). Nothing has changed since.
- **MQTT/Mosquitto with mTLS, parked**: consider deleting. `noggin/service.py:9` says "nothing starts it". It can only
  come back with a Core firmware that leaves room for TLS (core-tls.md:123: "A custom firmware with a smaller GC heap
  could change that"). ADR 0002 says the firmware "is never modified". Until then it costs a dev dependency (paho-mqtt
  2.1.0, 2024-04-29; https://pypi.org/project/paho-mqtt/), an apt package in every code job (`check.yml:48-49`), and
  14 tests (`noggin/test_broker.py`, `noggin/test_pki.py`). Decision for Cansin: ADR 0005's update parked it on purpose.
- **Wi-Fi flashing**: keep. The audit found no standard that runs on this build (standards-audit.md:180-192).
- **Mech stand-in (unix port of v1.23.0)**: keep. It builds in about 10 s (2026-11-01-micropython-unix.md:13) and runs
  the Core's real .mpy files. An emulator would need the vendor's firmware image, which is not published and is never
  read off the Core (inferred from ADR 0002).
- **Stubs**: keep. micropython-stubs (Josverl) is the standard source, active (repo pushed 2026-11-01; latest
  1.29.0.post1, https://pypi.org/project/micropython-esp32-esp32_generic_c3-stubs/). Stay on `1.23.*` to match the
  Core.

### Mac side (the noggin service)

- **CPython 3.12**: keep. It gets security fixes only until 2028-10. 3.14 and 3.15 are in bugfix
  (https://peps.python.org/api/release-cycle.json). We use nothing a newer version adds; TLS-PSK (3.13) mattered only
  for the rejected Link options (standards-audit.md:96). A move to 3.14 is open: cadquery-ocp and build123d allow
  `<3.15`.
- **pyserial**: keep. Its last release is 3.5 (2020-11-23; https://pypi.org/project/pyserial/), but the repo is still
  worked on (commits 2026-02-27, https://github.com/pyserial/pyserial). mpremote depends on it too, and no other
  library is widely used for this.
- **launchd LaunchAgent**: keep. It is macOS's service manager. Homebrew's `brew services` writes launchd plists too.
- **Unix socket + `sh`/`nc` hook + settings.json install**: keep. The audit weighed HTTP hooks and a Claude Code
  plugin (standards-audit.md:107-129); the plugin choice is still Cansin's (its Decision 2).
- **Setup wizard in bash, token from `openssl rand`**: keep. Both ship with macOS. Python's `secrets.token_hex` would
  be the same.

### The model (CAD, simulation, geometry)

- **CadQuery**: keep. Latest 2.8.0 (2026-06-21, Apache-2.0; https://pypi.org/project/cadquery/), repo active.
  build123d 0.13.0 (2026-09-21; https://pypi.org/project/build123d/) runs on the same OCP kernel
  (2026-10-31-fusion-throughput.md:47), so moving to it means rewriting every part for no new capability. OpenSCAD
  writes meshes only, no STEP.
- **FreeCAD to open STEP**: keep. It is only a viewer here, not a dependency (`Makefile:42`).
- **MuJoCo**: keep. Latest 3.17.0 (2026-10-22, Apache-2.0; https://pypi.org/project/mujoco/), and that is what we lock.
  ADR 0007 made the choice. PyBullet's last release is 3.2.7 (2025-01-30; https://pypi.org/project/pybullet/), and
  Genesis 1.4.5 (https://pypi.org/project/genesis-world/) targets GPU learning workloads.
- **CoACD**: keep. Latest 1.0.14 (2026-08-28, MIT; https://pypi.org/project/coacd/), repo pushed 2026-09-23. Its
  settings are tuned to our clearances (2026-11-01-coacd-tuning.md). V-HACD (trimesh's backend `vhacdx` 0.1.1,
  https://pypi.org/project/vhacdx/) would need that tuning redone.
- **trimesh, NumPy, SciPy**: keep. All are at the latest release (5.2.0 2026-10-24, 2.5.4 2026-10-10, 1.18.1
  2026-08-21; PyPI).
- **PySpice over ngspice**: consider replacing. Its latest release is still 1.5 (2021-05-15,
  https://pypi.org/project/PySpice/); `master` was last touched 2024-01-26, and the 2026-09 work sits unreleased on
  `devel` (https://github.com/PySpice-org/PySpice/commits/devel). We work around it in two places:
  `model/electrical.py:12-15` sets the library path by hand and `:22-35` monkeypatches `send_char`, because 1.5 fails
  on ngspice 42's solver note. Our use is one DC operating point of about 30 elements (`model/electrical.py:89-114`).
  Options:
  - **spicelib** 1.6.4 (2026-10-04, GPL-3.0; https://pypi.org/project/spicelib/, https://github.com/nunobrum/spicelib).
    It runs ngspice's CLI ("cannot (yet) work with the shared library", README) and parses the output with
    `RawRead`. CI would install `ngspice` instead of `libngspice0-dev`, and the monkeypatch would go.
  - **ngspice's CLI** with our own netlist text: the fewest dependencies, but we would parse the output ourselves,
    which the directive warns against.
  - **InSpice** 1.7.0.7 (https://pypi.org/project/InSpice/): a PySpice fork with 14 stars. Not widely used.
  Act when the electrical model next changes.
- **GazeBase**: data, not a tool. Its licence is out of scope (CLAUDE.md).

### Pictures and the web viewer

- **Blender 5.2, `bpy` scripts**: keep (directive, ADR 0008). 5.2.3 (2026-10-22, web-viewer.md:85) reaches the
  two-week rule on 2026-11-05. The PyPI `bpy` 5.2.3 wheel requires Python `==3.13.*`
  (https://pypi.org/project/bpy/), so it cannot share our 3.12 venv; the tarball stays.
- **ffmpeg (GIFs)**: keep. It is the standard.
- **three.js 0.186.1**: keep. ADR 0008 rejected `<model-viewer>` because it cannot draw the look. Babylon.js 9.33.1
  and PlayCanvas 2.23.3 (npm) are larger engines that add nothing we need. 0.187.0 (2026-10-30) becomes eligible
  2026-11-13.
- **Draco**: keep. Meshopt compression would let an import-map hash cover its decoder (no self-hosted copy), but it
  needs a post-processing step after Blender (e.g. glTF-Transform CLI 4.5.1, npm). Not worth the change.
- **pygltflib**: keep. Its latest is 1.16.5 (2025-07-24; https://pypi.org/project/pygltflib/), and the tests read only
  scene extras and animation names (`web/test_build.py:70-98`). Khronos' `gltf-validator` on npm is 2.0.0-dev.3.10
  (2024-10-22), so it is staler.
- **Mermaid**: keep, pinned (docs/research/2026-11-01-diagrams.md:63-72). Under Starlight see below.

### Docs and the site

**Planned: Astro Starlight** (being specced elsewhere). MkDocs Material's own alternatives are out of scope here.
The site needs: the repo's Markdown as-is (README.md as home, docs/ in place, readable on GitHub); numbers from the
code at build time (today `macros.py`, its Jinja hidden in HTML comments); Mermaid; the three.js viewer on the same
site; GitHub Pages; few dependencies and little CI time.

| | Starlight 0.42.8 (Astro 7.4.4) | Docusaurus 3.10.2 | VitePress 1.6.4 | Hugo 0.169.0 | Zensical 0.0.74 |
|---|---|---|---|---|---|
| Released | 2026-10-30 / 2026-10-28 (npm) | 2026-07-10 (npm) | 2025-08-05; 2.0 still `2.0.0-alpha.21` (npm) | 2026-10-27 (GitHub) | 2026-10-30; 0.1.0 "dependable release line" from 2026-11-05 ([upcoming](https://zensical.org/upcoming-changes/)) |
| Toolchain | Node >= 22.23.4 (astro `engines`) | Node, React | Node, Vue | one Go binary | Python (uv) |
| Repo Markdown in place | `docsLoader()` reads `src/content/docs/` only ([config](https://starlight.astro.build/reference/configuration/)); Astro's `glob()` loader takes any `base` ([loader ref](https://docs.astro.build/en/reference/content-loader-reference/)), but the docs never show it for Starlight's collection (**unverified**) | `docs.path` is configurable; `README.md` names a folder's index page ([create a doc](https://docusaurus.io/docs/create-doc)) | `srcDir` plus `rewrites` map any file to any route ([routing](https://vitepress.dev/guide/routing)) | content mounts (needs a theme, frontmatter titles) | **`docs_dir` can't be `.`**, a "temporary limitation" ([basics](https://zensical.org/docs/setup/basics/)) |
| Page title | frontmatter **`title` required** on every page ([frontmatter](https://starlight.astro.build/reference/frontmatter/)) | not checked | not checked | frontmatter | from the page |
| Numbers from code | remark plugin (`markdown.remarkPlugins`, [Markdown](https://docs.astro.build/en/guides/markdown-content/)) plus a JSON file from Python: custom glue | remark plugin plus JSON: glue | data loaders (`.data.js`, [data loading](https://vitepress.dev/guide/data-loading)); comments still need glue | data files plus shortcodes, which show as text on GitHub | native `macros` ([plugins](https://zensical.org/compatibility/plugins/)), but its table lists no `j2_*` delimiters, which our hidden Jinja needs (**unverified**) |
| Mermaid | not built in; community `astro-mermaid` 2.2.0, client-side ([plugins](https://starlight.astro.build/resources/plugins/)) | official `@docusaurus/theme-mermaid` ([diagrams](https://docusaurus.io/docs/markdown-features/diagrams)) | community `vitepress-plugin-mermaid` 2.0.17, 2024-09-24 | code-block render hook ([docs](https://gohugo.io/render-hooks/code-blocks/)) | native ([diagrams](https://zensical.org/docs/authoring/diagrams/)) |
| Search | Pagefind built in ([search](https://starlight.astro.build/guides/site-search/)) | plugin | built in | theme | built in |

**Verdict: Starlight, with two gates its spec must clear.** If either gate fails, the fallback is Docusaurus.

- **Gate 1:** a `glob()` loader with `base: "."` must feed Starlight's `docs` collection, so README.md and docs/
  stay where they are.
- **Gate 2:** every page must carry a frontmatter `title`. GitHub shows frontmatter as a table at the top (inferred,
  not checked here), and Starlight prints the title as the page heading, so each file's own `# H1` would show twice
  (inferred from the frontmatter docs: "displayed at the top of the page").
- **The rivals:**
  - Zensical is the one candidate with no new toolchain, but today it cannot build from the repo root.
  - VitePress has had no stable release in 15 months.
  - Hugo puts its shortcodes in the Markdown, where GitHub shows them as text.
  - Docusaurus answers both of Starlight's gates (README as index, configurable docs path, official Mermaid), at the
    cost of React and a heavier build (not measured).

**What Starlight brings to the rest of the stack:**

- **Node next to uv.**
  - Add `package.json` and `package-lock.json` (a lockfile, so a source under ADR 0009).
  - CI gets `actions/setup-node`, pinned by SHA, and `npm ci`. withastro/action exists
    ([deploy to GitHub](https://docs.astro.build/en/guides/deploy/github/)), but our pinned
    upload-pages-artifact/deploy-pages already do its job.
  - Dependabot gets an `npm` entry; `cooldown` supports npm, uv and GitHub Actions
    ([options](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/dependabot-options-reference#cooldown)).
  - A plus: the `npx` pins we have today (mermaid-cli, skills) can move into the lockfile.
- **Numbers from code.** Astro cannot import Python. `macros.py` becomes a step that writes JSON before
  `astro build`, plus a small remark plugin that swaps each hidden `<!--{{ name }}-->` for its value. The
  GitHub-side check in test_site.py stays as it is.
- **Mermaid.**
  - astro-mermaid bundles Mermaid from npm, so the lockfile pins it in place of the jsDelivr URL with sha384
    (`overrides/main.html:6`).
  - test_site.py's mermaid-cli must then take its version from the lockfile.
  - GitHub draws with Mermaid 12 regardless (diagrams.md:23).
- **Viewer.** Copy `web/build` into Astro's `public/viewer/`, whose files are copied unprocessed
  ([project structure](https://docs.astro.build/en/basics/project-structure/)), or keep copying into the output after
  the build as `Makefile:112` does now. Set `site` and `base: "/noggin"`.
- **Leaving the dev group:** mkdocs-material, mkdocs-same-dir, mkdocs-macros-plugin (`pyproject.toml:28-31`).
- **Until then:** Material 9.8.0 (2026-10-24) is "primarily a security release", and Material reaches end of life on
  2027-05-05 ([release](https://github.com/squidfunk/mkdocs-material/releases/tag/9.8.0)). We pin 9.7.7
  (`pyproject.toml:28`); move to 9.8.0 from 2026-11-07.

**Hosting on GitHub Pages**: keep. It is free and holds the custom domain. ADR 0009 rejected Netlify and Vercel.

### Python tooling and quality

- **uv**: keep. Latest 0.13.6 (2026-10-27; https://pypi.org/project/uv/).
- **pytest, pytest-xdist**: keep. Latest are 9.2.0 and 3.8.0; xdist was sized in 2026-11-01-ci-budget.md.
- **Ruff**: keep. 0.17.3 is the latest and the one we lock.
- **Pyright (basic)**: keep. The alternatives:
  - ty is still 0.0.95 (2026-10-29; https://pypi.org/project/ty/).
  - pyrefly 1.4.0 is stable (2026-10-15; https://pypi.org/project/pyrefly/), but a switch would only re-triage
    findings.
  - mypy 2.4.1 is slower and is not what we run.
- **shellcheck, `sh -n`, `bash -n`**: keep.
- **`scripts/heavy.py`**: keep. It is `fcntl.flock` from the stdlib (`scripts/heavy.py:13-21`), the standard lock.

### CI, review and repo automation

- **GitHub Actions, SHA pins, merge queue**: keep. Pinning by SHA is GitHub's own hardening advice
  (standards-audit.md:42-47). Optional: zizmor v1.31.1 (2026-10-15, MIT; https://github.com/zizmorcore/zizmor), a
  static checker for workflow security. It would add one more tool for workflows that already take `pull_request`
  only from the same repo (`review.yml:14`).
- **claude-code-action**: keep. We pin v1.0.266, the newest tag (`review.yml:50`; `gh api
  repos/anthropics/claude-code-action/tags`). Managed Code Review is Team/Enterprise only, so paid
  (2026-10-31-claude-code-action.md:23).
- **`skills` CLI**: keep. 1.7.4 is the latest (2026-10-19, npm); the lock is verified by `scripts/verify_skills.mjs`.
- **Dependabot**: keep, and add `cooldown: {default-days: 14}` to both entries (`.github/dependabot.yml:3-10`).
  Dependabot's default cooldown is 3 days, and `default-days` is supported for uv and GitHub Actions (options page
  above). Renovate (free, AGPL-3.0; https://github.com/renovatebot/renovate) could bump the hand-pinned CDN and
  tarball versions with regex managers. It cannot recompute their sha384/sha256, though, so those bumps stay manual
  either way.
- **Release via `gh release create`**: keep. It is preinstalled and needs no third-party action (`release.yml:16-17`).
- **License (PolyForm Noncommercial)**: not a tool; Cansin's choice.

### Not verified

- Whether Starlight accepts a non-`docsLoader` `glob()` loader for its `docs` collection, and whether a page's own H1
  shows twice next to the frontmatter title.
- Whether Zensical's `macros` honours `j2_*` delimiters.
- Docusaurus's and VitePress's titles from the first H1.
- Docusaurus's build time against Starlight's.
- The ngspice CLI output format for a spicelib port.
