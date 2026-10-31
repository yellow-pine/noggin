"""GLOSSARY.md avoid-words must not appear in code, scripts or their comments (docs are exempt)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AVOID = ["daemon", "poke", "firmware", "animation", "neutral", "puppeteer", "receiver"]
FILES = [p for d in ("eyes", "reactions", "noggin", "scripts") for p in (ROOT / d).rglob("*")
         if p.is_file() and p.suffix in (".py", ".sh", "") and "stock-backup" not in p.parts and p.name != "gaze_trace.py"]
FILES.append(ROOT / "Makefile")
ALLOWED = {"daemon=True"}   # threading API, not our vocabulary

def test_no_avoid_words_in_code():
    hits = []
    for f in FILES:
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            for w in AVOID:
                if re.search(rf"\b{w}\b", line, re.I) and not any(a in line for a in ALLOWED):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {w}")
    assert not hits, "\n".join(hits)
