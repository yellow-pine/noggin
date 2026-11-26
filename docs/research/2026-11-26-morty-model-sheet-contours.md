# Morty's contours off his model sheet (2026-11-26)

#991 decided that Morty's colour boundaries come from the show's model sheet: the hairline, each eye white's outline
and lid line, the pupils, the mouth line and the shirt collar. This note records how our control points in
`model/contours.json` were measured. Only those points are committed; the sheet is the studio's art, read for
measurement, kept local (`docs/references/model-sheets/`, gitignored) and never committed or published.

## Source

- Starburns Industries' Morty model sheet, front view beside the turnaround, hosted on the Rick and Morty fandom wiki:
  <https://rickandmorty.fandom.com/wiki/File:Morty_model_sheet.jpg>, image
  <https://static.wikia.nocookie.net/rickandmorty/images/9/9e/Morty_model_sheet.jpg> (already cited in
  `2026-11-03-cartoon-head-proportions.md`). The wiki now sits behind a human check, so Cansin saved it by hand.
- The local copy read: a WebP of 9796 × 4482 px. Views used: the front view (first standing figure in colour) and the
  right-facing side view (third standing figure).

## Method

Every point was read by script off the pixels, not by eye. The sheet paints flat colours with black outlines:

| Region | Colour (sRGB) | Tolerance |
|---|---|---|
| Hair | 131, 84, 29 | 40 |
| Skin | 244, 196, 158 | 30 |
| Eye white | 255, 255, 255, enclosed by an outline | 12 |
| Pupil | 8, 8, 8, inside an eye white | 60 |
| Mouth | 132, 57, 55 | 18 |
| Shirt | 251, 249, 120 | 30 |

1. Each region is the largest connected patch of its colour (an eye white: a white patch not touching the crop's
   edge, its pupil filled in).
2. Each region is grown 9 px, half the measured black outline across the hairline (hair ends at ~279 px, skin starts
   at ~303 px along one row), so a traced edge runs down the line's middle.
3. Each edge is taken as a pixel chain: an eye white's or a pupil's whole outline; the hairline as the hair's outline
   where it meets the (grown) skin; the collar as the shirt's outline where it meets the skin; the mouth line as the
   mouth's top edge, corner to corner.
4. Each chain is smoothed along itself (Gaussian, σ 6 px; 2 px for the pupils and the mouth) and resampled at evenly
   spaced points: 24 per eye white, 8 per pupil, 16 on the hairline, 8 on the mouth line and on the collar.

## Frame

- Unit: the distance between the two eye whites' centres on the front view, 268.3 px. Front eye centres at
  (2629.7, 1932.8) and (2898.0, 1930.2) px.
- Origin: the eyes' midpoint on the front view; on the side view the visible eye white's centre, (6467.5, 1938.3) px
  (its circle's radius 94.8 px, 0.35 units). The two views' eye heights differ by 7 px (0.03 units).
- Axes: x toward Morty's left (image right on the front view), z up, y backward (Morty faces image right on the side
  view, so forward is -y), as in the Mech's head frame (`model/skin.py`).
- Each contour keeps the view it was traced in, front (x, z) or side (y, z), and cuts straight through the head along
  that view's axis.
- Depth: the sheet draws his eyes standing out of his face, while ours sit behind it, so the eyes set no depth. The
  side view's face front, on the midline 0.5 units over the eyes, is at y -0.07 (the outline's outer edge -0.117 and
  its inner edge -0.024 there); a side view's contour moves along y so this point meets the head's own front
  (`FACE_FRONT` in `contours.json`).

## Results (in eye spacings)

- Hairline (side view): from the forehead at (0.24, 0.89), back and down in front of the ear to the nape at
  (1.80, -0.83).
- Eye whites (front view): each about 0.39 units round its eye's centre, nearly round; 0.22 units apart at their
  inner edges.
- Lid lines: the neutral sheet draws no lids, so each eye white's outline is its lid line too: its upper arc the upper
  lid's free edge at rest, its lower arc the lower lid's (inferred).
- Pupils (front view): dots about 0.06 units across, at (±0.55, -0.01) for L/R, a little outward of each eye's centre.
- Mouth line (front view): the mouth's top edge from (-0.19, -0.90) to (0.29, -0.89), its middle at z -0.84.
- Collar (side view): from under the chin at (0.55, -1.42) back to (1.41, -1.29).

## Limits

- Each point is good to about the outline's half-width, 9 px or 0.03 units.
- The side view's collar starts under the chin: the chin hides the neck's front, so the collar runs on level forward
  of its first point (inferred).
- The sheet is one drawing of a 2D character; the sculpt and the Shells have their own proportions, so the contours
  land where the sheet puts them relative to the eyes and the face front, not on the sculpt's own sculpted hair edge.
