"""Derived, not listed (docs/adr/0011): a workflow, the Makefile or a doc never spells out a list the code holds (the
gestures, the servos, the documents the model simulates). A list is two or more of one list's names in a workflow or
the Makefile, or three on one line of Markdown, where two is prose ("pan and tilt"). A name joined to another word by a
hyphen ("pan-tilt") is not the name."""

import re
import subprocess
from pathlib import Path

from model.stages import DOCS
from noggin.core import CORES, GESTURES

ROOT = Path(__file__).resolve().parent
LISTS = {"gesture": GESTURES, "servo": [s for ports in CORES.values() for s in ports.values()], "document": list(DOCS)}
HISTORY = ("docs/research/", "docs/adr/", "CHANGELOG.md")  # what was decided or found then, in its own words
ALLOWED = {  # (file, list): why it spells them
    ("GLOSSARY.md", "servo"): "the Servo entry defines the names",
    ("docs/how-it-works.md", "servo"): "the diagram's Core 2 label, drawn as GitHub shows it",
    ("docs/build/wiring.md", "servo"): "the second Core's ports: #306 fills them from CHANNELS",
}


def spelled_lists():
    """{(file, list): [where]} for every list a workflow, the Makefile or a doc spells out."""
    files = subprocess.run(
        ["git", "ls-files", "*.md", ".github/*.yml", "Makefile"], cwd=ROOT, capture_output=True, text=True
    )
    found = {}
    for f in files.stdout.split():
        if f.startswith(HISTORY):
            continue
        text = (ROOT / f).read_text()
        chunks, min_hits = (enumerate(text.splitlines(), 1), 3) if f.endswith(".md") else ([("", text)], 2)
        for n, unit in chunks:
            for kind, names in LISTS.items():
                hit = sorted(m for m in names if re.search(rf"(?<![\w-]){re.escape(m)}(?![\w-])", unit))
                if len(hit) >= min_hits:
                    found.setdefault((f, kind), []).append(f"{f}:{n} {', '.join(hit)}")
    return found


def test_nothing_spells_out_a_list_the_code_holds():
    found = spelled_lists()
    assert [w for key, where in found.items() if key not in ALLOWED for w in where] == []
    assert [key for key in ALLOWED if key not in found] == [], "spelled out no more: drop it from ALLOWED"
