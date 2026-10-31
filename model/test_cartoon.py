"""Seam: model/cartoon.py, the two post-process styles of the Fusion renders, on a synthetic transparent capture."""

import numpy as np
import pytest

from model import cartoon

PINK, WHITE = np.array([0xF7, 0xCE, 0xD7]) / 255, np.array([1.0, 1.0, 1.0])


def capture(w=480, h=240):
    """Transparent frame: a shaded pink disc (bright left half, dim right half) overlapping a grey-white square."""
    img = np.zeros((h, w, 4))
    yy, xx = np.mgrid[:h, :w]
    square = (abs(xx - 300) < 60) & (abs(yy - 120) < 60)
    img[square, :3], img[square, 3] = WHITE * 0.85, 1
    disc = (xx - 200) ** 2 + (yy - 120) ** 2 < 70**2
    img[disc, :3] = np.where((xx[disc] < 200)[:, None], PINK * 0.95, PINK * 0.6)
    img[disc, 3] = 1
    return img


def at(img, x, y):
    return img[y, x, :3]


def test_cartoon_flattens_to_two_spool_tones_with_bold_outlines_on_an_off_white_ground():
    out = cartoon.cartoon(capture())
    assert at(out, 5, 5) == pytest.approx(np.array(cartoon.BACKGROUND) / 255, abs=0.01)  # no grid, flat ground
    lit, shadow = at(out, 170, 120), at(out, 230, 140)
    assert lit == pytest.approx(PINK, abs=0.01) and shadow == pytest.approx(PINK * cartoon.SHADOW, abs=0.01)
    assert at(out, 330, 150) == pytest.approx(WHITE, abs=0.01)  # the dimmed white square is still Pure White
    for x, y in ((130, 120), (268, 100), (359, 120)):  # silhouette, disc over square, square's far edge
        assert at(out, x, y) == pytest.approx((0, 0, 0), abs=0.01), (x, y)
    assert len({tuple(np.round(p, 3)) for p in out.reshape(-1, 3)}) <= 6  # flat: ground, black, 2 tones x 2 parts


def test_ink_keeps_the_shading_and_darkens_only_the_outlines():
    img = capture()
    out = cartoon.ink(img)
    assert at(out, 5, 5) == pytest.approx((1, 1, 1))
    assert at(out, 170, 120) == pytest.approx(PINK * 0.95)  # the render inside a part is untouched
    edge = at(out, 130, 120)
    assert edge.max() < 0.4  # near-black at ~70 % over the white ground
    assert at(out, 125, 120) == pytest.approx((1, 1, 1))  # thin: a few pixels at 480 wide
