"""Code Checks' model shards (`make model-shards-list`, #305, #474): N runners, balanced on measured seconds. The units
are the hero's collision sweep, each document (stages.DOCS, picked by its id: pytest -k on the parameter), the rest of
the model tests and make sim; each goes, longest first, to the lightest shard. Their seconds are the CI runs' own
(model/durations.json, pytest-split's --store-durations plus make sim's core-seconds: `make model-durations`), so a new
document needs no workflow edit and no list of names."""

import json
import os
import shlex

from model import stages

N = 3
HERO = "test_hero.py"  # -k on its module, model/render/test_hero.py
SIM = "make sim"  # its key in DURATIONS
DURATIONS = os.path.join(stages.REPO, "model", "durations.json")


def units():
    """{unit: its pytest -k expression}, None for make sim."""
    docs = {d.removeprefix("noggin-"): d for d in stages.DOCS}
    rest = " and ".join(f"not {k}" for k in [HERO, *docs.values()])
    return {"hero": HERO, **docs, "rest": rest, "sim": None}


def seconds(durations):
    """{unit: seconds}: each test's under the unit whose -k picks it (the rest otherwise); an unmeasured unit, the mean."""
    pick = {u: k for u, k in units().items() if k and u != "rest"}
    took = dict.fromkeys(units(), 0.0)
    for test, s in durations.items():
        took["sim" if test == SIM else next((u for u, k in pick.items() if k in test), "rest")] += s
    measured = [s for s in took.values() if s]
    return {u: s or (sum(measured) / len(measured) if measured else 1.0) for u, s in took.items()}


def shards():
    """[{shard, units, tests}]: tests is the shard's pytest arguments (PYTEST_ADDOPTS), empty when it has none."""
    took = seconds(json.load(open(DURATIONS)))
    bins = [[] for _ in range(N)]
    for u in sorted(took, key=lambda u: (-took[u], u)):
        min(bins, key=lambda b: sum(took[x] for x in b)).append(u)
    k = units()
    picks = [[f"({k[u]})" for u in b if k[u]] for b in bins]
    return [
        {"shard": " ".join(b), "units": b, "tests": shlex.join(["-k", " or ".join(p)]) if p else ""}
        for b, p in zip(bins, picks, strict=True)
    ]


if __name__ == "__main__":
    print(json.dumps(shards()))
