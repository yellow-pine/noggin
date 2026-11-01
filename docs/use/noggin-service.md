# The noggin service

A small Mac service (launchd) that takes Claude Code's hooks, decides which gesture to play and sends it to the Cores
over the Link: Wi-Fi first, USB-C as fallback (ADR 0003, ADR 0005). Drawn in [How it works](../how-it-works.md).

## Commands

```
make install         # host side only: hooks + the noggin service
make start / stop    # (re)start or stop the noggin service; stop frees the Link for mpremote
noggin/noggin status # mode (follow, demo or pose), Link (Wi-Fi or USB) per Core
noggin/noggin off    # mute (on to resume); noggin/noggin eureka 2 for a manual gesture
make demo            # demo mode: every gesture on a loop, 5 s apart, hooks ignored (ARGS=once, ARGS="bored 2")
make follow          # follow mode: react to Claude Code again, from demo or pose (the default, and the mode after any restart)
make stl / step      # our printed parts as print-ready STLs (model/build/stl); STEP files of every part and Stage
make render / gifs / hero   # the model's pictures (docs/model-notes.md)
```

Posing, live calibration and the run-in are under [Tuning](tuning.md); flashing and the Wi-Fi under
[Flashing](../build/flashing.md).

## Wi-Fi Link timing (2026-10-31, #104)

Seen live on the eyes Core: the Wi-Fi Link gave up on the startup calibration batch every time, and `wink 3` played
but logged `no ack`. Two causes. A gesture blocks the Core for about a second, and the Core used to ack only after the
line had run, past the noggin service's 2 x 200 ms window. And WLAN power save was on (MicroPython's default, ping RTT
about 60 ms), so the access point held the first datagrams and ARP after a quiet spell. The Core now acks on receipt
and sets `pm=PM_NONE`, and a line that Wi-Fi does not deliver goes over USB when the cable is in (ADR 0005). Checked on the
Mech 2026-10-31 (eyes Core at 192.168.68.55, cable out, noggin service restarted): the calibration batch is acked
over Wi-Fi, `wink 3` is acked and the left eye winks, and the six gestures played over Wi-Fi alone (`demo once`).

## Live check on the eyes Core alone (2026-11-01, #177)

Eyes Core on a new network (192.168.178.141; the Core only knew last night's Wi-Fi, so the Link was silent until the
Wi-Fi step ran again, see #195), noggin service and program from main (9075717), `noggin demo` looping:
- Cable out: every gesture kept playing over Wi-Fi. The unplug left the eyes offline for about 12 s and dropped one
  gesture until the next beacon (#196).
- Wi-Fi flash: `noggin flash` installed main's program (back in 3 s). A deliberately broken `eyes.mpy` never reached
  `noggin ready`; the Core went back to its .bak files and its beacon returned. `make flash` once misread the beacon
  as stale, fell back to `flash-usb` with no cable and stopped the noggin service (#196).
- USB fallback: with Wi-Fi unreachable (wrong network) and the cable in, the service found the Core on serial, sent the
  calibration and gestures, and the Core answered.
- Mech off 20 s, cable out: the Link came back by itself (beacon, uptime 11 s), but nothing was logged for the Wi-Fi
  outage (#196).

## Cable-out check of the Link fixes (2026-11-01, #212)

Eyes Core on the home network (192.168.68.61), program and noggin service from main after #196, #200 and #205:
- Cable pulled during a gesture in `noggin demo`: `Link lost` at 14:11:50, the next gesture went `sent eyes` 5 s later,
  nothing dropped (#196).
- Cable out, `bored 2` and `wink 1` 3 s into it: both acked over Wi-Fi, the wink played right after bored (#205).
- Mech off 30 s, cable out: `eyes beacon stale for 22.0 s`, then `eyes beacon back: wifi ... uptime 8s` and the
  calibration resent (#196).
- The Core joined the home network from its list of two (#195).
