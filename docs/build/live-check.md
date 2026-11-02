# Live check

Both Cores on the Mech, end to end ([#29](https://github.com/yellow-pine/noggin/issues/29)): each Core flashed over
USB and over Wi-Fi, then probed over Wi-Fi with the cable in, with the cable out and after the Mech was off. Run it
once Core 2 is set up as the neck Core (`scripts/setup.sh`, answering `neck`), and again after a change to the Link.

```
just start         # the noggin service, from this checkout
just live-check    # asks you to plug, unplug and switch; the rest runs itself
```

It plugs nothing in and switches nothing itself: it asks, you do it and press Return. Each Core goes on USB alone in
turn for `just flash-usb` (which stops the noggin service; the check starts it again) and must beacon the new program
within 90 s. Then `noggin/noggin flash eyes` and `noggin/noggin flash neck` send each Core the program over Wi-Fi (plain
`noggin/noggin flash`, as `just flash` runs it, is the eyes Core's). A probe sends `wink 3`, which both
Cores play, and reads `noggin.log` for each Core's ack over Wi-Fi: with the cable in, with every cable out, and once
the Mech was switched off (both Cores offline within 32 s, the beacon's stale window plus 10 s) and on again (both
back on Wi-Fi within 90 s). Each run appends its results below as a dated table, ok or FAIL per step and Core with
what `noggin status` and the log said; commit them in a PR.
