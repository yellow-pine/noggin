# A single Daemon owns the Link; hooks only poke it

Claude Code hooks could open the USB serial port directly, but several sessions finishing together would fight over the port, and a hook that waits on a serial handshake slows every Claude response. Instead a launchd-managed Daemon holds the Link open and listens on a Unix socket; each hook writes one gesture name to the socket and exits immediately. The Daemon enforces Busy (drop while playing) and tolerates the Core being unplugged or unpowered.

## Considered options

- Direct from hook: simplest, rejected for port contention and hook latency.
- Queue instead of drop: rejected; stacked gestures look twitchy and carry stale meaning.
