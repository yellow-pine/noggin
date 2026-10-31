"""Seam: the pure part of model/parts.py (the parts library build) that decides which library designs get
(re)converted: a part is skipped when the stored fingerprint still matches its source files."""

import importlib.util
import os
import sys
import types

HERE = os.path.dirname(__file__)
for name in ("adsk", "adsk.core", "adsk.fusion"):  # parts.py imports Fusion's API at the top; stub it
    sys.modules.setdefault(name, types.ModuleType(name))
spec = importlib.util.spec_from_file_location("parts", os.path.join(HERE, "parts.py"))
parts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parts)


def test_stale_lists_parts_whose_sources_changed_or_were_never_converted(tmp_path):
    a, b = tmp_path / "a.stl", tmp_path / "b.stp"
    a.write_bytes(b"solid a")
    b.write_bytes(b"STEP b")
    library = {"a": [str(a)], "b": [str(b)]}
    stored = {"a": parts.source_fingerprint(library["a"]), "b": parts.source_fingerprint(library["b"])}
    assert parts.stale(library, stored) == []
    assert parts.stale(library, {"a": stored["a"]}) == ["b"]  # never converted
    a.write_bytes(b"solid a2")
    assert parts.stale(library, stored) == ["a"]


def test_each_library_part_converts_from_its_one_source():
    assert all(len(paths) == 1 for paths in parts.LIBRARY.values())  # no decimated proxy: the sweep left Fusion
    assert all("docs/references" in paths[0] for paths in parts.LIBRARY.values())


def test_every_printed_library_part_has_a_spool():
    gspec = importlib.util.spec_from_file_location("geometry", os.path.join(HERE, "geometry.py"))
    geometry = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(geometry)
    from model.engine.stages import REFERENCE

    stems = {REFERENCE[k.split(" (")[0]] for k in geometry.PRINTED}
    assert {stem for s in parts.STLS.values() for stem in s} <= stems
    assert all(
        spool in geometry.SPOOLS and material in geometry.MATERIALS for spool, material in geometry.PRINTED.values()
    )
