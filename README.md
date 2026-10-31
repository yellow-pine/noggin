# noggin

An animatronic Mech on the desk that reacts to Claude Code. Today it is a pair
of eyes with lids that do a "just thought of something great" gesture when
Claude finishes a response and a "needs you" scan when Claude is waiting.
The pan-and-tilt base and the mouth come later.

Hardware is PurpleShark's three-part CyberBrick animatronic series on
MakerWorld (eyes: model 1718839). This repo holds the Core program, the Mac
daemon and the Claude Code hooks; see `docs/build-notes.md`, `GLOSSARY.md` and
`docs/adr/`.

## License

PolyForm Noncommercial 1.0.0. Copyright Yellow Pine. Free for noncommercial
use; contact Yellow Pine for commercial licensing. See `LICENSE.md`.

## Setup

```
make test            # unit tests
scripts/setup.sh     # guided first-run: plug in the Core, back up, flash, calibrate, install hooks + daemon
daemon/noggin off    # mute (on to resume); daemon/noggin eureka 2 for a manual gesture
daemon/noggin pose lids 0.3 eyes 95     # hold a pose while you look
daemon/noggin set lid_rest 0.3           # live calibration, saved to eyes/calibration.json
daemon/noggin exercise 10                # gentle run-in, 10 minutes
make restore-stock   # put Bambu's remote-control program back on the Core
```
