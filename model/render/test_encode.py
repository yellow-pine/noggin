"""Seam: model/render/pictures.py encode(), each theme's frames as WebP with their alpha (#470)."""

import subprocess

import imageio_ffmpeg
import numpy as np

from model.render import pictures


def test_each_theme_keeps_its_transparent_background_and_its_opaque_part(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    block = "color=c=black@0:s=64x32,format=rgba,geq=r=200:g=0:b=0:a='if(between(X,16,47)*between(Y,8,23),255,0)'"
    for theme in pictures.THEMES:
        (tmp_path / theme / "p").mkdir(parents=True)
        pictures.ffmpeg("-f", "lavfi", "-i", block, "-frames:v", "1", str(tmp_path / theme / "p" / "frame0000.png"))
    pictures.encode("p")
    for theme in pictures.THEMES:
        webp = str(tmp_path / f"p-{theme}.webp")
        raw = subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-loglevel",
                "error",
                "-i",
                webp,
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        img = np.frombuffer(raw, np.uint8).reshape(32, 64, 4)
        assert img[0, 0, 3] == 0 and img[-1, -1, 3] == 0  # the corners stay transparent
        assert img[16, 32, 3] == 255 and img[16, 32, 0] > 150  # the part
