# The noggin service

A small Mac service (launchd) that takes Claude Code's hooks, decides which gesture to play and sends it to the Cores
over the Link: Wi-Fi first, USB-C as the eyes Core's fallback (ADR 0003, ADR 0005). Drawn in [How it works](../how-it-works.md).

## Commands

```
just install         # host side only: hooks + the noggin service
just start / stop    # (re)start or stop the noggin service; stop frees the Link for mpremote
noggin/noggin status # Link (Wi-Fi or USB) and program version per Core, the service's version, the last pack cut (charge the pack), the mode (follow, demo or pose)
noggin/noggin off    # mute (on to resume); noggin/noggin eureka 2 for a manual gesture
just demo            # demo mode: every gesture on a loop, 5 s apart, hooks ignored (just demo once, just demo bored 2)
just follow          # follow mode: react to Claude Code again, from demo or pose (the default, and the mode after any restart)
just stl / step      # our printed parts as print-ready STLs (model/build/stl); STEP files of every part and document
just render          # the model's pictures (docs/model-notes.md)
```

Posing, live calibration and the run-in are under [Tuning](tuning.md); flashing and the Wi-Fi under
[Flashing](../build/flashing.md).

## The Link

Each Core joins your Wi-Fi and beacons every 2 s, so the noggin service learns its address; the Core acks each line on
receipt, before it plays it, and keeps WLAN power save off, so a line after a quiet spell isn't held. A line Wi-Fi does
not deliver goes over USB when the eyes Core's cable is in, and a neck line is dropped ([How it works](../how-it-works.md#the-link)).
`noggin/noggin status` shows which way each Core is reached. With the cable out the gestures keep playing over Wi-Fi;
after the Mech is switched off and on, each Core's beacon comes back by itself and the noggin service resends the
calibration.

Both Cores together, end to end: `just live-check` ([Live check](../build/live-check.md)).
