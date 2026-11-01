"""docs_versions.py: which Releases' docs Site Deploy serves beside main's, and versions.json (ADR 0014)."""

from scripts.docs_versions import served, versions_json


def release(tag: str, docs: bool = True, draft: bool = False, prerelease: bool = False) -> dict:
    assets = [{"name": f"noggin-{tag}.zip"}] + ([{"name": f"noggin-docs-{tag}.tar.gz"}] if docs else [])
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": assets}


def test_no_release_serves_latest_alone():
    assert served([]) == []
    assert versions_json([]) == [{"version": "latest", "title": "latest", "aliases": []}]


def test_each_minor_serves_its_newest_patch_newest_minor_first():
    releases = [release("v0.1.0"), release("v0.2.0"), release("v0.1.10"), release("v0.1.2"), release("v1.0.0")]
    assert served(releases) == [("v1.0", "v1.0.0"), ("v0.2", "v0.2.0"), ("v0.1", "v0.1.10")]
    assert versions_json(served(releases))[:2] == [
        {"version": "latest", "title": "latest", "aliases": []},
        {"version": "v1.0", "title": "v1.0.0", "aliases": []},
    ]


def test_drafts_prereleases_and_releases_without_docs_are_skipped():
    releases = [
        release("v0.1.0", docs=False),  # before docs were attached
        release("v0.1.1", draft=True),
        release("v0.0.0-test.358", prerelease=True),
        release("v0.2.0-rc.1"),  # not a plain vX.Y.Z
    ]
    assert served(releases) == []
