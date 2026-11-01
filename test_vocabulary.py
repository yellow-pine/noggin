"""A few GLOSSARY.md avoid-words that have crept in before must stay out of code and scripts (docs are exempt).
Not the whole avoid list: API words like serial, board, hook are unavoidable in places."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AVOID = ["daemon", "poke", "animation", "neutral", "puppeteer", "receiver"]
FILES = [
    p
    for d in ("ci", "eyes", "reactions", "noggin", "scripts", "web", "mech")
    for p in (ROOT / d).rglob("*")
    if p.is_file()
    and p.suffix in (".py", ".sh", "")
    and not {"stock-backup", "build"} & set(p.parts)  # the stock program, mech/build
    and p.name != "gaze_trace.py"
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
        *(ROOT / "docs").glob("*.md"),
        *(ROOT / "docs" / "build").glob("*.md"),
        *(ROOT / "docs" / "use").glob("*.md"),
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


# The designer's file stems our parts replaced (#96): history, never names in the repo.
DESIGNER = [
    "main bracket v2", "L eyeball regular", "R eyeball regular", "regular pupil", "inside lid", "outside lid",
    "eyelid bar", "eyelid bar crank", "PandT base", "PandT bearing block", "PandT pan base", "PandT upright v2",
    "PandT tilt arm", "PandT servo mount plain", "PandT servo mount cutout", "PandT wire holder", "PandT bar",
    "top jaw plain", "bottom jaw plain", "jaws servo mount", "jaws connector bar",
]  # fmt: skip


# CyberBrick product codes: only where we buy them.
CODES = ["ZK004", "ZL003", "PG001", "XA004", "PC003", "X11"]
# Where the vendor, the designer and their names may appear: the site's Credits page, README's credits line, the buy
# list, dated research notes (history).
CREDITS = {"README.md": "## Credits", "docs/build/parts.md": "## Parts to buy"}


def outside_credits(f, text):
    """The file's lines with their numbers, minus its credits section (heading to the next ## heading)."""
    lines, skip = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            skip = line.strip() == CREDITS.get(f)
        if not skip:
            lines.append((n, line))
    return lines


def test_vendor_and_designer_names_only_in_credits():
    """Every part and board goes by our name (GLOSSARY.md); the vendor, the designer, product codes and the
    designer's file names stay in docs/credits.md, README's credits line, the buy list and dated docs/research."""
    from model import printed

    names = set(printed.PARTS)
    # the stems, and their shortened forms the code used for parts (no "PandT" prefix, no version suffix)
    variants = {v for s in DESIGNER for v in (s, s.removeprefix("PandT "), s.removesuffix(" v2"))}
    banned = sorted(v for v in variants if " " in v and v not in names)
    words = "|".join(r"[ _]".join(map(re.escape, v.lower().split())) for v in banned)
    vendors = "|".join(["PandT", "PurpleShark", "MakerWorld", "Bambu", "CyberBrick"])
    codes = "|".join(CODES)  # case-sensitive: "\x11" in the baked trace bytes is not a code
    pattern = re.compile(rf"(?i:\b(?:{vendors})\b)|\b(?:{codes})\b|\sv2\b(?!\.\d)|(?i:(?<!\w)(?:{words})(?!\w))")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    files = [
        f
        for f in tracked
        if f not in {"test_vocabulary.py", "docs/credits.md"}
        and not re.match(r"docs/research/\d{4}-\d\d-\d\d-", f)
        and Path(f).suffix in (".py", ".md", ".json", ".sh", ".yml", ".toml", "")
        and (ROOT / f).is_file()
    ]
    hits = [
        f"{f}:{n}: {line.strip()[:120]}"
        for f in files
        for n, line in outside_credits(f, (ROOT / f).read_text(errors="replace"))
        if pattern.search(line)
    ]
    assert not hits, f"{len(hits)} lines\n" + "\n".join(hits)
