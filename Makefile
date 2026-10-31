REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.plist
LABEL := gui/$(shell id -u)/com.noggin

.PHONY: venv test check model-check model-proxies install hooks unhooks start stop status log interrupt core-info backup-stock flash restore-stock model-eyes model-pan-tilt model-mouth model-parts
DOC ?= noggin-eyes   ## Stage document for model-check: noggin-eyes, noggin-pan-tilt or noggin-mouth

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv
	$(PY) -m pytest -q
check: test       ## everything CI runs: tests, wizard syntax, plist validity, hook script syntax
	bash -n scripts/setup.sh
	for f in noggin/hook.sh noggin/noggin noggin/demo; do sh -n $$f; done
	$(PY) -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"
model-check: venv  ## sweep every horn joint of $(DOC) (Fusion open, MCP on); writes model/build/
	$(PY) model/sweep.py $(DOC)
	$(PY) -m pytest -q model/test_report.py
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
	-tail -5 noggin.log
log:
	tail -f noggin.log

interrupt: stop  ## drop the Core to its REPL (the stock app ignores mpremote's own Ctrl-C)
	$(PY) eyes/interrupt.py
core-info: interrupt ## what is on the Core right now
	$(MPR) resume exec "import sys, os; print(sys.version); print(os.listdir())"
backup-stock: interrupt   ## copy the stock program off the Core (named entries; cp -r :/ is unreliable)
	mkdir -p eyes/stock-backup
	cd eyes/stock-backup && for f in $$($(MPR) resume exec "import os; print(' '.join(os.listdir()))"); do $(MPR) resume cp -r :$$f . ; done
	ls -R eyes/stock-backup
flash: interrupt ## install the eye program and reboot the Core
	$(MPR) resume cp eyes/eyes.py :eyes.py
	$(MPR) resume cp eyes/gaze_trace.py :gaze_trace.py
	$(MPR) resume cp eyes/boot.py :boot.py
	$(PY) eyes/interrupt.py reset
restore-stock: interrupt
	cd eyes/stock-backup && for f in *; do $(MPR) resume cp -r $$f : ; done
	$(PY) eyes/interrupt.py reset

model-proxies:   ## decimated STLs for the sweep (Blender), into model/build/proxies
	/Applications/Blender.app/Contents/MacOS/Blender -b -P model/proxies.py -- docs/references/01-eyes/models docs/references/02-pan-tilt/models docs/references/03-mouth/models model/build/proxies | grep -v '^Blender'
model-parts: venv model-proxies   ## convert every STL/STEP once into the Fusion `parts` folder; skips unchanged sources (FULL=1: reconvert all)
	sed 's/^FULL = False/FULL = $(if $(FULL),True,False)/' model/parts.py | $(PY) scripts/fusion_run.py /dev/stdin
model-eyes: venv model-proxies   ## rebuild the noggin-eyes Fusion design, reusing unchanged parts; saves only on change (FULL=1: empty + reimport)
	sed 's/^FULL = False/FULL = $(if $(FULL),True,False)/' model/eyes.py | $(PY) scripts/fusion_run.py /dev/stdin
model-pan-tilt: venv model-proxies   ## rebuild the noggin-pan-tilt Fusion design the same way
	sed 's/^FULL = False/FULL = $(if $(FULL),True,False)/' model/pan_tilt.py | $(PY) scripts/fusion_run.py /dev/stdin
model-mouth: venv model-proxies   ## rebuild the noggin-mouth Fusion design the same way (WIP: not yet run, #32)
	sed 's/^FULL = False/FULL = $(if $(FULL),True,False)/' model/mouth.py | $(PY) scripts/fusion_run.py /dev/stdin
