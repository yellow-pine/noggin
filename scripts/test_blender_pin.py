"""blender_pin.py: the newest Linux x64 tarball at least 14 days old wins, its hash comes from the release's .sha256,
and the re-pin moves the version, series directory and hash and nothing else; sources fall back in the Dockerfile's
order."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from scripts import blender_pin
from scripts.blender_pin import SOURCES, lookup, newest, repin, tarball_sha256

NOW = datetime(2026, 11, 1, tzinfo=UTC)
# download.blender.org/release/Blender5.2/ and a later series, as Apache's autoindex lists them
LISTING = """
<a href="blender-5.2.2-linux-x64.tar.xz">blender-5.2.2-linux-x64.tar.xz</a>     15-Sep-2026 09:18           383295504
<a href="blender-5.2.2-macos-arm64.dmg">blender-5.2.2-macos-arm64.dmg</a>       15-Sep-2026 09:18           383295504
<a href="blender-5.2.3-linux-x64.tar.xz">blender-5.2.3-linux-x64.tar.xz</a>     22-Oct-2026 08:13           385331224
<a href="blender-5.2.3.sha256">blender-5.2.3.sha256</a>                         22-Oct-2026 08:16                 777
"""
SHA = "84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168"


def test_a_release_younger_than_14_days_waits():
    assert newest(LISTING, NOW) == "5.2.2"
    assert newest(LISTING, datetime(2026, 11, 5, 8, 13, tzinfo=UTC)) == "5.2.3"


def test_versions_compare_as_numbers():
    later = '<a href="blender-5.10.0-linux-x64.tar.xz">x</a> 01-Oct-2026 00:00 1\n'
    assert newest(LISTING + later, NOW) == "5.10.0"


def test_nothing_old_enough_is_none():
    assert newest(LISTING, datetime(2026, 9, 20, tzinfo=UTC)) is None


def test_the_hash_is_the_linux_tarballs_line():
    sums = (
        f"{'1' * 64}  blender-5.2.2-macos-arm64.dmg\n"
        f"{SHA}  blender-5.2.2-linux-x64.tar.xz\n"
        f"{'2' * 64}  blender-5.2.2-windows-x64.zip\n"
    )
    assert tarball_sha256(sums, "5.2.2") == SHA


def test_the_repin_moves_version_series_and_hash_only():
    before = (
        "# Blender 5.2.2 cached; numpy 15.2.2 and 5.2.20 stay\n"
        "key: blender-5.2.2-linux-x64\n"
        "curl https://download.blender.org/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz\n"
        f'echo "{SHA}  x" | sha256sum -c\n'
    )
    after = repin(before, "5.2.2", "5.3.0", SHA, "f" * 64)
    assert after == (
        "# Blender 5.3.0 cached; numpy 15.2.2 and 5.2.20 stay\n"
        "key: blender-5.3.0-linux-x64\n"
        "curl https://download.blender.org/release/Blender5.3/blender-5.3.0-linux-x64.tar.xz\n"
        f'echo "{"f" * 64}  x" | sha256sum -c\n'
    )


RELEASES = """
<a href="Blender5.1/">Blender5.1/</a>  19-May-2026 07:10  -
<a href="Blender5.2/">Blender5.2/</a>  14-Jul-2026 07:24  -
"""
GOOD = {"5.2.2": SHA, "5.2.3": "3" * 64}
LATER = datetime(2026, 11, 5, 9, tzinfo=UTC)
# Berkeley lists in a table with ISO-ish dates: the script reads no pinned tarball there, so it takes the next listing
TABLE = '<a href="blender-5.2.2-linux-x64.tar.xz" title="x">x</a><td class="date">2026-Sep-15 09:18</td>\n'


def site(source: str, listing: str, sums: dict[str, str]) -> dict[str, str]:
    """One source's recorded pages: its release index, Blender5.2/ listing and .sha256 files."""
    r = f"https://{source}/release/"
    files = {f"{r}Blender5.2/blender-{v}.sha256": f"{s}  blender-{v}-linux-x64.tar.xz\n" for v, s in sums.items()}
    return {r: RELEASES, f"{r}Blender5.2/": listing, **files}


def recorded(pages: dict[str, str]):
    """A fetch over recorded pages: a page not recorded says 403, as download.blender.org did to runners (#367)."""

    def fetch(url: str) -> str:
        if url not in pages:
            raise HTTPError(url, 403, "Forbidden", {}, None)  # pyright: ignore[reportArgumentType]
        return pages[url]

    return fetch


def test_the_sources_are_the_dockerfiles_download_order():
    assert SOURCES[0] == "download.blender.org"
    assert len(SOURCES) > 2


def test_a_403_or_an_unreadable_listing_falls_to_the_next_and_two_agreeing_sources_pin():
    pages = recorded({**site(SOURCES[2], TABLE, GOOD), **site(SOURCES[3], LISTING, GOOD)})
    assert lookup("5.2.2", LATER, pages) == ("5.2.3", SHA, "3" * 64, [SOURCES[2], SOURCES[3]])
    assert lookup("5.2.2", NOW, pages) is None


def test_one_source_alone_does_not_pin():
    with pytest.raises(ValueError, match="two sources that agree"):
        lookup("5.2.2", LATER, recorded(site(SOURCES[1], LISTING, GOOD)))


def test_sources_that_disagree_do_not_pin():
    forged = {**GOOD, "5.2.3": "e" * 64}
    pages = {**site(SOURCES[0], LISTING, GOOD), **site(SOURCES[1], LISTING, GOOD), **site(SOURCES[3], LISTING, forged)}
    with pytest.raises(ValueError, match="none that differs"):
        lookup("5.2.2", LATER, recorded(pages))


def test_every_source_failing_fails_the_run():
    with pytest.raises(ExceptionGroup):
        lookup("5.2.2", LATER, recorded({}))


def test_the_weekly_update_moves_both_binary_and_native_source_pins(tmp_path, monkeypatch):
    repo = Path(blender_pin.__file__).parents[1]
    files = [tmp_path / "blender.Dockerfile", tmp_path / "gx10-blender-build.sh"]
    for destination in files:
        destination.write_text((repo / "ci" / destination.name).read_text())
    binary_sha = "78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec"
    monkeypatch.setattr(
        blender_pin.subprocess, "run", lambda *args, **kw: SimpleNamespace(stdout="\n".join(map(str, files)))
    )
    monkeypatch.setattr(blender_pin, "lookup", lambda *args: ("5.3.0", binary_sha, "e" * 64, ["mirror"]))
    monkeypatch.setattr(blender_pin, "source_sha256", lambda version: "f" * 64, raising=False)
    blender_pin.main()
    assert "BLENDER=5.3.0" in files[0].read_text()
    assert "e" * 64 in files[0].read_text()
    native = files[1].read_text()
    assert "5.2.3" not in native
    assert "BLENDER=5.3.0" in native
    assert "f" * 64 in native


def test_one_official_source_archive_alone_does_not_pin(monkeypatch):
    def archive(url, **kwargs):
        if url.startswith("https://download.blender.org/source/"):
            return BytesIO(b"abc")
        raise OSError("mirror unavailable")

    monkeypatch.setattr(blender_pin.urllib.request, "urlopen", archive)
    with pytest.raises(ValueError, match="two sources"):
        blender_pin.source_sha256("5.3.0")


def test_source_archives_must_match_across_the_official_mirrors(monkeypatch):
    monkeypatch.setattr(blender_pin.urllib.request, "urlopen", lambda *args, **kw: BytesIO(b"abc"))
    assert blender_pin.source_sha256("5.3.0") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

    def changed_mirror(url, **kwargs):
        return BytesIO(b"changed" if SOURCES[-1] in url else b"abc")

    monkeypatch.setattr(blender_pin.urllib.request, "urlopen", changed_mirror)
    with pytest.raises(ValueError, match="none that differs"):
        blender_pin.source_sha256("5.3.0")
