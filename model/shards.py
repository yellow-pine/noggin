"""Code Checks' model shards (`make model-shards-list`, #305): the hero's collision sweep alone, the recorded sweep
documents on one shard, each Stage on its own, the rest of the model tests, and make sim. A document's tests are
picked by its id (pytest -k on the parameter, stages.DOCS), so a new document needs no workflow edit."""

import json
import shlex

from model import geometry as g
from model import stages

HERO = "model/render/test_hero.py"


def shards():
    """[{shard, tests}]: tests is the shard's pytest arguments (PYTEST_ADDOPTS), none for sim."""
    pick = {"sweeps": " or ".join(d for d in stages.DOCS if d not in g.STAGES)}  # -k on the documents' ids
    pick |= {d.removeprefix("noggin-"): d for d in g.STAGES}
    pick["rest"] = " and ".join(f"not {d}" for d in stages.DOCS)
    return [
        {"shard": "hero", "tests": HERO},
        *({"shard": name, "tests": shlex.join([f"--ignore={HERO}", "-k", k])} for name, k in pick.items()),
        {"shard": "sim"},
    ]


if __name__ == "__main__":
    print(json.dumps(shards()))
