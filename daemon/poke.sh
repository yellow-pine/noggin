#!/bin/sh
# Claude Code hook: relay the hook's stdin JSON to the noggin daemon. Never blocks, never fails.
nc -U -w 1 "$HOME/.noggin.sock" >/dev/null 2>&1 || true
exit 0
