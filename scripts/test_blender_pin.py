"""blender_pin.py: the newest Linux x64 tarball at least 14 days old wins, its hash comes from the release's .sha256,
and the re-pin moves the version, series directory and hash and nothing else; sources fall back in the Dockerfile's
order."""

from datetime import UTC, datetime
from urllib.error import HTTPError

import pytest

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
SUMS = {"5.2.2": f"{SHA}  blender-5.2.2-linux-x64.tar.xz\n", "5.2.3": f"{'3' * 64}  blender-5.2.3-linux-x64.tar.xz\n"}
LATER = datetime(2026, 11, 5, 9, tzinfo=UTC)


def recorded(answers: dict[str, str]):
    """A get() over recorded pages: a source not in answers says 403, as download.blender.org did to runners (#367)."""

    def get(url: str) -> str:
        host, _, path = url.removeprefix("https://").partition("/release/")
        if host not in answers:
            raise HTTPError(url, 403, "Forbidden", {}, None)  # pyright: ignore[reportArgumentType]
        if path == "":
            return RELEASES
        if path == "Blender5.2/":
            return answers[host]
        return SUMS[path.removeprefix("Blender5.2/blender-").removesuffix(".sha256")]

    return get


def test_the_sources_are_the_dockerfiles_download_order():
    assert SOURCES[0] == "download.blender.org"
    assert "mirror.clarkson.edu/blender" in SOURCES[1:]


def test_a_403_or_an_unreadable_listing_falls_to_the_next_mirror():
    # Berkeley lists in a table with ISO-ish dates: it shows no pinned tarball, so its hashes are never used
    berkeley = '<a href="blender-5.2.2-linux-x64.tar.xz" title="x">x</a><td class="date">2026-Sep-15 09:18</td>\n'
    answers = {SOURCES[2]: berkeley, SOURCES[3]: LISTING}
    assert lookup("5.2.2", LATER, recorded(answers)) == ("5.2.3", SHA, "3" * 64)
    assert lookup("5.2.2", NOW, recorded(answers)) is None


def test_every_source_failing_fails_the_run():
    with pytest.raises(ExceptionGroup):
        lookup("5.2.2", LATER, recorded({}))
