"""Post-process for the model renders (docs/model-notes.md). Fusion captures with a transparent background (no grid);
every pixel is snapped to a part colour class: the spools of geometry.SPOOLS by chromaticity, the neutrals split by
brightness into Pure White, hardware grey (servos, boards, battery: their own flat tone) and black (spool black and the
STEP darks), plus brass for the servo labels. Part boundaries are where the class changes or the shading jumps.
ink(): the engineering style, Fusion's shading kept, thin near-black outlines (2 px at 480 wide, 70 %) on white.
cartoon(): the README style, two flat tones per class (lit, and SHADOW darker below the class's mean brightness in
the frame), bold black outlines (3 px at 480 wide), flat off-white ground. Images are float RGBA arrays 0..1;
`python -m model.cartoon ink|cartoon <png>...` restyles captures in place, the originals kept in raw/."""

import os
import shutil
import struct
import subprocess
import sys

import numpy as np
from scipy import ndimage

from model import geometry as g

BACKGROUND = (0xF7, 0xF4, 0xEE)
SHADOW = 0.75
JUMP = 0.12  # a luminance step this big between neighbours is a part boundary even within one colour class


def _rgb(h):
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)]) / 255


CHROMATIC = {"Milky Pink": _rgb(g.SPOOLS["Milky Pink"]), "Apricot": _rgb(g.SPOOLS["Apricot"]), "brass": _rgb("#B4A86A")}
NEUTRAL = {"Pure White": (0.62, _rgb(g.SPOOLS["Pure White"])), "hardware grey": (0.22, _rgb("#9C9C9C"))}
BLACK = _rgb("#2E2E2E")  # Absolute Black's lit tone: pure black would swallow the outlines
NAMES = [*CHROMATIC, *NEUTRAL, "Absolute Black"]
COLOURS = np.array([*CHROMATIC.values(), *(c for _, c in NEUTRAL.values()), BLACK])


def classes(img):
    """Per pixel index into NAMES, -1 where the capture is transparent."""
    rgb = img[..., :3]
    bright = rgb.max(axis=2)
    chroma = rgb / np.maximum(bright, 1e-6)[..., None]
    refs = np.array([c / c.max() for c in CHROMATIC.values()] + [np.ones(3)])
    nearest = np.linalg.norm(chroma[..., None, :] - refs, axis=3).argmin(axis=2)
    neutral = nearest == len(CHROMATIC)
    label = np.where(neutral, len(NAMES) - 1, nearest)
    for i, (floor, _) in reversed(list(enumerate(NEUTRAL.values()))):
        label[neutral & (bright >= floor)] = len(CHROMATIC) + i
    label[bright < 0.18] = len(NAMES) - 1
    label[img[..., 3] < 0.5] = -1
    return ndimage.median_filter(label, 3)  # drops single-pixel speckle at anti-aliased seams


def edges(img, label, px_at_480):
    """Boundary band about px_at_480 * width / 480 wide: class changes (silhouettes included) and luminance jumps."""
    size = max(2, round(px_at_480 * img.shape[1] / 480)) + 1
    band = ndimage.maximum_filter(label, size) != ndimage.minimum_filter(label, size)
    lum = img[..., :3].mean(axis=2)
    jump = (ndimage.maximum_filter(lum, 3) - ndimage.minimum_filter(lum, 3)) > JUMP
    jump &= label >= 0
    grow = size // 2 - 1
    return band | (ndimage.binary_dilation(jump, iterations=grow) if grow else jump)  # iterations=0 floods


def ink(img):
    """Fusion's shading on white with thin near-black outlines at 70 %."""
    label = classes(img)
    out = np.where((label >= 0)[..., None], img[..., :3], 1.0)
    line = edges(img, label, 2)[..., None]
    return np.where(line, out * 0.3 + 0.08 * 0.7, out)


def cartoon(img):
    """Two flat tones per class, bold black outlines, off-white ground."""
    label = classes(img)
    bright = img[..., :3].max(axis=2)
    out = np.broadcast_to(np.array(BACKGROUND) / 255, img.shape[:2] + (3,)).copy()
    for i, colour in enumerate(COLOURS):
        mask = label == i
        if mask.any():
            lit = ndimage.median_filter(bright >= bright[mask].mean(), max(3, img.shape[1] // 160))
            out[mask & lit] = colour
            out[mask & ~lit] = colour * SHADOW
    out[edges(img, label, 3)] = 0.0
    return out


def read(path):
    data = open(path, "rb").read(24)
    w, h = struct.unpack(">II", data[16:24])
    cmd = ["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgba", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4) / 255


def write(path, rgb):
    h, w = rgb.shape[:2]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-i", "-"]
    data = (np.clip(rgb, 0, 1) * 255).round().astype(np.uint8).tobytes()
    subprocess.run([*cmd, path], input=data, check=True)


def main(style, paths):
    """Rewrite each capture in the style, keeping the transparent original in raw/ beside it (cartoon() needs it)."""
    for p in paths:
        img = read(p)
        if img[..., 3].min() == 1:
            continue  # already styled: captures come transparent
        raw = os.path.join(os.path.dirname(p), "raw")
        os.makedirs(raw, exist_ok=True)
        shutil.copy(p, raw)
        write(p, (ink if style == "ink" else cartoon)(img))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
