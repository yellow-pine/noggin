"""Seam: model/render/pictures.py encode(), a picture's frames as WebP with their alpha (#470)."""

import json
import os
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


def test_the_site_s_motions_record_their_seconds_as_the_bins_weigh_them(tmp_path, monkeypatch):
    """#569: each motion's seconds in SECONDS/pictures.json, which main's Blender bins upload and the next packing reads
    (model/shards.py); a hero frame shard's as its seconds a frame (those after the first, which compiles Eevee's
    shaders) and the setup every shard pays."""
    monkeypatch.setattr(pictures, "OUT", str(tmp_path))
    monkeypatch.setattr(pictures, "IMAGES", str(tmp_path / "images"))
    monkeypatch.setattr(pictures, "SECONDS", str(tmp_path / "seconds"))
    monkeypatch.setattr(pictures, "MOTIONS", {})
    monkeypatch.setattr(pictures, "render", lambda motion: [20.0, 2.0, 3.0] if motion.startswith("hero") else None)
    pictures.main("site", ["hero:0-3", "views"])
    took = json.loads((tmp_path / "seconds" / "pictures.json").read_text())
    assert sorted(took) == ["blender hero frame", "blender hero setup", "blender views"]
    assert took["blender hero frame"] == 2.5


def panel(path, height, colour):
    path.parent.mkdir(parents=True, exist_ok=True)
    pictures.ffmpeg("-f", "lavfi", "-i", f"color=c={colour}:s=800x{height},format=rgba", "-frames:v", "1", "-c:v",
                    "libwebp", str(path))  # fmt: skip


def size(path):
    probe = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
    ]
    return len(subprocess.run([*probe, "-"], capture_output=True, check=True).stdout) // (800 * 4)


def test_a_prs_preview_stacks_the_live_sites_next_mech_panels_above_its_own(tmp_path, monkeypatch):
    """#649: the preview artifact's before/after panel, the live site's (main's) next Mech panels above this run's, one
    column; a panel the live site lacks yet is left out of the top. Beside it, every picture this run publishes."""
    monkeypatch.setattr(pictures, "IMAGES", str(tmp_path / "images"))
    monkeypatch.setattr(pictures, "PREVIEW_OUT", str(tmp_path / "preview"))
    monkeypatch.setattr(
        pictures, "published", lambda: ["next-mech-side.webp", "next-mech-isometric.webp", "next-x.webp"]
    )
    for f in pictures.published():
        panel(tmp_path / "images" / f, 100, "red")
    panel(tmp_path / "live" / "next-mech-side.webp", 60, "blue")  # the live site has no isometric panel yet
    pictures.compare((tmp_path / "live").as_uri() + "/")
    assert sorted(os.listdir(tmp_path / "preview")) == sorted(["before", "before-after.webp", *pictures.published()])
    assert os.listdir(tmp_path / "preview" / "before") == ["next-mech-side.webp"]
    assert size(tmp_path / "preview" / "before-after.webp") == 60 + 100 + 100
