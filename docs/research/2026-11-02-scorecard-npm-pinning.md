# Scorecard: which npm installs in a Dockerfile `RUN` count as pinned (2026-11-02, #563)

Scorecard's Pinned-Dependencies check warns `npmCommand not pinned by hash` on a `RUN` line in our CI images. Which ways
of installing npm itself does it accept?

Code is read from ossf/scorecard at the latest release **`v5.6.0`** (2026-10-12; annotated tag → commit `61e8474`) and
at `main` (`2ef237f`). `checks/raw/shell_download_validate.go` is byte-identical on both, so the line numbers below hold
for both. `pinned_dependencies.go` differs on `main` only in the GitHub Actions immutable-release cache, not in the
Dockerfile path. Links are to the tag; `SDV` = [checks/raw/shell_download_validate.go](https://github.com/ossf/scorecard/blob/v5.6.0/checks/raw/shell_download_validate.go).

## How a `RUN` line is checked

- Every file matching `*Dockerfile*` is parsed; each `RUN` (or heredoc) is joined into one string and handed to the
  shell checker, and one `taintedFiles` map is shared by every `RUN` in the file
  ([checks/raw/pinned_dependencies.go L318-L415](https://github.com/ossf/scorecard/blob/v5.6.0/checks/raw/pinned_dependencies.go#L318-L415)).
- The shell checker parses it with mvdan.cc/sh and walks every node, running five detectors: `interpreter -c "…"`
  recursion, `curl | sh`, executing a previously downloaded file, `sh <(curl …)`, and package-manager installs; then
  it records any downloaded file (SDV L1222-L1300).
- `extractCommand` keeps only single-part words (plain literals, `'…'`, `"lit"`), drops `sudo`, and silently drops any
  word containing `$VAR`/`${VAR}` (SDV L258-L289).
- Each unpinned dependency becomes `"<type> not pinned by hash"`
  ([probes/pinsDependencies/impl.go L122-L131](https://github.com/ossf/scorecard/blob/v5.6.0/probes/pinsDependencies/impl.go#L122-L131));
  each type is scored as its own pinned/total share, and a type with no dependencies is left out of the score
  ([checks/evaluation/pinned_dependencies.go L109-L124](https://github.com/ossf/scorecard/blob/v5.6.0/checks/evaluation/pinned_dependencies.go#L109-L124)).

## 1. `npm install -g <local .tgz>`: flagged

- `isNpmDownload`: `path.Base(cmd[0])` must equal `npm` (case-insensitive), and **any** argument must be `install`,
  `i`, `install-test`, `update` or `ci` (SDV L446-L462; `isBinaryName` L62-L64).
- `isNpmUnpinnedDownload` returns **pinned** only if some argument is exactly `ci`, or an argument starts with
  `github:`, `git://`, `git+http://` or `git+https://` and has exactly one `#` followed by a 40-hex commit. Everything
  else is unpinned (SDV L464-L491). There is no case for a file path, a tarball, a registry URL, `--integrity`, or a
  lockfile.
- So `npm install -g ./npm-11.21.1.tgz` and `npm install -g /tmp/npm-11.21.1.tgz` are `npmCommand`, unpinned. So is
  `npm install -g npm@11.21.1`. The only accepted forms are `npm ci` and a git URL pinned to a commit. Tests confirm:
  `npm install` → unpinned, `npm ci` → pinned, `github:…#<40 hex>` and `git://…#<40 hex>` → pinned, `git:`, `http://`,
  `https://` with a hash → unpinned
  ([shell_download_validate_test.go L435-L524](https://github.com/ossf/scorecard/blob/v5.6.0/checks/raw/shell_download_validate_test.go#L435-L524);
  testdata `RUN npm install -g`, `RUN npm ci` …
  [checks/raw/testdata/Dockerfile-pkg-managers L110-L119](https://github.com/ossf/scorecard/blob/v5.6.0/checks/raw/testdata/Dockerfile-pkg-managers#L110-L119)).
- The `ci` match is a token match on any argument, not on the subcommand (SDV L465-L469).

## 2. `curl -o … && sha512sum -c && tar -xzf …`: not flagged

- A download is only a finding when it is executed: piped into an interpreter (SDV L338-L388), run via `<( )`
  (L1080-L1147), or recorded as a file and later run as `cmd[0]` (`isExecuteFile`, L66-L72) or as an argument of an
  interpreter (`isInterpreterWithFile`, L240-L256), both checked in `collectExecuteFiles` (L411-L442).
- The file is recorded only from a `>` redirect, `wget -O`/URL basename, `gsutil` or `aws s3api get-object`
  (`recordFetchFileFromNode` L1052-L1078, `getOutputFile` L170-L195). **curl's `-o` is not parsed**, so
  `curl -fsSL -o /tmp/npm.tgz …` records nothing.
- Even when recorded (`curl … > /tmp/npm.tgz`), `tar -xzf /tmp/npm.tgz` is neither `cmd[0] == file` nor an interpreter
  (`tar` is not in the list, L46-L51), so no finding. The source says so: `TODO(laurent): detect downloads of zip/tar
  files containing scripts` (SDV L1285).
- `sha512sum` does not appear in the checker; there is no hash-validation detection in either file. The only checksum
  logic is choco's `--requirechecksum` flag (SDV L736-L747). `echo … | sha512sum -c` is not a download pipe (left side
  is not curl/wget/gsutil/aws, L75-L96). So the checksum line neither helps nor hurts; the step passes because nothing
  downloaded is executed.

## 3. `node …/bin/npm-cli.js install -g …`: not detected

- `isNpmDownload` needs the basename of `cmd[0]` to be `npm`; here it is `node` (SDV L447). Not an `npmCommand`. (A
  path whose basename is `npm`, e.g. `/tmp/package/bin/npm install -g`, would be detected.)
- `node` is in `otherInterpreters` (SDV L48), which only matters for download-then-run: `node <file>` is flagged when
  `<file>` was recorded as downloaded (L240-L256, L426), and `curl … | node` is flagged (L365). A `node -c "…"` style
  command is not recursed into because `isShellInterpreterOrCommand` rejects `node` (L210-L225, L1261).
- Trap: `isInterpreterWithFile` matches **any** argument of `node` against recorded files. If the tarball was fetched
  with `curl … > /tmp/npm.tgz` (recorded) in any `RUN` of the same Dockerfile, then
  `node npm-cli.js install -g /tmp/npm.tgz` is `downloadThenRun` unpinned. With `curl -o` the tarball is never
  recorded, so it is not.
- No other package-manager detector matches `node` (go, pip, npm, choco, nuget only; SDV L926-L1050).

## 4. `npm -v`: not flagged

No install verb, so `isNpmDownload` is false and no dependency is recorded (SDV L451-L461).

## For noggin

- Any `npm install -g …` of npm itself stays `npmCommand not pinned by hash`, whatever the argument; `npm ci` needs a
  `package.json` + lockfile.
- Accepted without a finding: fetch the tarball (`curl -o`, checked with `sha512sum -c` for our own integrity, which
  Scorecard ignores), extract it with `tar`, and run it as `node <dir>/bin/npm-cli.js …`, or `npm -v` afterwards.
  Avoid putting the extracted `bin/npm` as `cmd[0]` of an `install` command, and fetch with `curl -o`, not `>`.
- Inferred: these are heuristics on literal tokens, so they can change in any release; re-check on a Scorecard bump.
