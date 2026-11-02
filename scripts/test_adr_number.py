"""ADR numbers (docs/adr/0015): no two ADRs share one, and adr_number.py moves a draft past main's numbers, fixing the
references its branch added."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "adr_number.py"


def test_no_two_adrs_share_a_number():
    # Code runs this on the PR merged into main: a number main took since the draft fails here
    numbers = [p.name[:4] for p in (ROOT / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    taken = sorted({n for n in numbers if numbers.count(n) > 1})
    assert not taken, f"ADR {', '.join(taken)} taken twice: python3 scripts/adr_number.py docs/adr/<your draft>.md"


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True, capture_output=True
    )


def write(repo: Path, path: str, text: str) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)


def test_a_draft_moves_past_mains_numbers_with_the_references_it_added(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "docs/adr/0001-first.md", "# First\n")
    write(tmp_path, "README.md", "Intro: ADR 0002 will follow.\n")  # main's own, before the draft
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "checkout", "-qb", "draft")
    write(tmp_path, "docs/adr/0002-mine.md", "# Mine\n\nAfter ADR 0001.\n")
    write(
        tmp_path,
        "README.md",
        "Intro: ADR 0002 will follow.\nMine: ADR 0002 (docs/adr/0002-mine.md), docs/adr/0001, 0002.\n",
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "mine")
    git(tmp_path, "checkout", "-q", "main")  # main takes 0002 meanwhile
    write(tmp_path, "docs/adr/0002-theirs.md", "# Theirs\n")
    write(tmp_path, "README.md", "Intro\nTheirs: ADR 0002.\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "theirs")
    git(tmp_path, "checkout", "-q", "draft")
    write(tmp_path, "notes.md", "Untracked, about ADR 0002 too.\n")  # a draft not yet added

    run = subprocess.run(
        [sys.executable, SCRIPT, "docs/adr/0002-mine.md", "main"], cwd=tmp_path, capture_output=True, text=True
    )

    assert run.returncode == 0, run.stderr
    assert not (tmp_path / "docs/adr/0002-mine.md").exists()
    assert (tmp_path / "docs/adr/0003-mine.md").read_text() == "# Mine\n\nAfter ADR 0001.\n"
    assert (tmp_path / "README.md").read_text() == (
        "Intro: ADR 0002 will follow.\nMine: ADR 0003 (docs/adr/0003-mine.md), docs/adr/0001, 0003.\n"
    )
    assert (tmp_path / "notes.md").read_text() == "Untracked, about ADR 0003 too.\n"
    assert re.search(r"0002-mine\.md -> docs/adr/0003-mine\.md", run.stdout)
