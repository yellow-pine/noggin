"""CI's cold convex cache (#223, .github/workflows/check.yml): `python -m model.convex_parts` prints, as JSON, the parts
whose CoACD pieces in model/build/convex are missing or stale, one matrix job each; `python -m model.convex_parts <part>`
cuts that part's pieces (model/mjcf.py convex). Outside model/mjcf.py on purpose: the trajectories' stamp hashes that file (model/trajectories.py)."""

import json
import sys
from unittest import mock

from model import mjcf, stages


class _Stale(Exception):
    pass


def _refuse(*_, **__):
    raise _Stale


def parts():
    """{part: (mesh file, clip)} over every document, as model/mjcf.py's spec() decomposes them."""
    return {stages.stem(p.file): (p.file, p.clip) for doc in stages.DOCS for p in stages.STAGES[doc].parts.values()}


def stale(meshes):
    """The parts mjcf.convex would decompose again: it is asked with CoACD stubbed to raise, so its own key decides."""
    # shortcut: relies on convex() calling CoACD before it clears the part's folder; a key function in mjcf.py once a
    # report-staling edit there is due anyway
    out = []
    with mock.patch.object(mjcf.coacd, "run_coacd", _refuse):
        for part, (file, clip) in meshes.items():
            try:
                mjcf.convex(file, clip)
            except _Stale:
                out.append(part)
    return out


if __name__ == "__main__":
    if sys.argv[1:]:
        mjcf.convex(*parts()[sys.argv[1]])
    else:
        print(json.dumps(stale(parts())))
