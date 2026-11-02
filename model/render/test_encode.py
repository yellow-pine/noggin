"""Seam: model/render/pictures.py encode(), a picture's frames as WebP with their alpha (#470)."""

import subprocess

import imageio_ffmpeg
import numpy as np
import pytest

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


def frames(folder, n):
    folder.mkdir(parents=True)
    for i in range(n):  # each its own colour: the encoder merges a frame equal to the one before
        colour = f"color=c=0x{40 * i:02x}0000:s=16x8"
        pictures.ffmpeg("-f", "lavfi", "-i", colour, "-frames:v", "1", str(folder / f"frame{i:04d}.png"))


def test_the_hero_joins_its_shards_frames_into_one_looping_webp(tmp_path, monkeypatch):
    """#537: CI renders the hero's frames on several runners; join encodes them all, in order, as images/hero.webp."""
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    monkeypatch.setattr(pictures, "IMAGES", str(tmp_path / "images"))
    monkeypatch.setattr(pictures, "hero_frames", lambda: 3)
    frames(tmp_path / "frames" / "hero", 3)
    pictures.main("join", [])
    webp = (tmp_path / "images" / "hero.webp").read_bytes()
    assert webp.count(b"ANMF") == 3 and b"ANIM" in webp  # three animation frames (ffmpeg decodes no animated WebP)


def test_the_hero_never_joins_with_a_frame_missing(tmp_path, monkeypatch):
    """ffmpeg's image sequence stops at a gap: a shard's frames lost would ship a short loop."""
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    monkeypatch.setattr(pictures, "IMAGES", str(tmp_path / "images"))
    monkeypatch.setattr(pictures, "hero_frames", lambda: 4)
    frames(tmp_path / "frames" / "hero", 3)
    with pytest.raises(SystemExit, match="hero"):
        pictures.main("join", [])


def test_the_hero_renders_eight_seconds_at_eight_fps():
    """Its frame count, which the shards split, without MuJoCo: model/render/hero.py's 8 s at HERO_FPS."""
    assert pictures.hero_frames() == 64
