"""Seam: the pure parts of model/fusion_lib.py that decide whether a rebuild touches the saved document:
part fingerprints (reuse or re-import) and the summary diff (save a version or print "unchanged")."""

import importlib.util
import os
import sys
import types

HERE = os.path.dirname(__file__)
for name in ("adsk", "adsk.core", "adsk.fusion"):  # fusion_lib imports Fusion's API at the top; stub it
    sys.modules.setdefault(name, types.ModuleType(name))
spec = importlib.util.spec_from_file_location("fusion_lib", os.path.join(HERE, "fusion_lib.py"))
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def test_fingerprint_changes_with_file_content_or_placement_only(tmp_path):
    a, b = tmp_path / "a.stl", tmp_path / "b.stl"
    a.write_bytes(b"solid x")
    b.write_bytes(b"solid y")
    same = lib.fingerprint([str(a)], IDENTITY)
    assert same == lib.fingerprint([str(a)], IDENTITY)
    assert same == lib.fingerprint([str(a)], [1 + 1e-9] + IDENTITY[1:])  # float noise is not a move
    assert same != lib.fingerprint([str(a)], [1, 0, 0, 0.5] + IDENTITY[4:])  # a 5 mm shift is
    assert same != lib.fingerprint([str(b)], IDENTITY)
    assert same != lib.fingerprint([str(a), str(b)], IDENTITY)  # the proxy counts too


def test_changes_lists_what_differs_between_two_summaries():
    old = {"joints": {"L lid horn": {"limits": [-20, 30]}, "gone": {}}, "ports": {"USB-C": [1, 2, 3]}}
    new = {"joints": {"L lid horn": {"limits": [-20, 20]}, "new": {}}, "ports": {"USB-C": [1, 2, 3]}}
    assert lib.changes(old, old) == []
    assert lib.changes(old, new) == [
        "joints L lid horn: {'limits': [-20, 30]} -> {'limits': [-20, 20]}",
        "joints gone: removed",
        "joints new: added",
    ]
    assert lib.changes(None, new) == ["no previous summary"]


def test_inserted_part_fingerprint_follows_the_library_version_and_placement():
    v3 = lib.fingerprint([], IDENTITY, "servo@v3")
    assert v3 == lib.fingerprint([], IDENTITY, "servo@v3")
    assert v3 != lib.fingerprint([], IDENTITY, "servo@v4")  # the library part was reconverted
    assert v3 != lib.fingerprint([], [1, 0, 0, 0.5] + IDENTITY[4:], "servo@v3")  # or moved
