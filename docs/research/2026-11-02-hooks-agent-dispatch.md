# Research: hooks on Agent dispatch and SessionStart (2026-11-02)

Primary sources only, read 2026-11-02: https://code.claude.com/docs/en/hooks (H), https://code.claude.com/docs/en/sub-agents (SA), https://code.claude.com/docs/en/settings (S), https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md (CL). Nothing below was tried in a live session.

## 1. Matcher name for the subagent tool: `Agent`

- PreToolUse "Matches on any tool name except `EndConversation`: built-in tools such as `Bash`, ... `Agent`, `Workflow`, ..." (H#pretooluse). The tool_input section is headed `##### Agent`, "Spawns a subagent", fields `prompt`, `description`, `subagent_type`, `model` (H#pretooluse-input).
- The matcher is tested against `tool_name`: "For tool events, that field is `tool_name`." A matcher of only letters is an "Exact string": "`Bash` matches only the Bash tool". (H#matcher-patterns)
- The rename: "In version 2.1.63, the Task tool was renamed to Agent. Existing `Task(...)` references in settings and agent definitions still work as aliases." (SA#restrict-which-subagents-can-be-spawned). That covers `Task(...)` permission-rule syntax (CL: "disabling specific agents using `Task(AgentName)` syntax in settings.json permissions"); neither H nor CL says a hook `matcher` of `Task` still matches. CL's 2.1.63 entry doesn't mention the rename.
- Use `"matcher": "Agent"`. `Task` is unverified at best: an exact-string compare against `tool_name` `"Agent"` would miss it.

## 2. Exit codes

- Exit 2, PreToolUse: table row "`PreToolUse` | Yes | Blocks the tool call" (H#exit-code-2-behavior-per-event). "The message that comes with the block is your hook's stderr." "Claude receives the hook's stderr as the tool's error, prefixed with the event name, the tool name, and the hook's command": `PreToolUse:Bash hook error: [<cmd>]: Blocked: ...` (H#exit-code-2). So the model sees it.
- Exit 2, SessionStart: "`SessionStart` | No | Shows stderr to user only". "Claude Code renders the exit code 2 stderr in the transcript as a `<hook name> hook error` notice ... Claude doesn't see it, and the session or subagent proceeds." (H#exit-code-2-behavior-per-event)
- Exit 0 with stderr, any event: "Claude never sees stderr from a hook that exits 0. To read it yourself on events such as `PreToolUse`, enable debug logging." (H#exit-code-0)
- Exit 0 stdout: "For most events, Claude Code writes stdout to the debug log and doesn't show it in the transcript. The exceptions are `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, and `PostModelSwitch`, where Claude Code adds plain-text stdout as context that Claude can see and act on." (H#exit-code-0) So SessionStart stdout on exit 0 reaches Claude; PreToolUse stdout doesn't (unless it is decision JSON).
- Other non-zero (e.g. 1): "Non-blocking error ... The action goes ahead ... On events such as `PreToolUse`, you see a `<hook name> hook error` notice in the transcript." With plain-text stdout "The notice carries the first line of your stderr" (H#exit-code-output). Shown to the user; for SessionStart the docs say Claude doesn't see that notice (quote above). For PreToolUse the docs don't say whether the model sees it.
- Caveat: on exit 1, stdout JSON that passes validation still decides: "Success. Claude Code ignores the exit code, and the fields alone decide." (H#exit-code-output)

## 3. Stdin JSON

- Common: `session_id`, `prompt_id`, `transcript_path`, `cwd` ("Current working directory when the hook is invoked"), `scratchpad_dir`, `permission_mode`, `effort`, `hook_event_name`; plus `agent_id`, `agent_type` when the hook fires inside a subagent. (H#common-input-fields)
- PreToolUse: "receive `tool_name`, `tool_input`, and `tool_use_id`" (plus `mcp_server` for MCP tools). For Agent, `tool_input` has `prompt`, `description`, `subagent_type`, `model`. (H#pretooluse-input)
- SessionStart: "receive `source` and optionally `model`, `agent_type`, and `session_title`"; `source` is `"startup"`, `"resume"`, `"clear"`, `"compact"` or `"fork"`. Docs example: `{"session_id","transcript_path","cwd","hook_event_name":"SessionStart","source":"resume","model":...}`. (H#sessionstart-input)

## 4. `CLAUDE_PROJECT_DIR` and subagents

- "`${CLAUDE_PROJECT_DIR}`: the project root where the session started." In a worktree it "stays put: it still points at the project root where the session started", while "`cwd` follows Claude: the `cwd` field ... is the worktree root after Claude enters a worktree, and the new directory after Claude runs `cd`." (H#reference-scripts-by-path)
- "Hooks from settings files, managed policy settings, and plugins also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main conversation" (H#hook-locations). Project settings come from "the session's primary working directory" (S, "Claude Code reads the shared `.claude/settings.json` ..."). So a subagent in another directory (e.g. `isolation: worktree`) runs the session's hooks, not that directory's `.claude/settings.json`. Inferred from those two lines; no page states the worktree-subagent case outright.

## 5. When `.claude/agents/` is (re)loaded

- "Claude Code watches `~/.claude/agents/` and `.claude/agents/`. When you add or edit a subagent file on disk ... Claude Code detects the change within a few seconds and the next delegation uses the updated definition, with no restart needed." Restart still needed when: "The watcher covers only directories that existed when the session started"; `--add-dir` agents dirs aren't watched; `--disable-slash-commands` sessions don't watch. (SA#write-subagent-files)
- Project agents are "discovered by walking up from the current working directory ... the definition closest to the working directory" wins. (SA#choose-the-subagent-scope)
- Settings (hooks included) also hot-reload: "Claude Code watches your settings files and reloads them when they change ... including edits to `permissions`, `hooks`". (S)

## 6. Timeout default

- "Defaults: 600 for `command`, `http`, and `mcp_tool`; 30 for `prompt`; 60 for `agent`." Lowered to 30 on `UserPromptSubmit`, `PreModelSwitch`, `PostModelSwitch`; 10 on `MessageDisplay`; `SessionEnd` shares a 1.5 s budget. Not enforced for `async: true`. (H#common-fields)

## Unverified

- Whether a hook `matcher` of `Task` still matches the Agent tool (docs are silent; alias note covers `Task(...)` rules only).
- Whether the model sees a PreToolUse non-blocking (exit 1) notice; the docs only say the user sees it.
- SessionStart stdout on a non-zero exit: context injection is documented for exit 0 only.
