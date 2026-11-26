# Calibration

Every Mech is calibrated on its own: each servo's horn sits on its spline a tooth either way, and each print fits a
little differently, so no one else's numbers fit yours. The eyes Core's servos (both lids, the yaw and the pitch) are
calibrated in `eyes/calibration.json`, live with `noggin/noggin set` ([Tuning](../use/tuning.md)). Until you calibrate
your own, the file holds the model's nominal ranges, each servo's horn about its 90 neutral (inferred; the
[Wiring](wiring.md#servo-ports) table shows them). *Upcoming (#929): the neck Core's tilt and jaw get a calibration of
their own.*

## What the numbers are

- `<servo>_lo` and `<servo>_hi`: a servo's two ends, in servo degrees, for each servo in the
  [Wiring](wiring.md#servo-ports) table's eyes Core rows. For a lid, `_lo` is closed (where the upper and lower lid meet) and `_hi` open.
- `<lid>_rest`: where each lid servo sits at `lid_rest`, so the two lids can match at rest even when their linkages
  differ.
- Both lids are in one shared frame, the right lid servo's degrees: the two lid servos are mirror-mounted, and the Core
  writes 180 - a to the left one itself, so a matched pair has the same numbers.
- `lid_rest`, `lid_think`, `lid_closed` and `lid_open`: how open the lids are, 0 closed to 1 open, at rest, while
  thinking, in a blink and at their widest.
- `pan_lo`, `pan_hi` and `head_share`: the pan, once the neck is built ([Gestures](../use/gestures.md#the-head-joins-wide-gaze-shifts)).

## The method

Finish [first-run setup](flashing.md#first-run) first: it flashes the Core, joins the Wi-Fi, checks the horns and
nominal motion over USB, then installs the noggin service. That USB check does not save fitted limits. For the steps
below, switch the pack on, run `just start` if the service is stopped, and check `noggin/noggin status` shows the eyes
Core on Wi-Fi or USB. Run every command from the repo on the Mac. Each `set` saves to `eyes/calibration.json` and
re-applies the held pose; it does not flash the Core.

1. **Check the horns at centre.** Hold the servos about their centre
   (`noggin/noggin pose lids 0.5 eyes 90`: lids half open, eyes straight ahead; inferred near each servo's 90), push each horn fully home on its spline, at the tooth nearest
   its part's centre, then its screw. A horn refitted several times wears; use a fresh one.
2. **Select an endpoint before adjusting it.** Use the table below, one row at a time. Read the current value of its
   key in `eyes/calibration.json`, then change it in small steps with `noggin/noggin set <key> <degrees>` (replace
   both placeholders). The held endpoint moves with each change. For the lids, adjust the left and right key
   separately until both eyes match. Start from the model's inferred limits and keep every part clear.

   | Hold this pose | Adjust these keys | What to find |
   |---|---|---|
   | `noggin/noggin pose lids 0` | `l_lid_lo`, `r_lid_lo` | Both lid edges just meet, quietly |
   | `noggin/noggin pose lids 1` | `l_lid_hi`, `r_lid_hi` | The widest clear opening |
   | `noggin/noggin pose eyes 0` | `yaw_lo` | The low yaw endpoint |
   | `noggin/noggin pose eyes 180` | `yaw_hi` | The high yaw endpoint |
   | `noggin/noggin pose pitch 0` | `pitch_lo` | The low pitch endpoint |
   | `noggin/noggin pose pitch 180` | `pitch_hi` | The high pitch endpoint |

   Here `0` and `180` request past the current yaw or pitch range so the Core clamps to its selected endpoint;
   they are not fitted angles or physical stops. `pose eyes 90` centres the yaw and levels the pitch. You can also
   request an angle inside the fitted pitch range, for example `noggin/noggin pose pitch 95`.
3. **Back off inside every stop.** If anything binds or buzzes, move the held limit back towards the centre at once.
   The 9 g servos have a slip clutch: driven into a mechanical stop, it slips and the calibration drifts, which looks
   like the horn sliding on its spline. Keep each endpoint a few degrees inside any stop; do not hold it against one.
4. **Match the rest.** Pose both eyes partly open (`noggin/noggin pose lids 0.3`) and set `l_lid_rest` and
   `r_lid_rest` until both lids show the same part of the pupil. Compare at a half-open pose, not only at the ends: the
   lid bars make equal servo steps unequal lid steps, so a straight line between the ends can't fit both.
5. **Check it moves.** `just demo` plays every gesture; `just demo bored 2` repeats one. Watch the blinks and the wink
   close at the closed end, then `just follow`.

Each `set` is saved to `eyes/calibration.json` and resent to the Core. Run `noggin/noggin exercise 10` for a gentle
run-in once it is fitted.

> [!WARNING]
> **The lids bind at the ends.** Verify a range on your Mech before pushing past it.
