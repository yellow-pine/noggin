REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.plist
LABEL := gui/$(shell id -u)/com.noggin

.PHONY: venv test check twin-check twin-proxies install hooks unhooks start stop status log interrupt core-info backup-stock flash restore-stock twin-eyes

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv
	$(PY) -m pytest -q
check: test       ## everything CI runs: tests, wizard syntax, plist validity, hook script syntax
	bash -n scripts/setup.sh
	for f in noggin/hook.sh noggin/noggin noggin/demo; do sh -n $$f; done
	$(PY) -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"
twin-check: venv  ## sweep every horn joint of the DOC named in twin/check.py (Fusion open, MCP on); writes twin/build/
	$(PY) twin/sweep.py
	$(PY) -m pytest -q twin/test_report.py
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

twin-proxies:   ## decimated STLs for the sweep (Blender), into twin/build/proxies
	/Applications/Blender.app/Contents/MacOS/Blender -b -P twin/proxies.py -- docs/references/01-eyes/models docs/references/02-pan-tilt/models docs/references/03-mouth/models twin/build/proxies | grep -v '^Blender'
twin-eyes: venv twin-proxies   ## rebuild the noggin-eyes Fusion design, reusing unchanged parts; saves only on change (FULL=1: empty + reimport)
	sed 's/^FULL = False/FULL = $(if $(FULL),True,False)/' twin/eyes.py | $(PY) scripts/fusion_run.py /dev/stdin
