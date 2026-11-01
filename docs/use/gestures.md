# Gestures and behaviour

Each gesture as the model plays it: [the home page](../index.md#gestures) and [Pictures](../pictures.md).

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
are in `2026-10-31-natural-eye-motion.md` and `2026-11-01-blink-kinematics.md`). No write asks more of
a servo than its rated 428°/s: `glide` takes more steps, a big saccade spaces its samples out, a
replayed trace caps each sample's move (`eyes/test_toon.py`). Fixational jitter (±0.5°) is below one
servo step and was dropped.
