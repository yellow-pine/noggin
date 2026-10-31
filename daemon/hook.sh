#!/bin/sh
# Claude Code hook: relay the Trigger JSON on stdin to the noggin Daemon. Never blocks, never fails.
nc -U -w 1 "$HOME/.noggin.sock" >/dev/null 2>&1 || true
exit 0
