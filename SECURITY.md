# Security

Report vulnerabilities privately through GitHub's [private vulnerability reporting](https://github.com/yellow-pine/noggin/security/advisories/new) (the Security tab's "Report a vulnerability"). Do not open a public issue. You will get a reply within a week.

## Supported versions

Only the [latest release](https://github.com/yellow-pine/noggin/releases/latest) gets security fixes.

## In scope

- The noggin service (`noggin/`): the Unix socket it listens on and the Wi-Fi Link to the Cores (UDP beacons and commands, shared token, HMAC).
- The Core program (`eyes/`): what it accepts over USB serial and over Wi-Fi.
- The setup wizard (`scripts/setup.sh`) and the hooks it installs into Claude Code.

## Out of scope

- The Core's firmware (the vendor's; this project only installs the vendor's own updates, ADR 0012).
- Claude Code itself; report those to Anthropic.
