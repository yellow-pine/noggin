# Morty's contours off his model sheet (2026-11-26)

#991 decided that Morty's colour boundaries come from the show's model sheet: the hairline, each eye white's outline
and lid line, the pupils, the mouth line and the shirt collar. This note records how our control points in
`model/contours.json` were measured. Only those points are committed; the sheet is the studio's art, read for
measurement, kept local (`docs/references/model-sheets/`, gitignored) and never committed or published.

Amended on 2026-11-27 (below, "The sculpt's own boundaries"): Cansin reviewed the result and decided that where the
Morty sculpt shows a form, the sculpt sets the boundary. The hairline and the eye whites are now measured on the sculpt;
the pupils, the mouth line and the collar stay the sheet's.

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
  inner edges. Replaced on 2026-11-27 by the sculpt's eye domes (below); these points are no longer in the data file.
- Lid lines: the neutral sheet draws no lids, so each eye white's outline was taken as its lid line too (inferred).
  Dropped on 2026-11-27: no lid has a cut, the lids are the mechanism's moving covers.
- Pupils (front view): dots about 0.06 units across, at (±0.55, -0.01) for L/R, a little outward of each eye's centre.
- Mouth line (front view): the mouth's top edge from (-0.19, -0.90) to (0.29, -0.89), its middle at z -0.84.
- Collar (side view): from under the chin at (0.55, -1.42) back to (1.41, -1.29).

## Limits

- Each point is good to about the outline's half-width, 9 px or 0.03 units.
- The side view's collar starts under the chin: the chin hides the neck's front, so the collar runs on level forward
  of its first point (inferred).
- The sheet is one drawing of a 2D character; the sculpt has its own proportions, so the sheet's contours land where
  the sheet puts them relative to the eyes and the face front, not on the sculpt's own forms. That is what the review
  of 2026-11-27 showed on the hairline and the eye whites, and why those two are now measured on the sculpt.

## The sculpt's own boundaries (2026-11-27)

Cansin's decision after reviewing the sheet's contours on the sculpt (#992, #893's directive of 2026-11-27): the
hairline sits where the sculpt's own hair volume starts, each eye white is its whole eye dome, and no lid ring is
painted. The cuts are made once, on the sculpt's skin, and the same cuts colour the review and split the printed
Shells (`skin.cuts()` in `model/skin.py`).

### Source and frame

- The Morty sculpt the review's reference is made from (909,718 triangles; local under `docs/references/morty/`, its
  source and licence in the `SOURCE.md` beside it, until #850 adopts it into the repo), read as it was downloaded.
- Frame: the head's, as above. The sculpt's eye centres (`MORTY_EYES` in `model/review`) sit on the Mech's, and the
  sculpt is scaled so their spacing is one unit (72.7 mm, a factor of 7.126 from the file's millimetres).

### Method

Every point was read by script off the mesh. A form's foot on a sculpt is a concave crease, so:

1. Creases: every mesh edge whose two faces meet concave by more than 10°, taken at its midpoint.
2. Hairline (side view, both halves of the head on one (y, z) plane): the crease points on the outer surface (within
   2.5 mm of the head's half-width at that y and z). Under the brows (z 27 to 56 mm) the sculpt has noisy inner faces,
   so only points at least 66 mm from the midline count there. Along a rough guide through the crease, at stations
   1 mm apart, the trace takes the median of the crease points within 1.5 mm across it, four passes.
3. Eye whites (front view): the crease points in front of the eyes, 31.5 to 35.3 mm from each dome's centre (a brow's
   own creases start past 35 mm). The trace takes their median radius in 120 stations of 3° round the centre.
4. Smoothing, as on the sheet: each trace is smoothed along itself (Gaussian, σ 4 mm on the hairline, 9° on a dome)
   and resampled at evenly spaced points, 16 on the hairline and 24 on each dome, the sheet's counts.

### Results

- Hairline: 203 mm long. It starts on the midline at the top of the forehead, at (0.2, 74.9) mm, runs back and down
  to the top of the ear, round the back of the ear, and straight down to (84.4, -94.0) mm, where it meets the collar's
  crease. Behind that end the hair covers the whole back of the head, down to the collar.
- The hair's crease lies on one side-view line right across the head: on the midline it is at (0.1, 74.7) mm and
  50 mm out at (9.7, 64.9) mm, both on the trace. So one curve swept across the head cuts it.
- Fit: the curve through the 16 points stays within 1.06 mm of the trace (0.20 mm on average). The 3,919 crease points
  within 4 mm of it lie 0.27 mm off it at the median and 0.73 mm at the 90th percentile.
- Against the sheet's hairline, as it lay on the sculpt: at the temple (y 36 mm) the sculpt's hair starts at z 42 mm,
  where the sheet's line ran at 51 mm; on the midline the sculpt's starts at 75 mm, where the sheet's crossed the
  forehead near 69 mm. The sheet's line ended at the nape, at (117.5, -60.0) mm, 33 mm behind and 34 mm above the
  sculpt's end, which left the back of the head under it without hair.
- Eye domes: nearly round, radius 33.9 mm (0.47 units; 33 to 35 mm round each), centred at (40.5, 2.2) and
  (-39.7, 2.1) mm, so about 4 mm outward of the Mech's eyes and 2 mm above them. Each curve stays within 0.37 mm of
  its trace. The sheet's eye whites were 0.39 units in radius, 5.5 mm smaller.
- The sculpt also sculpts a pupil ring (radius 7.0 mm, centred at (43.1, 1.5) and (-41.9, 1.7) mm), a mouth and a
  collar. Cansin's decision keeps the sheet's for these three, so they are recorded here and not used.
- The sculpt's face front: on the midline 0.5 units over the eyes its surface is at y -18.4 to -18.6 mm. The review
  of 2026-11-26 measured -18.7 mm on its lighter copy of the mesh and moved the sheet's side view 13.6 mm forward to
  meet it. `sculpt face front` in `contours.json` is -0.257 units (-18.7 mm), so the collar stays where that review
  put it.

### Limits

- Each sculpt-measured point is good to about 1 mm, the curve's worst distance from its trace.
- Under the brows the hairline's crease is read at the temples alone, and a dome's foot under a brow is read from the
  crease points nearest the dome's own radius (inferred from the dome being round everywhere else).
- The sheet's collar is level behind the neck, while the sculpt's own collar drops there. Between the two, at the back
  of the neck, the fixed body is painted as shirt where the sculpt has hair.
