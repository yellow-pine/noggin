# noggin

An animatronic Mech on the desk that reacts to Claude Code. Today it is a pair
of eyes with lids that do a "just thought of something great" gesture when
Claude finishes a response and a "needs you" scan when Claude is waiting.
The pan-and-tilt base and the mouth come later.

Hardware is PurpleShark's three-part CyberBrick animatronic series on
MakerWorld (eyes: model 1718839). This repo holds the Core program, the Mac-side
noggin service and the Claude Code hooks; see `docs/build-notes.md`, `GLOSSARY.md` and
`docs/adr/`.

## What it does

| Claude Code event | Mech |
|---|---|
| SessionStart | wink (hello) |
| UserPromptSubmit | thinking: lids low, gaze averted, micro-saccades, a blink every 5-8 s |
| Stop | eureka, sized by how long the turn took: under 20 s small, under 3 min normal, longer big |
| Notification permission_prompt | attention: half lids, a real left-right scan |
| Notification idle_prompt | bored: drooping lids, heavy blinks, one long closure |
| StopFailure | wince |
| SessionEnd | back to rest (a turn with no events for 15 min also returns to rest) |

Several sessions share the one Mech; a gesture already playing wins and later ones are dropped.
Eye movements use real human recordings (GazeBase): every saccade follows a recorded velocity
profile, attention replays a scan, bored a calm viewing window; thinking is synthetic drift built
from those saccades unless `think_trace` is on. Blink and lid timing follow the literature in
`docs/research/`. Calibration is live: `eyes/calibration.json`, pushed to the Core by the noggin
service, tuned with `noggin set`.

## License

PolyForm Noncommercial 1.0.0. Copyright Yellow Pine. Free for noncommercial
use; contact Yellow Pine for commercial licensing. See `LICENSE.md`.

## Setup

```
make test            # unit tests
scripts/setup.sh     # guided first-run: plug in the Core, back up, flash, calibrate, install hooks + the noggin service
noggin/noggin off    # mute (on to resume); noggin/noggin eureka 2 for a manual gesture
noggin/noggin pose lids 0.3 eyes 95     # hold a pose while you look
noggin/noggin set lid_rest 0.3           # live calibration, saved to eyes/calibration.json
noggin/noggin exercise 10                # gentle run-in, 10 minutes
make restore-stock   # put Bambu's remote-control program back on the Core
```
