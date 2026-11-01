"""Re-pin Blender (#334, .github/workflows/blender.yml): the newest stable release whose Linux x64 tarball is at least
14 days old, its sha256 from the release's own .sha256 file. The listing comes from the first of
ci/blender.Dockerfile's sources that answers (download.blender.org, then Blender's official mirrors: #367, #370), the
sha256 only when two of them agree. Rewrites the version and sha256 in every file under .github/ and ci/ that holds the
current pin, and prints the new version and the sources that agree on its hash; prints nothing when the pin is
already the newest. Usage: python3 scripts/blender_pin.py"""

import re
import subprocess
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from pathlib import Path

# the Dockerfile's download loop is the one list of sources, in order (docs/adr/0011)
DOCKERFILE = Path(__file__).parents[1] / "ci/blender.Dockerfile"
SOURCES = re.findall(r"for mirror in ([^;]+);", DOCKERFILE.read_text())[0].split()
AGE = timedelta(days=14)
# shortcut: regexes over Apache's autoindex lines (href, then the date); upgrade if the index's format changes
SERIES = re.compile(r'href="Blender(\d+\.\d+)/"')
TARBALL = re.compile(r'href="blender-(\d+\.\d+\.\d+)-linux-x64\.tar\.xz">.*?(\d\d-\w{3}-\d{4} \d\d:\d\d)')
PIN = re.compile(r"blender-(\d+\.\d+\.\d+)-linux-x64|BLENDER=(\d+\.\d+\.\d+)")  # main's workflow, #299's Dockerfile


def key(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in version.split("."))


def newest(listing: str, now: datetime) -> str | None:
    """The newest version among the listing's Linux x64 tarballs that went up at least AGE before now."""
    old = [
        v
        for v, d in TARBALL.findall(listing)
        if now - datetime.strptime(d, "%d-%b-%Y %H:%M").replace(tzinfo=UTC) >= AGE
    ]
    return max(old, key=key, default=None)


def tarball_sha256(sums: str, version: str) -> str:
    """The Linux x64 tarball's hash from a release's blender-X.Y.Z.sha256 (one `<hash>  <file>` line a download)."""
    (sha,) = re.findall(rf"^([0-9a-f]{{64}})  blender-{re.escape(version)}-linux-x64\.tar\.xz$", sums, re.M)
    return sha


def repin(text: str, old: str, new: str, old_sha: str, new_sha: str) -> str:
    """The pin moved from old to new: its version (alone, not inside a longer number), series directory and hash."""
    text = re.sub(rf"(?<![\d.]){re.escape(old)}(?![\d.])", new, text.replace(old_sha, new_sha))
    return text.replace(f"Blender{old.rsplit('.', 1)[0]}/", f"Blender{new.rsplit('.', 1)[0]}/")


def get(url: str) -> str:  # the network fetch; tests pass recorded pages
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode()


def newer(releases: str, old: str, now: datetime, fetch: Callable[[str], str]) -> str | None:
    """The newest release past old in one source's release/ directory; None when old is the newest."""
    series = [s for s in SERIES.findall(fetch(releases)) if key(s) >= key(old)[:2]]
    listing = "".join(fetch(f"{releases}Blender{s}/") for s in series)
    if old not in dict(TARBALL.findall(listing)):  # shortcut: a listing in another format (Berkeley's) is skipped
        raise ValueError(f"{releases} lists no Blender {old} tarball we can read")
    new = newest(listing, now)
    return new if new is not None and key(new) > key(old) else None


def agreed_sha256(version: str, fetch: Callable[[str], str]) -> tuple[str, list[str]]:
    """The tarball's hash and the sources that serve it. Blender signs no checksums, so one mirror's word is not enough:
    at least two sources must answer, and every source that answers must agree."""
    sums: dict[str, str] = {}
    for source in SOURCES:
        url = f"https://{source}/release/Blender{version.rsplit('.', 1)[0]}/blender-{version}.sha256"
        try:
            sums[source] = tarball_sha256(fetch(url), version)
        except (OSError, ValueError, HTTPException):
            pass
    if len(sums) < 2 or len(set(sums.values())) > 1:
        raise ValueError(f"Blender {version}'s sha256 needs two sources that agree and none that differs: {sums}")
    return next(iter(sums.values())), list(sums)


def lookup(old: str, now: datetime, fetch: Callable[[str], str] = get) -> tuple[str, str, str, list[str]] | None:
    """The newest release past old (from the first source whose listing answers), old's and its agreed sha256, and the
    sources that agree on the new one; None when old is the newest. Raises when no source lists or the hashes don't
    agree."""
    errors: list[Exception] = []
    for source in SOURCES:
        try:
            new = newer(f"https://{source}/release/", old, now, fetch)
            break
        except (OSError, ValueError, HTTPException) as e:  # URLError/HTTPError and timeouts are OSErrors
            errors.append(e)
    else:
        raise ExceptionGroup("no Blender source lists the releases", errors)
    if new is None:
        return None
    new_sha, sources = agreed_sha256(new, fetch)
    return new, agreed_sha256(old, fetch)[0], new_sha, sources


def main() -> None:
    tracked = subprocess.run(["git", "ls-files", ".github", "ci"], capture_output=True, text=True, check=True)
    files = [Path(f) for f in tracked.stdout.split()]
    (old,) = {a or b for f in files for a, b in PIN.findall(f.read_text())}  # exactly one pin, wherever it lives
    found = lookup(old, datetime.now(UTC))
    if found is None:
        return
    new, old_sha, new_sha, sources = found
    pinned = [f for f in files if old_sha in f.read_text()]
    assert pinned, f"no file holds Blender {old}'s official sha256 {old_sha}"
    for f in pinned:
        f.write_text(repin(f.read_text(), old, new, old_sha, new_sha))
    print(new, *sources)


if __name__ == "__main__":
    main()
