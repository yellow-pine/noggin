"""Seam: model/render/guide.py's step table, the guide steps the sheets put beside the model."""

import os
import subprocess

import pytest

from model.engine import stages
from model.render import guide


def test_every_guide_has_steps_and_every_step_shows_parts_of_its_document():
    assert {s.guide for s in guide.STEPS} == set(guide.GUIDES)
    for s in guide.STEPS:
        doc = stages.STAGES[guide.GUIDES[s.guide][1]]
        assert s.parts and not set(s.parts) - set(doc.parts), (s.guide, s.step, set(s.parts) - set(doc.parts))


@pytest.mark.parametrize("name", sorted(guide.GUIDES))
def test_every_step_picture_is_on_its_page_of_the_guide_pdf(name):
    pdf = guide.pdf(name)
    if not os.path.isfile(pdf):
        pytest.skip("the guide PDFs are local only (docs/references)")
    listing = subprocess.run(["pdfimages", "-list", pdf], capture_output=True, text=True, check=True).stdout
    per_page = {}
    for row in listing.splitlines()[2:]:
        page = int(row.split()[0])
        per_page[page] = per_page.get(page, 0) + 1
    for s in guide.STEPS:
        if s.guide == name:
            assert s.image < per_page.get(s.page, 0), (name, s.step, s.page, s.image)
