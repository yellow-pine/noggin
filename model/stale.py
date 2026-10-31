"""Is the committed sim stale? The documents whose report (model/reports/<doc>-sim.json) no longer matches the inputs
in the repo and the meshes as built now (run.py's stamp; a missing mesh counts as changed). `make sim-if-stale` (CI on
PRs) runs `make sim` only when there is one. Outside the engine on purpose: a file the stamp hashes would stale every
report. Usage: python -m model.stale (prints "fresh", or exits 1 naming the stale documents)."""

import json
import os
import sys

from model.engine import run, stages


def stale():
    out = []
    for doc in sorted(stages.DOCS):
        path = os.path.join(stages.REPO, "model", "reports", f"{doc}-sim.json")
        inputs = json.load(open(path))["inputs"] if os.path.isfile(path) else {"stamp": None, "sources": {}}
        paths = {s: os.path.join(stages.REPO, s) for s in inputs["sources"]}
        now = {s: run.fingerprint(p) if os.path.isfile(p) else None for s, p in paths.items()}
        if inputs["stamp"] != run.stamp(now):
            out.append(doc)
    return out


if __name__ == "__main__":
    docs = stale()
    print(f"stale: {', '.join(docs)}" if docs else "fresh")
    sys.exit(1 if docs else 0)
