REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
MPYC  := $(REPO)/.venv/bin/mpy-cross
BLENDER := /Applications/Blender.app/Contents/MacOS/Blender
NOGGIN := noggin/noggin
# one heavy command (MuJoCo, CoACD, Blender) at a time on this machine, the next waits (#246); no comment after the value, as below
HEAVY := $(PY) scripts/heavy.py
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.plist
LABEL := gui/$(shell id -u)/com.noggin
DOC ?= noggin-eyes
# a Core on USB (the noggin service's PORT_GLOB); no comment after the value: make would keep the spaces before it
USB_PORTS := $(wildcard /dev/cu.usbmodem*)
OURS_SRC := $(sort $(wildcard model/printed/*.py)) model/envelopes.py model/geometry.py model/ours.py uv.lock   # what model/build/ours is built from (CI caches it on the same files)

.PHONY: venv test check check-all sim ours stl step install hooks unhooks start stop status log demo follow wifi interrupt core-info backup-stock mpy flash flash-usb restore-stock render gifs hero pictures trajectories view web site lint fmt mech

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv ours   ## every test, under the heavy lock (CI's model jobs select theirs with -m model)
	$(HEAVY) $(PY) -m pytest -q
lint: venv       ## ruff
	$(PY) -m ruff check
fmt: venv        ## ruff format, in place
	$(PY) -m ruff format
check: venv ours lint  ## CI's code job: the tests not marked model, the viewer's framing (node), lint, formatting, types, wizard syntax, plist validity, hook script syntax
	$(PY) -m pytest -q -m "not model"
	node --test web/frame.test.mjs
	$(PY) -m ruff format --check
	$(PY) -m pyright
	bash -n scripts/setup.sh
	for f in noggin/hook.sh noggin/noggin; do sh -n $$f; done
	$(PY) -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"
check-all: check   ## every test: make check, then the model tests under the heavy lock
	$(HEAVY) $(PY) -m pytest -q -m model
sim: venv ours   ## simulate every document (sub-assemblies + Stage configurations) on our geometry into model/build/reports: placements, fits, beams, electrical and MuJoCo (model/report.py) with each MJCF, then threshold the reports (CI builds them, the site publishes main's: docs/adr/0009)
	$(HEAVY) $(PY) -m model.report $(SIM_DOCS)
	$(PY) -m pytest -q model/test_report.py
ours: venv   ## our printed parts and hardware envelopes as STLs in model/build/ours (what CI simulates and every picture draws); skipped while its sources are unchanged
	@key=$$(shasum $(OURS_SRC) | shasum); if [ "$$(cat model/build/ours/.key 2>/dev/null)" = "$$key" ]; then echo "model/build/ours: up to date"; else $(PY) -m model.ours && echo "$$key" > model/build/ours/.key; fi
stl: venv    ## print-ready STLs of our printed parts (mm, the designer's frames, L and R each) in model/build/stl
	$(PY) -m model.ours stl
step: venv   ## STEP files of every part and envelope, and each Stage as assembled (every horn at 0), in model/build/step (open -a FreeCAD)
	$(PY) -m model.ours step
install: venv hooks start   ## host side: hooks + the noggin service
hooks:
	$(PY) noggin/install_hooks.py
unhooks:
	$(PY) noggin/install_hooks.py --remove
start: stop      ## install + (re)start the noggin service (launchd)
	sed 's|__REPO__|$(REPO)|g' noggin/com.noggin.plist > $(PLIST)
	launchctl bootstrap gui/$(shell id -u) $(PLIST)
stop:            ## stop the noggin service (frees the Link for mpremote); waits until it is really gone
	-launchctl bootout $(LABEL) 2>/dev/null
	@while launchctl print $(LABEL) >/dev/null 2>&1; do sleep 0.2; done
status:
	-launchctl print $(LABEL) | grep -E 'state|pid' | head -3
	-noggin/noggin status
	-tail -5 noggin.log
log:
	tail -f noggin.log
demo:            ## loop every gesture with a 5 s pause, hooks ignored (ARGS=once, or ARGS="bored 2" for one gesture)
	noggin/noggin demo $(ARGS)
follow:          ## back to reacting to Claude Code (the mode after any restart)
	noggin/noggin follow

interrupt: stop  ## drop the Core to its REPL (the stock app ignores mpremote's own Ctrl-C)
	$(PY) eyes/interrupt.py
core-info: interrupt ## what is on the Core right now
	$(MPR) resume exec "import sys, os; print(sys.version); print(os.listdir())"
backup-stock: interrupt   ## copy the stock program off the Core (named entries; cp -r :/ is unreliable)
	mkdir -p eyes/stock-backup
	cd eyes/stock-backup && for f in $$($(MPR) resume exec "import os; print(' '.join(os.listdir()))"); do $(MPR) resume cp -r :$$f . ; done
	ls -R eyes/stock-backup
mpy: venv        ## the eye program as .mpy for the Core's MicroPython (pyproject [tool.noggin]) in eyes/build: what both flashes send
	mkdir -p eyes/build
	$(MPYC) -o eyes/build/eyes.mpy eyes/eyes.py
	$(MPYC) -o eyes/build/gaze_trace.mpy eyes/gaze_trace.py
	$(MPYC) -o eyes/build/wifi.mpy eyes/wifi.py
flash: mpy       ## install the eye program and reboot the Core: over Wi-Fi while its beacon is fresh or no Core is on USB (the noggin service waits for the beacon), else USB (USB=1 forces it)
	@if [ -z "$(USB)" ] && { [ -z "$(USB_PORTS)" ] || $(NOGGIN) status 2>/dev/null | grep -q '^eyes wifi '; }; then $(NOGGIN) flash; else $(MAKE) flash-usb; fi
flash-usb: interrupt mpy ## the cable: the only way boot.py and hmac (micropython-lib, for the Link's tags) change, and the way back from anything Wi-Fi cannot fix
	$(MPR) resume exec "import os; 'flash.trial' in os.listdir() and os.remove('flash.trial')"
	$(MPR) resume mip install hmac
	$(MPR) resume cp eyes/build/eyes.mpy :eyes.mpy
	$(MPR) resume cp eyes/build/gaze_trace.mpy :gaze_trace.mpy
	$(MPR) resume cp eyes/build/wifi.mpy :wifi.mpy
	$(MPR) resume cp eyes/boot.py :boot.py
	$(MPR) resume exec "import os; [os.remove(f) for f in ('eyes.py', 'gaze_trace.py', 'wifi.py') if f in os.listdir()]"  # a .py shadows its .mpy
	$(PY) eyes/interrupt.py reset
wifi: venv       ## add a Wi-Fi network to the Core on USB: the wizard's Join the Wi-Fi step alone (scripts/setup.sh wifi); in a Terminal window (docs/build/flashing.md)
	scripts/setup.sh wifi
restore-stock: interrupt
	cd eyes/stock-backup && for f in *; do $(MPR) resume cp -r $$f : ; done
	$(PY) eyes/interrupt.py reset

view: venv ours     ## a document (DOC=, default noggin-eyes; any stages.DOCS key) in MuJoCo's viewer, from its MJCF (model/mjcf.py)
	$(HEAVY) $(PY) -m model.mjcf $(DOC)
	$(PY) -m mujoco.viewer --mjcf=model/build/mjcf/$(DOC).xml
trajectories: venv ours   ## MuJoCo plays each gesture and the hero on each Stage (TRAJ_DOCS= picks some): every part's world pose per 100 ms frame in model/build/trajectories (a Stage whose files carry its stamp is skipped)
	$(HEAVY) $(PY) -m model.trajectories $(TRAJ_DOCS)
render: venv ours trajectories   ## Blender pictures, each Stage at rest from its trajectories: views, Stage strip, stage 3 exploded (model/build/pictures)
	BLENDER=$(BLENDER) $(HEAVY) $(PY) -m model.render.pictures views
gifs: venv ours trajectories     ## the six gesture GIFs + contact sheets on stage 1, from their trajectories
	BLENDER=$(BLENDER) $(HEAVY) $(PY) -m model.render.pictures gifs
hero: venv ours trajectories     ## the README hero: stage 3 talking, an 8 s loop keyed in model/render/hero.py, from its trajectory
	BLENDER=$(BLENDER) $(HEAVY) $(PY) -m model.render.pictures hero
pictures: venv ours trajectories   ## the README's pictures (model/render/pictures.py SITE) in model/build/images, which the site serves at images/; PARTS= picks some (views, hero or a gesture); SHARD=i/n with one part renders only that shard of its frames, unjoined (the pages workflow, #278)
	BLENDER=$(BLENDER) $(HEAVY) $(PY) -m model.render.pictures $(if $(SHARD),frames $(PARTS) $(SHARD),site $(PARTS))
web: venv ours trajectories   ## the web viewer's site in web/build: the page and Blender's GLB per Stage from its trajectories (docs/adr/0008), then their tests; look with python -m http.server -d web/build
	BLENDER=$(BLENDER) $(HEAVY) $(PY) -m web.build
	$(PY) -m pytest -q web
site: venv       ## the site in site/ (docs/adr/0009): MkDocs builds the docs and the web viewer's page, its GLBs and three.js go beside it in site/viewer once make web built them, the pictures to site/images once make pictures did, the sim reports to site/reports once make sim did; look with python -m http.server -d site
	NO_MKDOCS_2_WARNING=1 $(PY) -m mkdocs build --strict
	[ ! -d web/build ] || cp -R web/build/. site/viewer
	[ ! -d model/build/images ] || cp -R model/build/images site/images
	[ ! -d model/build/reports ] || { cp -R model/build/reports site/reports && cd site/reports && ls *.json *.xml | sed 's|.*|<a href="&">&</a><br>|' > index.html; }

# the Core's MicroPython (pyproject [tool.noggin]); CI caches mech/build on it (no comment after the value, as above)
MICROPYTHON := v1.23.0
mech/build/micropython:   ## the unix port of it and micropython-lib's hmac (what flash-usb's mip gives the Core), for the Mech stand-in
	rm -rf mech/build/src
	git clone -q --depth 1 -b $(MICROPYTHON) https://github.com/micropython/micropython mech/build/src
	$(MAKE) -C mech/build/src/ports/unix submodules
	$(MAKE) -C mech/build/src/ports/unix -j4 FROZEN_MANIFEST= MICROPY_PY_FFI=0 MICROPY_PY_BTREE=0 MICROPY_PY_SSL=0 CFLAGS_EXTRA=-Wno-error   # newer compilers warn where v1.23.0 compiled clean
	mkdir -p mech/build/lib
	cp mech/build/src/lib/micropython-lib/python-stdlib/hmac/hmac.py mech/build/lib/
	cp mech/build/src/ports/unix/build-standard/micropython mech/build/micropython
	rm -rf mech/build/src
mech: venv mech/build/micropython   ## the Mech stand-in: the Core's program on that MicroPython beside the real noggin service, the Link's live checks as tests (mech/)
	$(PY) -m pytest -q mech
