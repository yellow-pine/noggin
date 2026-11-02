# Gestures and behaviour

Each gesture as the model plays it: [the home page](../index.md#gestures).

## Which event plays what

<!--{{ behaviour }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
Which Claude Code event plays which gesture is in [the table on the site](https://yellowpine.com/noggin/docs/use/gestures/#which-event-plays-what),
built from the code.
<!-- #}-->

Several sessions share the one Mech; a gesture already playing wins. The gestures live on the Core, so motion stays
smooth whatever the Mac does; the Mac only says which one (ADR 0001). How a hook becomes a gesture is drawn in
[How it works](../how-it-works.md#from-a-hook-to-a-gesture).

## Real eye movements (GazeBase)

Eye movements replay real human recordings; blinks and lids keep toon timing (anticipation, slow in and out, holds,
overshoot and settle).

`eyes/build_trace.py` pulls GazeBase subject 1001, session 1 (CC BY 4.0) with a 7 MB byte-range
fetch and bakes `eyes/gaze_trace.py`: real saccade velocity profiles at 10/20/25° (used by every
dart and return, undershoot and correction included), a 4 s horizontal-scan clip (attention), and a
60 s video-viewing session (thinking, when `think_trace` is 1). Lids are not in the data; blinks and
lids keep toon timing (#258, `docs/research/2026-11-01-toon-eyes.md`; the human kinematics behind it
are in `2026-10-31-natural-eye-motion.md` and `2026-11-01-blink-kinematics.md`). Every move between
keyframes follows minimum jerk, at rest at both ends so nothing rings (#619,
`2026-11-02-literature-motion-control.md`), and each servo gets one write per 20 ms PWM frame, since the
Core's PWM takes a new pulse width only at the next frame. No write asks more of a servo than its rated
428°/s or its acceleration cap: `glide` takes more frames, a big saccade spaces its samples out, a
replayed trace caps each sample's move (`eyes/test_toon.py`). Fixational jitter (±0.5°) is below one
servo step and was dropped.

A jump (a lid pop or snap, a saccade's sample) draws a servo's stall current until it arrives, and seven
at once would ask the one pack for more than its 3 A. So each Core keeps a start budget: at most two
servos jump at once, and a further jump waits, in whole frames, until one has arrived. The noggin service
sends the neck Core each command one frame after the eyes Core, so the two Cores' gestures never start
in the same frame (#620, `2026-11-02-literature-motion-control.md` 4).

## The head joins wide gaze shifts

Once the calibration's `head_share` is above 0, a gaze shift wider than about 15° (eureka's dart, thinking's look
aside, the way back) recruits the neck: the eyes lead, the pan follows two frames later and turns the head to that share
of the gaze, and the eyes counter-rotate as it arrives, so the gaze holds; the eyes move the slower the more of the shift
the head carries, and Rest brings the head back (#688, `eyes/eyes.py` `turn`,
`2026-11-02-literature-synthesis.md` Gestures). Both Cores play the same line and each writes only its own servos, so
the eyes Core counter-rotates against the head the neck Core is turning; the noggin service's frame between them, plus
a Wi-Fi round trip, is the gaze error it costs, which the model holds within 2° (`model/test_traces.py`).
`pan_lo` and `pan_hi` are the pan servo's degrees that turn the head as far as the left eye turns at its own ends
(`pan_lo` above `pan_hi` when the pan runs the other way). Today's Mech keeps `head_share` 0, the eyes alone: its pan
four-bar turns the head the other way, about half a degree per servo degree (the model), and its pan is not calibrated
yet. To try it: `noggin set pan_lo 150`, `noggin set pan_hi 30`, `noggin set head_share 0.6` (the pan's ends inferred).
The next Mech's model plays it at 0.6.
