# Morty Smith [Rick and Morty], by ChelsCCT: CC BY 4.0

`sculpt.ply` in this folder is **not under the repo's PolyForm Noncommercial licence** (`LICENSE.md` at the root). It is
adapted from [Morty Smith [Rick and Morty]](https://www.printables.com/model/13460-morty-smith-rick-and-morty) by
ChelsCCT (Chelsey Creates Things), shared under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/), and stays under that
licence. Our reading of the licence and of the page, source by source:
docs/research/2026-11-27-morty-sculpt-licence.md.

The licence covers the sculptor's mesh alone. Morty Smith is a character of Rick and Morty, Adult Swim's (Warner Bros.
Discovery), and no licence here grants any right in the character or its name; this is a fan project, not affiliated
with or endorsed by them or by the sculptor (docs/adr/0027).

Changes from the original (`morty-fixed.stl`, 909,718 triangles, downloaded 2026-11-03; #850, 2026-11-27):

- `sculpt.ply`: the whole figure decimated to 220,000 triangles in Blender (its Decimate modifier, collapse) and saved as
  a binary PLY, by `adopt.py`. Nothing else: the original's frame and millimetres (z up, his feet on z 0), one closed
  surface as the original is.
- How far the copy strays from the original, as `adopt.py` measured it, in the original's millimetres and at the
  Mech's life size (about 7.13 times, the Mech's eye spacing over the sculpt's):

  | | mean | 99th percentile | most |
  | --- | --- | --- | --- |
  | the original's every vertex to the copy | 0.0012 mm (0.009) | 0.0046 mm (0.033) | 0.111 mm (0.79) |
  | the copy, seven points a triangle, to the original | 0.0010 mm (0.007) | 0.0043 mm (0.031) | 0.027 mm (0.20) |

  So the copy's surface lies within 0.2 mm of the original everywhere at life size, a print layer. The other way, 126
  of the original's 453,906 vertices (inferred: small creases the decimation smoothed over) lie further than that from the copy,
  the furthest in the head at (79.8, 253.9, 113.8).

From #850 the model builds Morty's Skin from it: scaled to the Mech, cut at the base and along its seams into
Shells, each with a wall grown inward. Every such adaptation it writes, the Shells' print files, pictures and GLBs, is
shared under the same licence, with this credit.
