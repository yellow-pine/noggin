"""A few GLOSSARY.md avoid-words that have crept in before must stay out of code and scripts (docs are exempt).
Not the whole avoid list: API words like serial, board, hook are unavoidable in places."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AVOID = ["daemon", "poke", "animation", "neutral", "puppeteer", "receiver"]
FILES = [
    p
    for d in ("eyes", "reactions", "noggin", "scripts")
    for p in (ROOT / d).rglob("*")
    if p.is_file() and p.suffix in (".py", ".sh", "") and "stock-backup" not in p.parts and p.name != "gaze_trace.py"
]
FILES.append(ROOT / "Makefile")
ALLOWED = {"daemon": ["daemon=True"]}  # threading API, not our vocabulary


def test_no_avoid_words_in_code():
    hits = []
    for f in FILES:
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            for w in AVOID:
                if re.search(rf"\b{w}\b", line, re.I) and not any(a in line for a in ALLOWED.get(w, [])):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {w}")
    assert not hits, "\n".join(hits)


def test_the_model_is_never_called_twin():
    files = [p for p in (ROOT / "model").rglob("*.py")] + [ROOT / "Makefile"]
    hits = [
        f"{f.relative_to(ROOT)}:{n}"
        for f in files
        for n, line in enumerate(f.read_text().splitlines(), 1)
        if re.search(r"twin", line, re.I)
    ]
    assert not hits, "\n".join(hits)


def test_docs_say_noggin_service_and_model():
    """The decisions' words in ADRs, README, CONTRIBUTING (GLOSSARY and CLAUDE.md name the avoid-words)."""
    files = [
        *(ROOT / "docs" / "adr").glob("*.md"),
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs" / "model-notes.md",
    ]
    hits = [
        f"{f.relative_to(ROOT)}:{n}"
        for f in files
        for n, line in enumerate(f.read_text().splitlines(), 1)
        if re.search(r"\bdaemon\b|\btwin\b", line, re.I) and 'not "the Daemon"' not in line
    ]
    assert not hits, "\n".join(hits)


def test_fusion_is_only_history():
    """Fusion is gone (#88, ADR 0004): only the research notes and the two ADRs that record it may name it."""
    history = ("docs/research/", "docs/adr/0004-", "docs/adr/0006-", "test_vocabulary.py")
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = [
        f"{f}:{n}"
        for f in files
        if not f.startswith(history) and (ROOT / f).is_file()
        for n, line in enumerate((ROOT / f).read_text(errors="ignore").splitlines(), 1)
        if re.search(r"fusion", line, re.I)
    ]
    assert not hits, "\n".join(hits)
