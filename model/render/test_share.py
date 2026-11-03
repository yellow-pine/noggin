"""Seam: model/render/pictures.py share(), the pictures one of Checks' Render shards renders (#770), balanced on each
one's measured Blender seconds (#839, model/shards.py renders)."""

from model.render import pictures

# a worked example: three slow pictures and four quick ones, as seconds
SECONDS = {"long.webp": 92, "mid.webp": 56, "short.webp": 50, "a.webp": 1, "b.webp": 1, "c.webp": 1, "d.webp": 1}


def test_the_shards_render_every_picture_once():
    shares = [pictures.share(SECONDS, i, 3) for i in range(3)]
    assert sorted(f for s in shares for f in s) == sorted(SECONDS)


def test_each_picture_goes_longest_first_to_the_lightest_shard():
    assert [pictures.share(SECONDS, i, 3) for i in range(3)] == [
        ["long.webp"],
        ["mid.webp"],
        ["short.webp", "a.webp", "b.webp", "c.webp", "d.webp"],
    ]
