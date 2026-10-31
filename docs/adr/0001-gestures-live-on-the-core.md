# Gestures live on the Core, not on the Mac

The Mac could stream servo angles over the Link in real time, or the Core could hold named gestures and play them on a one-word command. We chose the latter: gestures are MicroPython on the Core, and the Daemon only sends names. Motion stays smooth if the Mac stutters or the Daemon restarts, the Link protocol is one line of text, and tuning a gesture by eye means editing one file on the board rather than two moving parts.

## Consequences

- Tuning a gesture requires re-uploading the eye program to the Core.
- The Daemon knows gesture names and durations, nothing about servos.
