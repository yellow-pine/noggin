# noggin's recipes (docs/adr/0016): `just --list` shows them with their comments. Variables go before the recipe
# (just BLENDER=blender pictures), a recipe's own arguments after it (just view noggin-neck).

# a variable is evaluated only when a recipe uses it: PROGRAM needs the venv, LABEL runs id
set lazy

REPO := justfile_directory()
BIN := REPO / ".venv/bin"
PY := BIN / "python"
MPR := BIN / "mpremote"
MPYC := BIN / "mpy-cross"
BLENDER := "/Applications/Blender.app/Contents/MacOS/Blender"
NOGGIN := "noggin/noggin"
# one heavy command (MuJoCo, CoACD, Blender) at a time on this machine, the next waits (#246); the recipes that take
# it are in the heavy group, which .claude/settings.json's deny list keeps for CI
HEAVY := PY + " scripts/heavy.py"
PLIST := home_directory() / "Library/LaunchAgents/com.noggin.plist"
LABEL := "gui/" + `id -u` + "/com.noggin"
# the eye program's files (noggin/core.py); PY word-splits, so just PY="python3 -S" mpy-list works
_program := shell('$1 -m noggin.core', PY)
PROGRAM := if _program == "" { error("noggin/core.py listed no eye program") } else { _program }
# a Core on USB (the noggin service's PORT_GLOB)
PORTS := "/dev/cu.usbmodem*"
# just gx10's ssh host and the paths it copies back (space-separated, repo-relative)
GX10 := "gx10"
FETCH := ""
# which way just flash goes: Wi-Fi while the eyes Core's beacon is fresh or no Core is on USB, else USB
FLASH_VIA := shell('if ls $1 >/dev/null 2>&1 && ! $2 status 2>/dev/null | grep -q "^eyes wifi "; then echo usb; else echo wifi; fi', PORTS, NOGGIN)
# the Core's MicroPython (pyproject [tool.noggin]): flash-usb's hmac and the stand-in build from it, CI caches
# mech/build on it (checks.yml reads this line)
MICROPYTHON := "v1.23.0"

# .venv with pyserial, pytest, mpremote and just; git runs .githooks (pre-push: just lint)
venv:
    uv sync -q
    git config core.hooksPath .githooks

# every test, under the heavy lock (CI's model jobs select theirs with -m model)
[group('heavy')]
test: venv ours
    {{HEAVY}} {{PY}} -m pytest -q

# ruff (lint and format) and pyright: the one local check, .githooks/pre-push runs it (#714)
lint: venv
    {{PY}} -m ruff check
    {{PY}} -m ruff format --check
    {{PY}} -m pyright

# ruff format, in place
fmt: venv
    {{PY}} -m ruff format

# delete the local branches whose PR merged or closed, and their clean worktrees (gh-poi, installed on first use)
worktrees-clean:
    gh extension list | grep -q seachicken/gh-poi || gh extension install seachicken/gh-poi
    gh poi --state closed

# the PR gate's Code job (#714): just lint and the tests not marked model, no CadQuery build
check-light: venv lint
    {{PY}} -m pytest -q -n auto -m "not model"

# just ours, then the pytest arguments given, in CI's base image as main has it (Linux and its OCCT, where macOS passes parts CI fails: #737, #772), its venv synced to this uv.lock, the repo mounted and its Linux model/build a volume the run deletes (parallel worktrees never share one): a model/ change's affected tests before its push (just linux-test model/printed/test_bone.py)
[positional-arguments]
linux-test +args:
    docker run --rm --pull always --platform linux/amd64 --user root -v "{{REPO}}:{{REPO}}" -v "{{REPO}}/model/build" -w "{{REPO}}" -e UV_PROJECT_ENVIRONMENT=/opt/uv/venv -e PYTHONDONTWRITEBYTECODE=1 ghcr.io/yellow-pine/noggin-ci-base:main sh -c 'uv sync -q --frozen && /opt/uv/venv/bin/just --no-deps BIN=/opt/uv/venv/bin ours && /opt/uv/venv/bin/python -m pytest -q -p no:cacheprovider "$@"' sh "$@"

# the command given, on Cansin's GX10 (ssh host gx10, #888) for a heavy Python job (sim, CoACD, every test; not Blender: no Linux ARM64 build): pushes this branch's commits, checks them out in ~/noggin there (cloned on first use), uv syncs, streams the output, then scps FETCH's paths back (just FETCH="model/build/reports" gx10 uv run just sim)
[positional-arguments]
gx10 +args:
    #!/usr/bin/env bash
    set -euo pipefail
    ssh -o ConnectTimeout=5 -o BatchMode=yes {{GX10}} true 2>/dev/null || { echo "gx10: {{GX10}} is unreachable; run light checks here and leave the rest to CI" >&2; exit 1; }
    branch=$(git branch --show-current)
    [ -n "$branch" ] || { echo "gx10: check out a branch first (it runs what is pushed)" >&2; exit 1; }
    git push -q origin "$branch"
    # flock: one run at a time holds the one clone, so a parallel agent's checkout never swaps the files under a running job
    ssh {{GX10}} "set -e; export PATH=\$HOME/.local/bin:\$PATH; exec 9>noggin.lock; flock -n 9 || { echo 'gx10: another run holds the GX10, waiting' >&2; flock 9; };[ -d noggin ] || git clone -q https://github.com/yellow-pine/noggin.git; cd noggin; git fetch -q origin $(printf %q "$branch"); git checkout -qf --detach FETCH_HEAD; uv sync -q; $(printf '%q ' "$@")"
    for f in {{FETCH}}; do mkdir -p "$(dirname "$f")"; scp -rq "{{GX10}}:noggin/$f" "$(dirname "$f")/"; done

# main's Code job: just check-light, the workflows (actionlint; zizmor, offline and here alone), the CI images' Dockerfiles (hadolint), wizard and hook script syntax (here alone), plist validity (the site's own tests: npm --prefix site test, Checks)
[group('heavy')]
check: check-light
    {{BIN}}/actionlint -shellcheck= -pyflakes=   # without the shellcheck CI's image has and a Mac may not: one result everywhere
    [ -n "${CI:-}" ] || {{BIN}}/zizmor -q --offline .   # CI's Code job runs it online, and shellcheck, which parses the scripts below (#732)
    {{BIN}}/hadolint --ignore DL3008 --ignore DL4006 --ignore DL3066 ci/*.Dockerfile   # apt takes what the digest-pinned base's archive has (it drops old versions), and gh GitHub CLI's repo's newest (ADR 0012); the only pipes are echo into sha256sum and printf into sort; USER runner is uid 1001 (useradd)
    [ -n "${CI:-}" ] || bash -n scripts/setup.sh
    [ -n "${CI:-}" ] || for f in noggin/hook.sh noggin/noggin; do sh -n $f || exit 1; done
    {{PY}} -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"

# every test: just check, then the model tests under the heavy lock
[group('heavy')]
check-all: check
    {{HEAVY}} {{PY}} -m pytest -q -m model

# simulate every document physics runs on (geometry.SIMULATED, the mechanical ones: #809), or the ones named, on our geometry into model/build/reports: the eye gimbal, the neck, the head variant, electrical and MuJoCo (model/report.py) with each MJCF, then threshold the reports (CI builds them, the site publishes main's: docs/adr/0009); SIM_PART=i/n measures part i of n into model/build/sim-part-<i>-of-<n> instead, which just sim-merge joins
[group('heavy')]
sim *docs: venv ours
    {{HEAVY}} {{PY}} -m model.report {{docs}}
    {{PY}} -m pytest -q model/test_report.py

# the sim's parts (SIM_PART, model/build/sim-part-*) merged into model/build/reports, then thresholded as just sim does (Checks' Sim job, #809)
sim-merge: venv
    {{PY}} -m model.report --merge
    {{PY}} -m pytest -q model/test_report.py

# our printed parts and hardware envelopes as STLs in model/build/ours (what CI simulates and every picture draws); skipped while its sources are unchanged: model/ours.py and what it imports (scripts/inputs.py), which CI's parts cache key covers (test_derived.py)
ours: venv
    @src=$({{PY}} scripts/inputs.py model/ours.py) && key=$(shasum $src uv.lock | shasum) && if [ "$(cat model/build/ours/.key 2>/dev/null)" = "$key" ]; then echo "model/build/ours: up to date"; else {{PY}} -m model.ours && echo "$key" > model/build/ours/.key; fi

# print-ready STLs of our printed parts (mm, the designer's frames, L and R each) and the clearance coupon in model/build/stl
stl: venv
    {{PY}} -m model.ours stl

# STEP files of every part and envelope, and each document as assembled (every horn at 0), in model/build/step (open -a FreeCAD)
step: venv
    {{PY}} -m model.ours step

# host side: hooks + the noggin service
install: venv hooks start

# add noggin's hooks to ~/.claude/settings.json
hooks:
    {{PY}} noggin/install_hooks.py

# take noggin's hooks out of ~/.claude/settings.json
unhooks:
    {{PY}} noggin/install_hooks.py --remove

# install + (re)start the noggin service (launchd)
start: stop
    sed 's|__REPO__|{{REPO}}|g' noggin/com.noggin.plist > {{PLIST}}
    launchctl bootstrap gui/$(id -u) {{PLIST}}

# stop the noggin service (frees the Link for mpremote); waits until it is really gone
stop:
    -launchctl bootout {{LABEL}} 2>/dev/null
    @while launchctl print {{LABEL}} >/dev/null 2>&1; do sleep 0.2; done

# the noggin service's launchd state, its status and its last log lines
status:
    -launchctl print {{LABEL}} | grep -E 'state|pid' | head -3
    -noggin/noggin status
    -tail -5 noggin.log

# follow noggin.log
log:
    tail -f noggin.log

# loop every gesture with a 5 s pause, hooks ignored (just demo once, or just demo bored 2 for one gesture)
demo *args:
    {{NOGGIN}} demo {{args}}

# back to reacting to Claude Code (the mode after any restart)
follow:
    {{NOGGIN}} follow

# drop the Core to its REPL (the stock app ignores mpremote's own Ctrl-C)
interrupt: stop
    {{PY}} eyes/interrupt.py

# what is on the Core right now
core-info: interrupt
    {{MPR}} resume exec "import sys, os; print(sys.version); print(os.listdir())"

# copy the stock program off the Core (named entries; cp -r :/ is unreliable)
backup-stock: interrupt
    mkdir -p eyes/stock-backup
    cd eyes/stock-backup && for f in $({{MPR}} resume exec "import os; print(' '.join(os.listdir()))"); do {{MPR}} resume cp -r :$f . || exit 1; done
    ls -R eyes/stock-backup

# the eye program's files: what eyes/boot.py imports from eyes/ (noggin/core.py; just PY=python3 mpy-list without the venv)
mpy-list:
    @echo {{PROGRAM}}

# the eye program as .mpy for the Core's MicroPython (pyproject [tool.noggin]) in eyes/build, stamped with the repo's version and commit (stamp.mpy, which its beacon reports): what both flashes send
mpy: venv
    mkdir -p eyes/build
    {{PY}} -m noggin.core stamp > eyes/build/stamp.py
    {{replace_regex(PROGRAM, 'eyes/(\w+)\.py', MPYC + ' -o eyes/build/${1}.mpy eyes/${1}.py &&')}} true
    {{MPYC}} -o eyes/build/stamp.mpy eyes/build/stamp.py

# install the eye program and reboot the Core: over Wi-Fi while its beacon is fresh or no Core is on USB (the noggin service waits for the beacon), else USB (just flash-usb forces it)
flash: mpy
    {{ if FLASH_VIA == "usb" { just_executable() + " flash-usb" } else { NOGGIN + " flash" } }}

# the cable: the only way boot.py and hmac (micropython-lib, for the Link's tags) change, and the way back from anything Wi-Fi cannot fix
flash-usb: interrupt mpy
    {{MPR}} resume exec "import os; 'flash.trial' in os.listdir() and os.remove('flash.trial')"
    {{MPR}} resume mip install github:micropython/micropython-lib/python-stdlib/hmac/hmac.py@{{MICROPYTHON}}   # the stand-in's hmac: micropython-lib's tag of the Core's MicroPython
    {{replace_regex(PROGRAM + ' eyes/stamp.py', 'eyes/(\w+)\.py', MPR + ' resume cp eyes/build/${1}.mpy :${1}.mpy &&')}} true
    {{MPR}} resume cp eyes/boot.py :boot.py
    {{MPR}} resume exec "import os; [os.remove(f) for f in '{{replace(PROGRAM, 'eyes/', '')}} stamp.py'.split() if f in os.listdir()]"  # a .py shadows its .mpy
    {{PY}} eyes/interrupt.py reset

# both Cores on the Mech, each flashed over USB and Wi-Fi, then probed over Wi-Fi with the cable in, with it out and after the Mech was off: asks you to plug, unplug and switch, appends the results to docs/build/live-check.md (#29)
live-check: venv
    {{PY}} -m noggin.live_check

# add a Wi-Fi network to the Core on USB: the wizard's Join the Wi-Fi step alone (scripts/setup.sh wifi); in a Terminal window (docs/build/flashing.md)
wifi: venv
    scripts/setup.sh wifi

# put the stock remote-control program (eyes/stock-backup) back on the Core
restore-stock: interrupt
    cd eyes/stock-backup && for f in *; do {{MPR}} resume cp -r $f : || exit 1; done
    {{PY}} eyes/interrupt.py reset

# a document (default next-mech-back-mechanical, which physics runs on: #809; any stages.DOCS key) in MuJoCo's viewer, from its MJCF (model/mjcf.py)
[group('heavy')]
view doc="next-mech-back-mechanical": venv ours
    {{HEAVY}} {{PY}} -m model.mjcf {{doc}}
    {{PY}} -m mujoco.viewer --mjcf=model/build/mjcf/{{doc}}.xml

# MuJoCo plays each gesture, Rest and the next hero on each of the next Mech's documents, or on the documents named (next: all of them; or in TRAJ_DOCS): every part's world pose per 100 ms frame in model/build/trajectories (a document whose files carry its stamp is skipped)
[group('heavy')]
trajectories *docs=env("TRAJ_DOCS", ""): venv ours
    {{HEAVY}} {{PY}} -m model.trajectories {{docs}}

# Blender pictures, each of the next Mech's documents at rest from its trajectories: the panels (model/build/pictures)
[group('heavy')]
render: venv ours trajectories
    BLENDER={{BLENDER}} {{HEAVY}} {{PY}} -m model.render.pictures views

# the site's pictures (model/render/pictures.py published) in model/build/images: the next Mech's panels and a picture per part, stills alone (Checks' Render shards run `just pictures next`, each its share by PICTURES_SHARD, balanced on model/durations.json, #649, #770, #839)
[group('heavy')]
pictures *what: venv ours trajectories
    BLENDER={{BLENDER}} {{HEAVY}} {{PY}} -m model.render.pictures site {{what}}

# the model tests' and just mech's eight shards, balanced on model/durations.json, as JSON (Checks' model matrix, #305, #474, #496; MODEL=false or MECH=false leaves those out)
model-shards-list: venv
    @{{PY}} -m model.shards

# model/durations.json from a Checks run's measured seconds (its durations-* artifacts): just model-durations <run id>
model-durations run:
    @d=$(mktemp -d) && gh run download {{run}} -p 'durations-*' -D $d && jq -S -s '(.[0] | with_entries(select(.key | test("^(just|render) ")))) + (.[1:] | add)' model/durations.json $d/*/*.json > $d/all.json && mv $d/all.json model/durations.json; rm -rf $d

# the web viewer's GLBs in web/build, Blender's per next Mech document (or the documents named; next: all of them, the ones the site serves, #649) from their trajectories (docs/adr/0008), then their tests; look with just site
[group('heavy')]
web *docs: venv ours trajectories
    BLENDER={{BLENDER}} {{HEAVY}} {{PY}} -m web.build web/build {{docs}}
    {{PY}} -m pytest -q web

# the site in site/dist (docs/adr/0009, 0013): the numbers from the code (macros.py), then Astro Starlight builds the docs and the viewer's page; the next Mech's pictures and GLB (the next-* ones, never today's: docs/adr/0019) go to site/dist/images and viewer once just pictures next and just web made them, the sim reports to site/dist/reports once just sim did; look with npm --prefix site run preview, check with npm --prefix site test
site: venv && site-reports
    {{PY}} -m macros
    cd site && npm ci --ignore-scripts --no-audit --no-fund && npm run build
    ! ls model/build/images/next-* >/dev/null 2>&1 || { mkdir -p site/dist/images && cp model/build/images/next-* site/dist/images/; }
    ! ls web/build/next-*.glb >/dev/null 2>&1 || cp web/build/next-*.glb site/dist/viewer/

# the sim reports (model/build/reports, once just sim made them) into the built site's site/dist/reports with an index; Checks' Deploy reruns it on main's site with the reports Checks saved
site-reports:
    scripts/site_reports.sh

# the unix port of the Core's MicroPython and micropython-lib's hmac (flash-usb's mip gives the Core the same tag's), for the Mech stand-in; built once, kept in mech/build
micropython:
    #!/usr/bin/env bash
    set -euo pipefail
    [ ! -x mech/build/micropython ] || exit 0
    rm -rf mech/build/src
    git clone -q --depth 1 -b {{MICROPYTHON}} https://github.com/micropython/micropython mech/build/src
    make -C mech/build/src/ports/unix submodules   # MicroPython's own Makefile
    make -C mech/build/src/ports/unix -j4 FROZEN_MANIFEST= MICROPY_PY_FFI=0 MICROPY_PY_BTREE=0 MICROPY_PY_SSL=0 CFLAGS_EXTRA=-Wno-error   # newer compilers warn where v1.23.0 compiled clean
    mkdir -p mech/build/lib
    cp mech/build/src/lib/micropython-lib/python-stdlib/hmac/hmac.py mech/build/lib/
    cp mech/build/src/ports/unix/build-standard/micropython mech/build/micropython
    rm -rf mech/build/src

# the Mech stand-in: the Core's program on that MicroPython beside the real noggin service, the Link's live checks as tests (mech/)
mech: venv micropython
    {{PY}} -m pytest -q mech
