REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.eyesd.plist
LABEL := gui/$(shell id -u)/com.noggin.eyesd

.PHONY: venv test install hooks unhooks daemon stop status log board-info backup-stock flash restore-stock

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv
	$(PY) -m pytest -q
install: venv hooks daemon   ## host side: hooks + launchd daemon
hooks:
	$(PY) daemon/install_hooks.py
unhooks:
	$(PY) daemon/install_hooks.py --remove
daemon:          ## install + (re)start the launchd agent
	sed 's|__REPO__|$(REPO)|g' daemon/com.noggin.eyesd.plist > $(PLIST)
	-launchctl bootout $(LABEL) 2>/dev/null
	launchctl bootstrap gui/$(shell id -u) $(PLIST)
stop:            ## stop the daemon (frees the USB port for mpremote)
	-launchctl bootout $(LABEL) 2>/dev/null
status:
	-launchctl print $(LABEL) | grep -E 'state|pid' | head -3
	-tail -5 eyesd.log
log:
	tail -f eyesd.log

board-info: stop ## what is on the Core right now
	$(MPR) exec "import sys, os; print(sys.version); print(sys.implementation); print(os.listdir())"
backup-stock: stop   ## copy the stock program off the Core (named entries; cp -r :/ is unreliable)
	mkdir -p eyes/stock-backup
	cd eyes/stock-backup && for f in $$($(MPR) exec "import os; print(' '.join(os.listdir()))"); do $(MPR) cp -r :$$f . ; done
	ls -R eyes/stock-backup
flash: stop      ## install the eye program and reboot the Core
	$(MPR) cp eyes/eyes.py :eyes.py
	$(MPR) cp eyes/boot.py :boot.py
	$(MPR) soft-reset
restore-stock: stop
	cd eyes/stock-backup && for f in *; do $(MPR) cp -r $$f : ; done
	$(MPR) soft-reset
