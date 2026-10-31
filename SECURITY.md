# Security

Report vulnerabilities privately to hello@yellowpine.com. Do not open a public issue. You will get a reply within a week.

## In scope

- The noggin service (`noggin/`): the Unix socket it listens on and the Wi-Fi Link to the Cores (UDP beacons and commands, shared token, HMAC).
- The Core program (`eyes/`): what it accepts over USB serial and over Wi-Fi.
- The setup wizard (`scripts/setup.sh`) and the hooks it installs into Claude Code.

## Out of scope

- The CyberBrick firmware (Bambu Lab's; this project never modifies it).
- Claude Code itself; report those to Anthropic.
