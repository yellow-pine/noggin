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
2. Print it twice: once in black PETG (the skeleton's), once in PLA Pure (the shells').
3. Let each cool. From the notch, turn each pin with a small flat screwdriver in its slot, and write down for each:
   **free** (turns with no effort; it also pushes out from below), **stiff** (turns once broken loose) or **fused**
   (will not turn).
4. If the magnets are in, press a disc into each pocket from the top and write down for each: **drops in**, **finger
   press** or **won't go**. Push it back out with a pin through the hole underneath. The shells' discs will be glued,
   so the tightest pocket a disc drops into square is the one we want.
5. Post both prints' results on [#51](https://github.com/yellow-pine/noggin/issues/51), with the slicer's hole
   compensation and layer height.

## Filming a servo

The servo reports no position, so its motion comes from slow-motion video of a marked horn. One servo, filmed once, at
two known loads; `model/servo_fit.py` fits the model's servo to it (its docstring has the take files it reads).

What you need: the spare servo and a horn, the eyes Core on its Shield and pack, a phone with slow motion, something to
hold it still above the desk (a tripod, a stack of books), a black marker, a printed protractor or angle scale, a ruler,
tape, a stiff strip about 6 cm long (a lolly stick, a cut ruler) and ten 2 euro coins (8.50 g each).

1. Set up. Unplug the right eye servo's lead from the Shield's port 4 and plug the spare servo in instead. Lay it on
   the paper scale with its shaft pointing straight up, so the horn sweeps flat and gravity does not load it, and tape
   it down. Draw a bold black line along the horn from the shaft to its tip, and a dot at the tip. Charge the pack.
2. Frame it. The phone straight above the horn, the horn's plane parallel to the screen, the whole sweep, the scale
   and the ruler in frame. Daylight or a bright lamp: slow motion needs light, and mains lighting can flicker in it.
   Lock focus and exposure (press and hold on the screen) so they don't hunt.
3. Run the moves. Start slow motion at the highest frame rate (240 fps), then, from the repo on the Mac, with the noggin
   service running:

   ```
   noggin/noggin pose eyes 90    # centre, then wait 2 s
   noggin/noggin pose eyes 115   # a big step; wait 2 s after each
   noggin/noggin pose eyes 65
   noggin/noggin pose eyes 115
   noggin/noggin pose eyes 95    # small steps
   noggin/noggin pose eyes 85
   noggin/noggin pose eyes 89    # one degree: does it move at all?
   noggin/noggin pose eyes 90
   just follow                   # back to reacting to Claude Code
   ```

   Each `pose eyes` ramps the eyes evenly in 20 ms steps over 150 ms (eyes/eyes.py), so a step is a known ramp; the
   fit finds the delay between the command and the horn itself. One clip for the whole run is fine.
4. Load A: the run above with the bare horn.
5. Load B: tape the strip along the horn's line, the ten coins stacked and taped on it 50 mm from the shaft, and
   read their radius from the shaft on the scale. The load has to be a few times the gear train's own inertia: one
   coin at the horn's tip barely changes how the servo gets going, and the fit then cannot tell the gear train from
   the delay.
   Run the same moves again into a second clip.
6. Put the servo back on port 4 when done.

**Where the videos go.** Local only, never git: `docs/references/servo-video/` (docs/references is gitignored). Keep
the original files at their slow-motion frame rate (AirDrop with Options, All Photos Data, or copy from Photos with
"Export Unmodified Original"), named `A.mov` and `B.mov`, and a `notes.md` beside them: the date, which servo, the
coins' radius, the pack's charge and anything that went differently from the steps above.
