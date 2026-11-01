"""firmware_watch.py: the newest release is the highest `<h2>` that reads `<version> (<yyyymmdd>)`; a page without one
fails instead of reporting nothing new."""

import pytest

from scripts.firmware_watch import newest

# the vendor's wiki page (Wiki.js, server-rendered) as it read on 2026-11-01, trimmed (anchors' hrefs cut)
PAGE = """
<h1 class="title">Firmware Release Notes</h1>
<h2 id="h-01000302-20251126" class="toc-header"><a class="toc-anchor" href="#">¶</a> 01.00.03.02 (20251126)</h2>
<h3 id="new-features" class="toc-header"><a class="toc-anchor" href="#new-features">¶</a> New Features</h3>
<p>Supports 1.2.3 (20250101) style text in a paragraph, which is not a release.</p>
<h2 id="h-01000301-20250910" class="toc-header"><a class="toc-anchor" href="#">¶</a> 01.00.03.01 (20250910)</h2>
<h2 id="end-notes" class="toc-header"><a class="toc-anchor" href="#end-notes">¶</a> End Notes</h2>
"""


def test_the_newest_release_is_the_highest_version_wherever_it_stands():
    assert newest(PAGE) == "01.00.03.02"
    assert newest(PAGE.replace("01.00.03.01", "01.00.10.00")) == "01.00.10.00"


def test_headings_that_are_not_releases_are_skipped():
    assert newest("<h2>Notice</h2><p>0.9.0 (20240101)</p>" + PAGE) == "01.00.03.02"


def test_a_page_without_releases_fails():
    with pytest.raises(AssertionError):
        newest("<h2>Page not found</h2>")
