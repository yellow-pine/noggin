# Calibration

The lids and eyes are calibrated per Mech in `eyes/calibration.json`, live with `noggin/noggin set`
([Tuning](../use/tuning.md)).

## Servo calibration lessons (2026-10-31)

- The 9 g servos have a slip clutch. Driving a lid into its
  mechanical stop makes the clutch slip and the calibration drifts, which looks
  like the horn sliding on the spline. Keep every range end a few degrees
  inside the stop; the eye program's lid ranges sit 6° inside.
- Fit horns with all servos held at centre (90): lids half open, eyes straight
  ahead. Push fully home, then the short screw from the servo pack. A horn that
  has been refitted several times is worn; use a fresh one.
- The two lid servos are mirror-mounted (a on one is 180 - a on the other).
  Since #213 `eyes/calibration.json` gives both lids in one shared frame, the
  right lid servo's degrees: `<lid>_lo` closed, `<lid>_rest` where it sits at
  `lid_rest`, `<lid>_hi` open. The Core mirrors the left servo itself, so a
  matched pair has identical numbers. A file with the old `<lid>_flip` keys
  still loads, converted.
- 2026-11-01 (#213): the left lid showed only a slit at rest and thinking while
  the right showed half its pupil. Raising the left lid's open end until rest
  matched broke the near-shut wink: the lid bars make equal servo steps unequal
  lid steps, so a straight line between the ends can't fit. Hence the rest
  point: tune closed, rest and open per lid, and compare both eyes at a
  half-open pose, not only at the ends.
- 2026-11-01 (#255): the lids retuned live in the shared frame. Closed 39 on both (the
  edges just touch, quiet: the two lids read 38 and 40, the midpoint taken), rest 61.4
  (left) / 64 (right, which sat a bit more closed in thinking at the same number), open
  102 (the lid stops opening visibly there; no stop or clutch slip up to 133). At
  `lid_closed` 0.1 the blinks left a clear gap, so `lid_closed` is now 0: blinks and the
  wink close at the closed end, and bored's long closure is 1.5 s (with its ramps it
  stays under the 2 s stall cap). Eyes unchanged, 58..118.
