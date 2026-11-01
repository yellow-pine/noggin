# Hooks

Claude Code tells the noggin service what it is doing through its hooks. `make install` (or the last step of
`scripts/setup.sh`) merges noggin's hooks into Claude Code's user settings, `~/.claude/settings.json`; running it again
changes nothing, and `make unhooks` takes them out.

```
make hooks           # add noggin's hooks to ~/.claude/settings.json
make unhooks         # take them out again
```

Each hook runs `noggin/hook.sh`, which passes the event's JSON to the noggin service's Unix socket, `~/.noggin.sock`,
and returns at once: it never blocks Claude Code and never fails, even with the noggin service stopped. Which event
plays which gesture is in [Gestures and behaviour](gestures.md).
