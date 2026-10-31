"""A few GLOSSARY.md avoid-words that have crept in before must stay out of code and scripts (docs are exempt).
Not the whole avoid list: API words like serial, board, hook are unavoidable in places."""

import re
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


# Files that keep the designer's names until their tickets delete them (#97 the reference machinery, #99 Fusion).
LEAVING = {
    *(f"model/{f}.py" for f in ("eyes", "stack", "mouth", "base", "stage", "parts", "fusion_lib", "fusion_run")),
    *(f"model/test_{f}.py" for f in ("parts", "fusion_lib", "fusion_run")),
    "model/printed/test_gate.py",
    "model/engine/test_gate.py",
    "model/engine/step_mesh.py",
    "model/render/guide.py",
    "model/render/test_guide.py",
}


def test_designer_file_names_only_in_the_reference_table():
    """Every part goes by our name (GLOSSARY.md, Model); the designer's file names live only in stages.REFERENCE, the
    table that loads the local reference meshes. README (credits) and docs/research (dated history) are exempt."""
    import subprocess

    from model.engine import stages

    names = set(stages.REFERENCE)
    stems = {s for n, s in stages.REFERENCE.items() if s != n}
    # the stems, and their shortened forms the code used for parts (no "PandT" prefix, no version suffix)
    variants = {v for s in stems for v in (s, s.removeprefix("PandT "), s.removesuffix(" v2"))}
    banned = sorted(v for v in variants if " " in v and v not in names)
    words = "|".join(r"[ _]".join(map(re.escape, v.lower().split())) for v in banned)
    pattern = re.compile(rf"PandT|\sv2\b(?!\.\d)|(?i:(?<!\w)(?:{words})(?!\w))")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    files = [
        f
        for f in tracked
        if f not in LEAVING | {"README.md", "test_vocabulary.py"}
        and not f.startswith("docs/research/")
        and Path(f).suffix in (".py", ".md", ".json", ".sh", ".yml", ".toml", "")
        and (ROOT / f).is_file()
    ]
    hits = []
    for f in files:
        text = (ROOT / f).read_text(errors="replace")
        if f == "model/engine/stages.py":
            start = text.index("REFERENCE = {")
            text = text[:start] + text[text.index("\n}\n", start) :]
        if f.startswith("model/reports/"):  # a report's input stamp lists the reference files the sim read
            text = re.sub(r'"docs/references/[^"]*"', '""', text)
        hits += [
            f"{f}:{n}: {line.strip()[:120]}" for n, line in enumerate(text.splitlines(), 1) if pattern.search(line)
        ]
    assert not hits, f"{len(hits)} lines\n" + "\n".join(hits)
