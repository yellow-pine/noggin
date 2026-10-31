REPO  := $(abspath .)
PY    := $(REPO)/.venv/bin/python
MPR   := $(REPO)/.venv/bin/mpremote
PLIST := $(HOME)/Library/LaunchAgents/com.noggin.plist
LABEL := gui/$(shell id -u)/com.noggin
# $(call fusion,script[,extra sed]): run a Fusion build script with FULL set from `FULL=1 make ...`
fusion = sed -e 's/^FULL = False/FULL = $(if $(FULL),True,False)/' $(2) $(1) | $(PY) scripts/fusion_run.py /dev/stdin

.PHONY: venv test check sim model-step-meshes install hooks unhooks start stop status log interrupt core-info backup-stock flash restore-stock model-eyes model-base model-stack model-mouth model-stage1 model-stage2 model-stage3 model-parts model-canvases lint fmt

venv:            ## .venv with pyserial, pytest, mpremote
	uv sync -q
test: venv
	$(PY) -m pytest -q
lint: venv       ## ruff
	$(PY) -m ruff check
fmt: venv        ## ruff format, in place
	$(PY) -m ruff format
check: test lint  ## everything CI runs: tests, lint, formatting, types, wizard syntax, plist validity, hook script syntax
	$(PY) -m ruff format --check
	$(PY) -m pyright
	bash -n scripts/setup.sh
	for f in noggin/hook.sh noggin/noggin noggin/demo; do sh -n $$f; done
	$(PY) -c "import plistlib; plistlib.load(open('noggin/com.noggin.plist','rb'))"
sim: venv model/build/steps/horn.stl   ## simulate every document (sub-assemblies + Stage configurations) in Python into model/reports (commit them), then threshold the reports
	$(PY) -m model.engine.run $(SIM_DOCS)
	$(PY) -m pytest -q model/test_report.py
model-step-meshes: ## tessellate the Bambu STEPs once into model/build/steps (cadquery-ocp, ephemeral)
	uv run --with cadquery-ocp python model/engine/step_mesh.py
model/build/steps/horn.stl: model/engine/step_mesh.py
	$(MAKE) model-step-meshes
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

model-canvases: venv   ## show/hide the reference-photo canvases of the active Fusion document
	$(PY) scripts/fusion_run.py model/canvases.py
model-parts: venv   ## convert every STL/STEP once into the Fusion `parts` folder; skips unchanged sources (FULL=1: reconvert all)
	$(call fusion,model/parts.py)
model-eyes: venv   ## rebuild the noggin-eyes Fusion design, reusing unchanged parts; saves only on change (FULL=1: empty + reimport)
	$(call fusion,model/eyes.py)
model-base: venv   ## rebuild the noggin-base Fusion design (base plate + electronics set 1) the same way
	$(call fusion,model/base.py)
model-stack: venv   ## rebuild the noggin-stack Fusion design (the pan-tilt neck + electronics set 2) the same way
	$(call fusion,model/stack.py)
model-mouth: venv   ## rebuild the noggin-mouth Fusion design the same way
	$(call fusion,model/mouth.py)
model-stage1 model-stage2 model-stage3: venv   ## rebuild a Stage document from the saved sub-assemblies (noggin-stage1: base + eyes; 2: + stack; 3: + mouth)
	$(call fusion,model/stage.py,-e 's/^DOC = .*/DOC = "noggin-$(@:model-%=%)"/')
