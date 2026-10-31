"""Seam: inline_includes(text, repo_root) replaces '# include: <path>' lines with that file's contents."""

from pathlib import Path

from model.fusion_run import inline_includes

REPO = Path(__file__).resolve().parents[1]


def test_include_line_is_replaced_by_file_contents():
    out = inline_includes("a = 1\n# include: model/geometry.py\nprint(EYE_R)\n", REPO)
    assert out.startswith("a = 1\n")
    assert "EYE_R = (59.0, 0.0, 0.0)" in out
    assert out.endswith("print(EYE_R)\n")
    assert "# include:" not in out


def test_text_without_includes_is_unchanged():
    assert inline_includes("x = 2\n", REPO) == "x = 2\n"
