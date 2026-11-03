"""Checks' model shards (`just model-shards-list`, #305, #474, #496): N runners, balanced on measured seconds. The units
are each document (stages.DOCS, picked by its id: pytest -k on the parameter), the rest of the model tests, each of just
sim's parts (SIM_PART=i/n, which Checks' Sim job merges, #809) and just mech (the Mech stand-in); each goes, longest
first, to the lightest shard. Their seconds are the CI runs' own (model/durations.json, pytest-split's
--store-durations plus each sim part's and just mech's core-seconds: `just model-durations`), so a new document needs no
workflow edit and no list of names. MODEL=false or MECH=false (the Changes job's filters) leaves that group's units out,
SIM=false (its reports cached) the sim's."""

import json
import os
import shlex

from model import stages

N = 4  # runners (#496)
SIM = [f"sim {i}/3" for i in range(3)]  # just sim's parts, one a runner (#809)
JUST = {u: f"just {u}" for u in SIM} | {"mech": "just mech"}  # their keys in DURATIONS
DURATIONS = os.path.join(stages.REPO, "model", "durations.json")


def units(model=True, mech=True, sim=True):
    """{unit: its pytest -k expression}, None for just sim's parts and just mech: the model's units (its sim's
    `sim`), mech's, or both."""
    # -k matches substrings: a document's id picks the ids it is part of too (next-mech-back-mechanical), so it
    # leaves them
    docs = {d: " and ".join([d, *(f"not {o}" for o in stages.DOCS if o != d and d in o)]) for d in stages.DOCS}
    rest = " and ".join(f"not {d}" for d in stages.DOCS)
    sims = dict.fromkeys(SIM if sim else [])
    return ({**docs, "rest": rest, **sims} if model else {}) | ({"mech": None} if mech else {})


def seconds(durations):
    """{unit: seconds}: each test's under the unit whose -k picks it (the rest otherwise); an unmeasured unit, the mean."""
    expr = units()
    just = {v: k for k, v in JUST.items()}
    took = dict.fromkeys(expr, 0.0)
    docs = sorted(stages.DOCS, key=len, reverse=True)  # the longest id a test names is its document
    for test, s in durations.items():
        took[just.get(test) or next((d for d in docs if d in test), "rest")] += s
    measured = [s for s in took.values() if s]
    return {u: s or (sum(measured) / len(measured) if measured else 1.0) for u, s in took.items()}


def shards(model=True, mech=True, sim=True):
    """[{shard, units, tests, sim}]: tests is the shard's pytest arguments (PYTEST_ADDOPTS), empty when it has none;
    sim its parts of just sim (SIM_PART), space-separated, empty when it has none."""
    weight = {u: s for u, s in seconds(json.load(open(DURATIONS))).items() if u in units(model, mech, sim)}
    loads = [[] for _ in range(N)]
    for unit in sorted(weight, key=lambda u: (-weight[u], u)):
        min(loads, key=lambda load: sum(weight[u] for u in load)).append(unit)
    expr = units()
    out = []
    for load in filter(None, loads):
        picks = [f"({expr[u]})" for u in load if expr[u]]
        tests = shlex.join(["-k", " or ".join(picks)]) if picks else ""
        sims = " ".join(u.removeprefix("sim ") for u in load if u in SIM)
        out.append({"shard": " ".join(load), "units": load, "tests": tests, "sim": sims})
    return out


if __name__ == "__main__":
    on = {g: os.environ.get(g.upper()) != "false" for g in ("model", "mech", "sim")}
    print(json.dumps(shards(on["model"], on["mech"], on["sim"])))
