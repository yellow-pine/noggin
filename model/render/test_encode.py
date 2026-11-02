"""Seam: model/render/pictures.py encode(), a picture's frames as WebP with their alpha (#470)."""

import subprocess

import imageio_ffmpeg
import numpy as np

from model.render import pictures


def test_the_webp_keeps_the_transparent_background_and_the_opaque_part(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    block = "color=c=black@0:s=64x32,format=rgba,geq=r=200:g=0:b=0:a='if(between(X,16,47)*between(Y,8,23),255,0)'"
    (tmp_path / "frames" / "p").mkdir(parents=True)
    pictures.ffmpeg("-f", "lavfi", "-i", block, "-frames:v", "1", str(tmp_path / "frames" / "p" / "frame0000.png"))
    pictures.encode("p")
    ffmpeg = [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(tmp_path / "p.webp")]
    raw = subprocess.run([*ffmpeg, "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    img = np.frombuffer(raw, np.uint8).reshape(32, 64, 4)
    assert img[0, 0, 3] == 0 and img[-1, -1, 3] == 0  # the corners stay transparent
    assert img[16, 32, 3] == 255 and img[16, 32, 0] > 150  # the part
