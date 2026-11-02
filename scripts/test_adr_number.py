"""ADR numbers (docs/adr/0015): no two ADRs share one."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_no_two_adrs_share_a_number():
    # Code runs this on the PR merged into main: a number main took since the draft fails here
    numbers = [p.name[:4] for p in (ROOT / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    taken = sorted({n for n in numbers if numbers.count(n) > 1})
    assert not taken, (
        f"ADR {', '.join(taken)} taken twice: git mv your draft to the next free number and fix its references"
    )
