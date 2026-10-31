REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.eyesd.plist
LABEL := gui/$(shell id -u)/com.noggin.eyesd

.PHONY: venv test install hooks unhooks daemon stop status log interrupt core-info backup-stock flash restore-stock

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv
	$(PY) -m pytest -q
install: venv hooks daemon   ## host side: hooks + launchd daemon
hooks:
	$(PY) daemon/install_hooks.py
unhooks:
	$(PY) daemon/install_hooks.py --remove
daemon:          ## install + (re)start the launchd Daemon
	sed 's|__REPO__|$(REPO)|g' daemon/com.noggin.eyesd.plist > $(PLIST)
	-launchctl bootout $(LABEL) 2>/dev/null
	launchctl bootstrap gui/$(shell id -u) $(PLIST)
stop:            ## stop the Daemon (frees the Link for mpremote); waits until it is really gone
	-launchctl bootout $(LABEL) 2>/dev/null
	@while launchctl print $(LABEL) >/dev/null 2>&1; do sleep 0.2; done
status:
	-launchctl print $(LABEL) | grep -E 'state|pid' | head -3
	-tail -5 eyesd.log
log:
	tail -f eyesd.log

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
	$(MPR) resume cp eyes/boot.py :boot.py
	$(PY) eyes/interrupt.py reset
restore-stock: interrupt
	cd eyes/stock-backup && for f in *; do $(MPR) resume cp -r $$f : ; done
	$(PY) eyes/interrupt.py reset
