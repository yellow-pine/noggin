# Links are Wi-Fi first, USB second; every Core is addressed directly

The Mech should sit on the desk untethered: pack-powered, with no cable to the Mac. Both Cores join the home Wi-Fi as stations (Bambu's MicroPython build has `network.WLAN` and `espnow`; Bluetooth and WebREPL are removed, see docs/research/2026-10-31-radio.md). The noggin service talks to each Core directly, so no relay firmware exists. Each Core sends a UDP beacon every 2 s (`noggin <name> <ip>`); the service listens on one port and learns the Cores from it. Commands are the existing newline command lines, one per UDP datagram, as `<mac> <seq> <line>`: the mac is an HMAC-SHA256 of the sequence and line under the shared token (the token itself never travels), the sequence is milliseconds since the epoch and must never go backwards (replays are dropped); the Core answers with a one-line ack from its own address and the service retries once after 200 ms. Beacons are unauthenticated discovery: the service trusts only the datagram's source address, never the claimed one. Wi-Fi credentials and the token are written once over USB by the setup wizard (`wifi.json` beside `calibration.json`). USB-C keeps two jobs: flashing (mpremote, the only path, there is no over-the-air update) and an automatic fallback Link when the radio is down. Offline Cores make hooks silent no-ops; the service reconnects on its own and `noggin status` shows wifi / usb / offline per Core. Each Core reports its uptime since power-on, the only battery signal available (the shield has no voltage sense); one pack per shield, the spare swapped in.

## Considered options

- Core 1 relays to Core 2 by ESP-NOW: rejected once both Cores can be on the LAN; one more protocol for nothing.
- Bluetooth LE from the Mac: rejected, the Bambu build has no `bluetooth` module.
- ESP-NOW through a third Core as USB dongle: rejected, it keeps a cable and adds a part.
- mDNS names: unverified on the Bambu build; the beacon needs nothing from the network.
- TCP: rejected for now; datagrams plus one retry cover one-line commands with less reconnection logic.
- Two packs in series for runtime: impossible, 14.8 V exceeds the shield's 12.6 V input.
