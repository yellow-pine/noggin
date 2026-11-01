"""blender_pin.py: the newest Linux x64 tarball at least 14 days old wins, its hash comes from the release's .sha256,
and the re-pin moves the version, series directory and hash and nothing else."""

from datetime import UTC, datetime

from scripts.blender_pin import newest, repin, tarball_sha256

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
