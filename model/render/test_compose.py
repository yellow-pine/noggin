"""Seam: model/render/pictures.py compose(), which lays the lines over the parts per theme as WebP with alpha (#470)."""

import subprocess

import imageio_ffmpeg
import numpy as np

from model.render import pictures


def rgba(path, w, h):
    raw = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4)


def test_each_theme_keeps_the_transparent_background_and_draws_its_line_colour(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    box = "color=c=black@0:s=64x32,format=rgba,geq=r={r}:g=0:b=0:a='if(between(X,{a},{b})*between(Y,8,23),255,0)'"
    for layer, r, a, b in [("parts", 200, 16, 47), ("lines", 0, 12, 15)]:  # a red block, a line left of it
        (tmp_path / layer).mkdir()
        pictures.ffmpeg(
            "-f", "lavfi", "-i", box.format(r=r, a=a, b=b), "-frames:v", "1", str(tmp_path / layer / "p.png")
        )
    pictures.compose("p.png", str(tmp_path / "p"))
    for theme, colour in pictures.THEMES.items():
        img = rgba(str(tmp_path / f"p-{theme}.webp"), 64, 32)
        assert img[0, 0, 3] == 0 and img[-1, -1, 3] == 0  # the corners stay transparent
        assert img[16, 32, 3] == 255 and img[16, 32, 0] > 150  # the part
        line = [int(colour[k : k + 2], 16) for k in (1, 3, 5)]
        assert img[16, 13, 3] == 255 and np.abs(img[16, 13, :3].astype(int) - line).max() < 24  # its line
