REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
MPYC  := $(REPO)/.venv/bin/mpy-cross
BLENDER := /Applications/Blender.app/Contents/MacOS/Blender
NOGGIN := noggin/noggin
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.plist
LABEL := gui/$(shell id -u)/com.noggin
DOC ?= noggin-eyes
OURS_SRC := $(sort $(wildcard model/printed/*.py)) model/envelopes.py model/geometry.py model/ours.py uv.lock   # what model/build/ours is built from (CI caches it on the same files)

.PHONY: venv test check sim sim-if-stale ours stl step install hooks unhooks start stop status log demo follow interrupt core-info backup-stock mpy flash flash-usb restore-stock render gifs view lint fmt

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv ours
	$(PY) -m pytest -q
lint: venv       ## ruff
	$(PY) -m ruff check
fmt: venv        ## ruff format, in place
	$(PY) -m ruff format
check: test lint  ## everything CI runs: tests, lint, formatting, types, wizard syntax, plist validity, hook script syntax
	$(PY) -m ruff format --check
	$(PY) -m pyright
	bash -n scripts/setup.sh
	for f in noggin/hook.sh noggin/noggin; do sh -n $$f; done
	$(PY) -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"
sim: venv ours   ## simulate every document (sub-assemblies + Stage configurations) on our geometry in Python into model/reports (commit them), then threshold the reports
	$(PY) -m model.engine.run $(SIM_DOCS)
	$(PY) -m pytest -q model/test_report.py
sim-if-stale: venv ours   ## make sim unless every committed report still matches the inputs and our meshes as built now (CI on PRs)
	$(PY) -m model.stale || $(MAKE) sim
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
flash: mpy       ## install the eye program and reboot the Core: over Wi-Fi while its beacon is fresh, else USB (USB=1 forces it)
	@if [ -z "$(USB)" ] && $(NOGGIN) status 2>/dev/null | grep -q '^eyes wifi '; then $(NOGGIN) flash; else $(MAKE) flash-usb; fi
flash-usb: interrupt mpy ## the cable: the only way boot.py and hmac (micropython-lib, for the Link's tags) change, and the way back from anything Wi-Fi cannot fix
	$(MPR) resume exec "import os; 'flash.trial' in os.listdir() and os.remove('flash.trial')"
	$(MPR) resume mip install hmac
	$(MPR) resume cp eyes/build/eyes.mpy :eyes.mpy
	$(MPR) resume cp eyes/build/gaze_trace.mpy :gaze_trace.mpy
	$(MPR) resume cp eyes/build/wifi.mpy :wifi.mpy
	$(MPR) resume cp eyes/boot.py :boot.py
	$(MPR) resume exec "import os; [os.remove(f) for f in ('eyes.py', 'gaze_trace.py', 'wifi.py') if f in os.listdir()]"  # a .py shadows its .mpy
	$(PY) eyes/interrupt.py reset
restore-stock: interrupt
	cd eyes/stock-backup && for f in *; do $(MPR) resume cp -r $$f : ; done
	$(PY) eyes/interrupt.py reset

view: venv ours     ## a document (DOC=, default noggin-eyes; any stages.DOCS key) in MuJoCo's viewer, from its MJCF (model/mjcf.py)
	$(PY) -m model.mjcf $(DOC)
	$(PY) -m mujoco.viewer --mjcf=model/build/mjcf/$(DOC).xml
render: venv ours   ## Blender pictures from the engine's poses: views, hero, Stage strip (model/build/pictures)
	BLENDER=$(BLENDER) $(PY) -m model.render.pictures views
gifs: venv ours     ## the six gesture GIFs + contact sheets on stage 1, from the Core program's commands
	BLENDER=$(BLENDER) $(PY) -m model.render.pictures gifs
