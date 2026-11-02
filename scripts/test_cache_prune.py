"""cache_prune.py: the prefixes come from the workflows themselves, and a cache is stale only when its key starts with
none of them."""

import pytest

from scripts.cache_prune import WORKFLOWS, prefixes, stale


def flow(tmp_path, steps):
    (tmp_path / "w.yml").write_text(f"on: push\njobs:\n  j:\n    steps:\n{steps}")
    return tmp_path


def test_the_workflows_on_main_keep_their_caches_and_drop_the_retired_ones():
    keys = ["ours-convex-ab-cd", "node-cache-Linux-x64-npm-ab", "blender-5.2.2-linux-x64", "mermaid-1"]
    caches = [{"id": i, "key": k} for i, k in enumerate(keys)]
    assert [c["key"] for c in stale(caches, prefixes(WORKFLOWS))] == ["blender-5.2.2-linux-x64", "mermaid-1"]


def test_keys_restore_keys_anchors_and_implicit_caches(tmp_path):
    steps = """\
      - uses: actions/cache/restore@abc
        with:
          key: &k a-${{ hashFiles('x') }}-b
          restore-keys: |
            a-
            c-${{ runner.os }}-
      - uses: actions/cache/save@abc
        with:
          key: ${{ steps.x.outputs.cache-primary-key }}
      - uses: actions/setup-node@abc
        with:
          cache: npm
      - uses: astral-sh/setup-uv@abc
        with:
          enable-cache: false
      - uses: actions/checkout@abc
        with:
          key: not-a-cache-
"""
    assert prefixes(flow(tmp_path, steps)) == {"a-", "c-", "node-cache-"}
    assert "setup-uv-" in prefixes(flow(tmp_path, "      - uses: astral-sh/setup-uv@abc\n"))


def test_a_key_with_no_literal_head_fails_rather_than_prune_its_caches(tmp_path):
    steps = "      - uses: actions/cache@abc\n        with:\n          key: ${{ runner.os }}-x\n"
    with pytest.raises(AssertionError):
        prefixes(flow(tmp_path, steps))
