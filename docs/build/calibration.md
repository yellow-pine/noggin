# Calibration

Every Mech is calibrated on its own: each servo's horn sits on its spline a tooth either way, and each print fits a
little differently, so no one else's numbers fit yours. The eyes Core's servos (both lids, the yaw and the pitch) and
the neck Core's pan, tilt and jaw are
calibrated in `eyes/calibration.json`, live with `noggin/noggin set` ([Tuning](../use/tuning.md)). Until you calibrate
your own, the file holds the model's nominal ranges, each servo's horn about its 90 neutral (inferred; the
[Wiring](wiring.md#servo-ports) table shows them).

## What the numbers are

- `<servo>_lo` and `<servo>_hi`: a servo's two ends, in servo degrees, for each servo in the
  [Wiring](wiring.md#servo-ports) table. For a lid, `_lo` is closed (where the upper and lower lid meet) and `_hi` open.
  The jaw uses `mouth_lo` closed and `mouth_hi` open; its horn turns backwards to open, so `_hi` may be smaller.
- `<lid>_rest`: where each lid servo sits at `lid_rest`, so the two lids can match at rest even when their linkages
  differ.
- Both lids are in one shared frame, the right lid servo's degrees: the two lid servos are mirror-mounted, and the Core
  writes 180 - a to the left one itself, so a matched pair has the same numbers.
- `lid_rest`, `lid_think`, `lid_closed` and `lid_open`: how open the lids are, 0 closed to 1 open, at rest, while
  thinking, in a blink and at their widest.
- `pan_lo`, `pan_hi` and `head_share`: the pan, once the neck is built ([Gestures](../use/gestures.md#the-head-joins-wide-gaze-shifts)).
- `tilt_rest`: the head's resting tilt, in servo degrees. Hold it with `pose tilt <degrees>` while finding the two
  ends, then set its rest. `pose jaw <0-1>` holds the jaw between closed and open; its closed position is a motion
  endpoint, not a servo hard stop. Keep each fitted endpoint inside any physical stop.

## The method

1. **Fit the horns at centre.** With the noggin service running, hold the servos about their centre
   (`noggin/noggin pose lids 0.5 eyes 90`: lids half open, eyes straight ahead; inferred near each servo's 90), push each horn fully home on its spline, at the tooth nearest
   its part's centre, then its screw. A horn refitted several times wears; use a fresh one.
2. **Find each end, then back off.** The 9 g servos have a slip clutch: driven into a mechanical stop, the clutch
   slips and the calibration drifts, which looks like the horn sliding on its spline. Step a servo towards an end with
   `noggin/noggin set <servo>_lo <degrees>` (or `_hi`) until its part reaches where you want it or just touches a stop,
   then keep the end a few degrees inside it.
3. **Close the lids.** Lower `l_lid_lo` and `r_lid_lo` until the lid edges just touch, quietly, both eyes alike.
4. **Open the lids.** Raise `_hi` until the lid stops opening visibly, inside any stop.
5. **Match the rest.** Pose both eyes partly open (`noggin/noggin pose lids 0.3`) and set `l_lid_rest` and
   `r_lid_rest` until both lids show the same part of the pupil. Compare at a half-open pose, not only at the ends: the
   lid bars make equal servo steps unequal lid steps, so a straight line between the ends can't fit both.
6. **The eyes.** Set `yaw_lo`, `yaw_hi`, `pitch_lo` and `pitch_hi` so the eyes reach their widest look with every
   part clear (the model's nominals are where every part sweeps clear in the model).
7. **Check it moves.** `just demo` plays every gesture; `just demo bored 2` repeats one. Watch the blinks and the wink
   close at the closed end, then `just follow`.

Each `set` is saved to `eyes/calibration.json` and resent to the Core. Run `noggin/noggin exercise 10` for a gentle
run-in once it is fitted.

> [!WARNING]
> **The lids bind at the ends.** Verify a range on your Mech before pushing past it.
