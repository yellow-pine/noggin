# CodeQL: from default setup to advanced setup (2026-11-02, #549)

The `main` ruleset's `code_scanning` rule wants CodeQL results (security alerts `high_or_higher`, alerts `errors`), and
default setup analyses no PR that touches no code, so a docs-only PR waits forever. Today `GET
repos/yellow-pine/noggin/code-scanning/default-setup` says `state: configured`, languages actions, javascript-typescript,
python, `schedule: weekly`. What does the move to a `.github/workflows/codeql.yml` take?

Docs are read from github/docs at `33b1f4a` (2026-10-31); the action from github/codeql-action at `v4.39.1`
(`9b32540`); the starter workflow from actions/starter-workflows at `fbc8bd8` (2026-07-31).

## 1. Switching, and the upload block

- **CodeQL SARIF is rejected while default setup is on.** Error text: `Upload with CodeQL results rejected due to
  "default setup"`. It covers any SARIF holding CodeQL results, by the action, the CLI or the REST API; SARIF from other
  tools is not blocked. The fix is to disable default setup ("Disable CodeQL") and rerun the upload.
  ([default-setup-enabled](https://docs.github.com/en/code-security/reference/code-scanning/sarif-files/troubleshoot-sarif-uploads/default-setup-enabled))
- **Order: disable first.** The advanced-setup how-to says that when switching, pick "Switch to advanced" and click
  **Disable CodeQL** in the pop-up, then commit the workflow
  ([configuring advanced setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning)).
  Enabling default setup "disables the existing CodeQL workflow file and blocks any CodeQL API analysis from uploading
  results"; to go back, disable default setup, then re-enable the workflow
  ([results-different-than-expected](https://docs.github.com/en/code-security/reference/code-scanning/troubleshoot-analysis-errors/results-different-than-expected)).
  A workflow run before the disable fails its upload; a rerun after it succeeds.
- **Existing alerts: no explicit statement.** No page says what disabling default setup does to its alerts. What the
  docs do say: each configuration (tool + category) has its own alerts; a configuration that no longer runs is stale,
  its alerts "will stay open indefinitely", and stale configurations on the default branch are removed from the tool
  status page (**Delete configuration**)
  ([code-scanning-alerts](https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning-alerts#about-alerts-from-multiple-configurations),
  [tool status page](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/use-the-tools-status-page-for-code-scanning#removing-configurations)).
  Inferred: default setup's alerts stay, and close once the default setup configuration is deleted or the same alert
  is fixed by the new one.
- **REST: confirmed.** `PATCH /repos/{owner}/{repo}/code-scanning/default-setup` with body `state`: `configured` |
  `not-configured`; 200 or 202 (202 returns `run_id`, `run_url`), 409 if a validation run with a different
  configuration is in progress, 422 if the repository is not in the required state
  ([REST code scanning](https://docs.github.com/en/rest/code-scanning/code-scanning#update-a-code-scanning-default-setup-configuration)).
  Classic PATs need `repo`; fine-grained tokens need **Administration: write**
  ([fine-grained permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens#repository-permissions-for-administration)).
  So: `gh api -X PATCH repos/yellow-pine/noggin/code-scanning/default-setup -f state=not-configured`.

## 2. Several languages in one job

- **`languages` takes a comma list.** init's `action.yml`: "A comma-separated list of CodeQL languages to analyze. Due
  to the performance benefit of parallelizing builds, we recommend specifying languages to analyze using a matrix"
  ([init/action.yml](https://github.com/github/codeql-action/blob/v4.39.1/init/action.yml)). The docs say the same:
  "We recommend that only one language is provided as an argument", and the matrix lets each language run in parallel
  and be customised; "We recommend that all workflows adopt this configuration"
  ([languages to be analyzed](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options#languages-to-be-analyzed)).
  The documented risk of one job is the sequential one: "If analysis for one language fails in this mode, then the
  analysis for all languages fails" (stated for the no-`languages` case, which runs the same way).
- **`build-mode` is one value for the whole job, not per language.** The input's description: "This input is only
  available when analyzing a single CodeQL language per job, for example using a matrix"
  ([init/action.yml](https://github.com/github/codeql-action/blob/v4.39.1/init/action.yml)). The code does not
  enforce that: `parseBuildModeInput` validates the value only, and `databaseInitCluster` passes one
  `--build-mode=<mode>` to `codeql database init --db-cluster` alongside every `--language=`
  ([src/config-utils.ts](https://github.com/github/codeql-action/blob/v4.39.1/src/config-utils.ts),
  [src/codeql.ts](https://github.com/github/codeql-action/blob/v4.39.1/src/codeql.ts)). "Interpreted languages must use
  `none` for the build mode" ([README](https://github.com/github/codeql-action/blob/v4.39.1/README.md#which-build-mode-should-i-use)),
  so `none` for actions + javascript-typescript + python works but sits outside the documented contract. Leaving
  `build-mode` out also works: each language then gets its default, which for interpreted languages is `none`
  ([languages to be analyzed](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options#languages-to-be-analyzed)).
- **`actions` with `none`: yes.** codeql-action's own CodeQL workflow runs `languages: actions` (matrix) with
  `build-mode: none` ([.github/workflows/codeql.yml](https://github.com/github/codeql-action/blob/v4.39.1/.github/workflows/codeql.yml));
  `actions` is a default setup language in the REST enum
  ([REST code scanning](https://docs.github.com/en/rest/code-scanning/code-scanning#update-a-code-scanning-default-setup-configuration)).
- **How analyze handles several languages:** one loop over `config.languages`, sequential: run queries, then
  interpret results into one SARIF file per language (`<language>.sarif`); the files are then merged (CodeQL CLI
  `github merge-results`) and sent as **one** upload under **one** category
  ([src/analyze.ts](https://github.com/github/codeql-action/blob/v4.39.1/src/analyze.ts),
  [src/upload-lib.ts](https://github.com/github/codeql-action/blob/v4.39.1/src/upload-lib.ts)). With no `category`
  input the category is built from workflow file, job and matrix values
  ([analysis category](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options#analysis-category)).
  The starter workflow's `category: "/language:<lang>"` is a per-job thing; a single job should leave `category` unset
  (one fixed category for every language is not something the docs show).
- Minor: per-language CodeQL bundles (rolling out since 4.38.1) are used only when one language is requested
  ([CHANGELOG](https://github.com/github/codeql-action/blob/v4.39.1/CHANGELOG.md),
  [src/per-language-bundles.ts](https://github.com/github/codeql-action/blob/v4.39.1/src/per-language-bundles.ts)), so a
  three-language job downloads the full bundle.

## 3. The "Require code scanning results" rule

- **What blocks a merge** (whole documented list): a required tool finds an alert at or above the ruleset's
  severities; a required tool's analysis "is still in progress"; a required tool "is not configured for the
  repository" ([merge protection](https://docs.github.com/en/code-security/concepts/code-scanning/merge-protection),
  [available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results)).
  It is not a status check. It does not apply to merge queue groups or to "Dependabot pull requests analyzed by default
  setup"; alert lines must be in the PR diff.
- **Tools, not categories.** The rule's parameters are a list of `{tool, alerts_threshold, security_alerts_threshold}`;
  there is no category field ([REST rules](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset)).
- **Head vs base, and `pull_request`: not documented for the rule.** No page says which commits the rule wants results
  for, or what it does when a PR has no analysis at all. What is documented: PR results come from a `pull_request` run
  (merge commit) or from a `push` run on the branch, and PR alerts are found "by comparing the existing analysis of the
  head of the branch to the analysis for the target branch"; scanning the PR's merge commit is "more efficient and
  accurate" ([scan frequency](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options#scan-frequency)).
  So the base needs an analysis too, which `push` to `main` gives. Inferred from our docs-only PRs: no analysis for the
  PR reads as "in progress" and blocks.
- **`paths-ignore` would recreate the bug.** The docs offer `on.pull_request.paths-ignore` to skip PRs
  ([avoiding unnecessary scans](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options#avoiding-unnecessary-scans-of-pull-requests));
  with the rule on, a skipped PR has no results.
- **Dependabot:** `pull_request` runs may always upload results, even with Dependabot's read-only token; GitHub
  recommends `pull_request` over `push` for Dependabot branches. A squash-merge commit authored by Dependabot runs its
  `push` workflows read-only, so the upload can fail with `403: Resource not accessible by integration`
  ([resource-not-accessible](https://docs.github.com/en/code-security/reference/code-scanning/troubleshoot-analysis-errors/resource-not-accessible)).

## 4. The starter workflow

[actions/starter-workflows code-scanning/codeql.yml](https://github.com/actions/starter-workflows/blob/main/code-scanning/codeql.yml):

- `on:` `push` and `pull_request` to `[ $default-branch, $protected-branches ]`, plus `schedule: - cron: $cron-weekly`.
  No `paths-ignore`.
- `permissions:` on the job: `security-events: write` ("required for all workflows"), `packages: read` (private CodeQL
  packs), `actions: read` and `contents: read` ("only required for workflows in private repositories"). The README:
  "All advanced setup code scanning workflows must have the `security-events: write` permission. Workflows in private
  repositories must additionally have the `contents: read` permission"
  ([README](https://github.com/github/codeql-action/blob/v4.39.1/README.md#workflow-permissions)).
- A `language` × `build-mode` matrix, `fail-fast: false`, `category: "/language:${{matrix.language}}"`.

## 5. Latest release and SHAs

- Latest v4: **`v4.39.1`** (2026-10-21; CodeQL bundle 2.27.3). Annotated tag `8498dc4c…` → commit
  **`9b3254085494b55a0f7c4c2b3d2d52cc712ce370`**; `v4` points to the same commit
  (`gh api repos/github/codeql-action/git/ref/tags/v4.39.1`, then `git/tags/8498dc4c…`;
  [release](https://github.com/github/codeql-action/releases/tag/v4.39.1)).
- `v4.39.0` (2026-10-15): annotated tag `48870fdd…` → commit `6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee`, the SHA the
  repo pins. So the pin is correct for v4.39.0 but one patch behind.

## 6. Copilot Autofix

"Copilot Autofix works the same way whether a repository uses default or advanced setup for code scanning. There is no
separate step to enable it: enabling code scanning with CodeQL is sufficient."
([autofix](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning#using-copilot-autofix))

## For noggin

- Order: the docs say disable, then commit. Either `PATCH … state=not-configured` first and let the PR's own run
  upload, or merge first and rerun the rejected runs after the PATCH. Then delete the stale default-setup configuration
  on the tool status page so its alerts don't stay open forever.
- Triggers: `pull_request` + `push` on `main` + weekly `schedule`, no `paths-ignore`. `push` to `main` gives the base
  analysis PRs are compared against.
- One job with `languages: actions,javascript-typescript,python` works; `build-mode: none` is passed to all three,
  which the docs call matrix-only. Dropping `build-mode` gets the same result inside the documented contract. Leave
  `category` unset. Cost: no parallelism, and one language failing fails all three.
- Permissions: `security-events: write` and `contents: read` on the job (public repo; `actions: read` and
  `packages: read` are for private repos and private packs).
- Pin `9b3254085494b55a0f7c4c2b3d2d52cc712ce370 # v4.39.1` (or keep v4.39.0 to match image-scan.yml and scorecard.yml;
  their Trivy/Scorecard SARIF is not CodeQL, so the default-setup block never touched them).
