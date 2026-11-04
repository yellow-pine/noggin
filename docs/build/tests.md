# Fit and servo tests

Two hands-on jobs for the next Mech ([#51](https://github.com/yellow-pine/noggin/issues/51)); nothing else waits on
them. The coupon finds the clearance our printer needs before a pivot or a magnet seat relies on one; the video gives
the servo model real motion to be fitted to. Why each: docs/research/2026-11-02-literature-cams-am.md (fits) and
2026-11-02-literature-simulation.md (the servo).

## The clearance coupon

A plate with a 3 mm pin printed loose in each hole and a row of pockets for the shells' 4x2 mm magnet disc. The pins'
clearance steps up from the notched corner, and so do the pockets':

<!--{{ coupon }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Each pin's and pocket's clearance is in [the table on the site](https://yellowpine.com/noggin/docs/build/tests/#the-clearance-coupon),
built from the code (model/printed/coupon.py).
<!-- #}-->

Clearance is per side: a hole is its pin plus twice its clearance across.

1. `just stl` writes `model/build/stl/clearance coupon.stl`. Slice it as it lies, flat, no supports, with the 0.4 mm
   nozzle and the filament's standard profile. Leave the slicer's hole compensation (X-Y hole compensation) as it is
   and note its value: the fit we pick holds only at that setting.
2. Print it twice: once in PETG (the Skeleton's), once in PLA (the Shells').
3. Let each cool. From the notch, turn each pin with a small flat screwdriver in its slot, and write down for each:
   **free** (turns with no effort; it also pushes out from below), **stiff** (turns once broken loose) or **fused**
   (will not turn).
4. If the magnets are in, press a disc into each pocket from the top and write down for each: **drops in**, **finger
   press** or **won't go**. Push it back out with a pin through the hole underneath. The shells' discs will be glued,
   so the tightest pocket a disc drops into square is the one we want.
5. Post both prints' results on [#51](https://github.com/yellow-pine/noggin/issues/51), with the slicer's hole
   compensation and layer height.

## Filming a servo

The servo reports no position, so its motion comes from slow-motion video of a marked horn. One servo, filmed at two
known loads, a Take each; `model/servo_take.py` turns each clip into the file `model/servo_fit.py` fits the model's
servo to.

What you need: the spare servo and a horn, the eyes Core on its Shield and pack, a phone with slow motion, something to
hold it still above the desk (a tripod, a stack of books), a printer, a ruler, tape, glue, a stiff strip about 6 cm
long (a lolly stick, a cut ruler) and ten 2 euro coins (8.50 g each).

1. Set up. Print the marker: `.venv/bin/python -m model.servo_take marker > marker.svg`, opened in a browser and
   printed at 100 % (no "fit to page"): a 12 mm black and white square inside a white margin; check it with the ruler.
   Cut it out with its white margin. Unplug the yaw servo's lead from the Shield's port 2 and plug the spare servo
   in instead. Tape it to the desk with its shaft pointing straight up, so the horn sweeps flat and gravity does not
   load it. Glue the marker flat on the horn, centred over the shaft (anywhere on the horn works, but there it stays
   in frame). Charge the pack.
2. Frame it. The phone straight above the horn, the horn's plane parallel to the screen, close enough that the marker
   is at least a tenth of the picture across, the whole sweep (25 degrees each way) in frame. Daylight or a bright
   lamp: slow motion needs light, and mains lighting can flicker in it. Lock focus and exposure (press and hold on the
   screen) so they don't hunt.
3. Run the take. From the repo on the Mac, with the noggin service running:

   ```
   noggin/noggin pose eyes 90    # centre and hold: Claude Code's hooks are ignored until follow
   ```

   Wait 2 s, start slow motion at the highest frame rate (240 fps), wait another second with the horn still, then:

   ```
   noggin/noggin take            # the moves, 7 s: a slow ramp, then steps both ways a second apart
   ```

   Stop filming a second after the horn's last move. `take` plays the same moves at the same times on the Core's own
   clock every time (eyes/eyes.py `TAKE`), so its writes are known; the slow ramp at its start is what lines the video
   up with them.
4. Take A: the run above with the bare horn.
5. Take B: tape the strip along the horn, the ten coins stacked and taped on it 50 mm from the shaft, the marker
   still clear of them, and read the coins' radius from the shaft with the ruler. The load has to be a few times the
   gear train's own inertia: one coin at the horn's tip barely changes how the servo gets going, and the fit then
   cannot tell the gear train from its other values. Run step 3 again into a second clip.
6. `just follow`, and put the servo back on port 2 when done.

**Where the videos go.** Local only, never git: `docs/references/servo-video/` (docs/references is gitignored). Keep
the original files at their slow-motion frame rate (AirDrop with Options, All Photos Data, or copy from Photos with
"Export Unmodified Original"), named `A.mov` and `B.mov`, and a `notes.md` beside them: the date, which servo, the
coins' radius, the pack's charge and anything that went differently from the steps above.

**Turning them into the fit.** With the coins' mass and radius:

```
.venv/bin/python -m model.servo_take docs/references/servo-video/A.mov 0 0
.venv/bin/python -m model.servo_take docs/references/servo-video/B.mov 85 50   # grams, mm
.venv/bin/python -m model.servo_fit docs/references/servo-video/A.json docs/references/servo-video/B.json
```

The fit writes model/servo_fit.json, which goes in a PR of its own.
