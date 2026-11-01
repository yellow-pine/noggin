"""Watch the Core's firmware releases (#334, .github/workflows/firmware.yml). The vendor publishes them only on its
wiki's release notes page (the workflow's NOTES), one `<h2>` per release, e.g. `01.00.03.02 (20251126)`.
Reads the page on stdin and prints the newest version. Usage: curl -fsS "$NOTES" | python3 scripts/firmware_watch.py
(the wiki answers urllib's user agent with 403, curl's with the page)"""

import re
import sys
from html.parser import HTMLParser

RELEASE = re.compile(r"(\d+(?:\.\d+)+) \(\d{8}\)")


class _Headings(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h2: list[str] = []
        self._in = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2":
            self._in, self.h2 = True, [*self.h2, ""]

    def handle_endtag(self, tag: str) -> None:
        self._in = self._in and tag != "h2"

    def handle_data(self, data: str) -> None:
        if self._in:
            self.h2[-1] += data


def newest(page: str) -> str:
    """The highest version among the release headings; fails loudly when the page has none."""
    parser = _Headings()
    parser.feed(page)
    versions = [m[1] for h in parser.h2 if (m := RELEASE.search(h))]
    assert versions, "no release heading: the page moved or changed shape"
    return max(versions, key=lambda v: tuple(int(n) for n in v.split(".")))


if __name__ == "__main__":
    print(newest(sys.stdin.read()))
