# GitHub Pages: why `deploy-pages` misses the artifact uploaded a moment earlier, and what makes a re-run safe (2026-11-28, #1117)

Our `deploy` job uploads the Pages artifact and deploys it in the next step. Twice on 2026-11-28 the deploy step said
`No artifacts named "github-pages" were found for this workflow run`, and re-running the job either deployed the earlier
attempt's artifact or failed with `Multiple artifacts named "github-pages"`. Why does the lookup miss, and which
documented options make (a) the lookup find the artifact and (b) a re-run of the job safe?

Code is read at the commits our workflow pins:

- `actions/deploy-pages` **v5.0.1**, `368f825`. It is the newest release (2026-09-01) and also the tip of `main`:
  nothing newer exists ([releases][dp-releases]). `DP` below is this commit.
- `actions/upload-pages-artifact` **v5.0.0**, `fc324d3`, the newest release (2026-04-10). It runs
  `actions/upload-artifact@bbbca2d`, which is **v7.0.0** ([action.yml L82-L89][upa-action-upload]).
- `@actions/artifact` **2.1.8**, the library `deploy-pages` bundles ([package-lock.json L39-L42][dp-lock]), read in
  `actions/toolkit` at `176b40a`, the last commit with that version. `TK` below is this commit.
- GitHub's docs, starter workflows (`e3c451d`) and status page as served on 2026-11-28.

"Our runs" are [46125318398][run-a] and [46138133454][run-b], two attempts each; their log lines are in #1117.

## The lookup, as written

- `deploy-pages` does not call the REST endpoint. `getArtifactMetadata` calls `artifactClient.listArtifacts()` with no
  arguments, once ([DP api-client.js L53-L109][dp-api], the call is L71). With no `findBy` option the library takes
  its internal path, not the REST one ([TK client.ts L176-L198][tk-client]).
- The internal path is one `ListArtifacts` request to the Actions results service (Twirp, at `ACTIONS_RESULTS_URL`).
  The request carries only the run's and the job's backend ids, read from the runner's token; it sets no name filter
  ([TK list-artifacts.ts L115-L147][tk-list], [TK util.ts L20-L68][tk-util]).
- There is no paging on this path: the request has four fields (two ids, an optional name filter, an optional id
  filter) and the response is one list ([TK artifact.ts L97-L131][tk-proto]). The 100-per-page loop exists only on the
  REST path, the function above it in the same file (L19-L113). So page size cannot hide an artifact here.
- `Found N artifact(s)` is printed by the library for everything the service returned, before any name filter
  ([TK list-artifacts.ts L142][tk-list]). `deploy-pages` filters by exact name afterwards
  ([DP api-client.js L79][dp-api]). N counts all artifacts of the run, not `github-pages` ones.
- Zero matches throws `No artifacts named ...`; more than one throws `Multiple artifacts named ...`
  ([DP api-client.js L84-L92][dp-api]). Neither branch waits or retries.
- The library retries a request only on HTTP 429, 500, 502, 503 and 504 or a network error
  ([TK artifact-twirp-client.ts L73-L160][tk-twirp]). A list that answers 200 without the newest artifact is a success
  to it.
- The one match's id goes to `POST /repos/{owner}/{repo}/pages/deployments` as `artifact_id`
  ([DP deployment.js L74-L88][dp-deployment], [DP api-client.js L111-L129][dp-api]).
- The library on `main` (6.3.1, `0c3a9c3`) lists the same way, without a retry
  ([list-artifacts.ts L124-L158][tk-list-main]). A dependency bump alone would not change this.

## What our runs show against that code

- Hypothesis in #1117: "the REST list endpoint lags the upload". Half right. The list that lags is the results
  service's `ListArtifacts`, not REST; the rest holds.
- Attempt 1 of both runs listed 11 artifacts 0.3 to 0.6 s after the upload's `successfully finalized` line, when the
  run held 12: the list was complete but for the artifact just finalized (our runs). Not a page limit (see above; and
  the same call returned 12 and 13 in the re-runs).
- The lag varies. Attempt 2 of run 46125318398 missed the new artifact again after 0.3 s; attempt 2 of run
  46138133454 saw it after 0.3 s (our runs). Inferred: the service's list is eventually consistent after an upload is
  finalized. No GitHub source states this; it is what the logs show.
- The list spans the attempts of a run. Attempt 2 received attempt 1's `github-pages` (our runs), as in
  [deploy-pages#338][dp338] (`Found 2 artifact(s)` on a re-run). The REST list does too:
  `GET /repos/yellow-pine/noggin/actions/runs/46125318398/artifacts?name=github-pages` returns both, ids 15258056866
  and 15258271483 (queried 2026-11-28; the [endpoint][rest-list] has no parameter for an attempt).
- So attempt 2 of run 46125318398 "succeeded" by the code above: its own artifact was not listed yet, attempt 1's was
  the single match, and that id was deployed.
- Artifact ids are not in creation order. In run 46138133454 the artifact of 12:21:37Z has id 15262757960 and the one
  of 12:23:13Z has id 15262338603 (the same REST query). "Take the highest id" would pick the wrong one;
  [toolkit#2540][tk2540] (open) reports the same.
- Our job starts 4 to 5 s after the job it needs has completed (Checks to Deploy, six runs on main today). Inferred:
  an upload moved to an earlier job would be looked up about 5 to 7 s after it was finalized.

## Upstream: known, open, unanswered

- [deploy-pages#451][dp451] (open, 2026-10-07) is this failure with the same versions and the same one-job layout:
  finalized, looked up 0.28 s later, `Found 0 artifact(s)`. The reporter saw it once in 63 deploys. From 2026-11-22
  others report it "most of the time". No maintainer has answered; every comment is a user's.
- Lag measured by users in that thread: 0.44 to 5.75 s in an eight-run probe, with the first lookup missing in four;
  one production run needed about 46 s; another repository missed at 0.69 s and 1.58 s and succeeded after 60 s; a
  `sleep 2` that had worked stopped being enough on 2026-11-24; a `sleep 10` works for one user
  ([deploy-pages#451][dp451]).
- Users there also found that the REST API lists the artifact while the lookup still misses it, so polling REST
  before deploying does not help ([deploy-pages#451][dp451]; Renovate tried it and replaced it,
  [renovate#48395][renovate]). `upload-artifact`'s README promises only that artifacts are "immediately available in
  the UI and REST API" ([README L65][ua-readme-65]).
- [deploy-pages#455][dp455] (open PR, 2026-11-12) retries the lookup when nothing matches, after 1, 2, 4 and 8 s.
  Not reviewed by a maintainer, not released.
- [deploy-pages#338][dp338] (open issue, 2024-04-18) asks for an `artifact_id` input because a re-run in a one-job
  layout fails with `Multiple artifacts`; [deploy-pages#399][dp399] (open PR, 2025-06-03) implements it. No maintainer
  answer on either. `upload-pages-artifact` already outputs `artifact_id`
  ([action.yml L21-L24][upa-action]), but `deploy-pages` has no input to take it ([DP action.yml L7-L31][dp-action]).
- The only answer found from the action's own team on a missing artifact is from 2024 and about mismatched major
  versions, not this ([deploy-pages#305][dp305]).
- The same lag is reported for downloads and merges since about 2026-11-20, also between jobs joined by `needs`:
  [download-artifact#505][da505] (open, with retry PR [#506][da506]), [upload-artifact#830][ua830] (open). Users'
  reports, no maintainer answer.
- [githubstatus.com][status] lists no incident on 2026-11-28; the latest is 2026-11-25 23:06Z (LFS). No incident in
  November names artifacts ([incidents feed][status-api], read 2026-11-28 12:30Z).

## Inputs and outputs that exist

- `deploy-pages` inputs: `token`, `timeout`, `error_count`, `reporting_interval`, `artifact_name` (default
  `github-pages`), `preview`. Output: `page_url`. Nothing for an artifact id, a wait or a retry of the lookup
  ([DP action.yml L7-L34][dp-action], [README L47-L62][dp-readme]).
- `upload-pages-artifact` inputs: `name` (default `github-pages`), `path`, `retention-days` (default 1),
  `include-hidden-files`. Output: `artifact_id` ([action.yml L4-L24][upa-action]). It does not pass
  `upload-artifact`'s `overwrite` through ([action.yml L82-L89][upa-action-upload]; asked for in
  [upload-pages-artifact#110][upa110], open).

## Names, attempts and re-runs

- An artifact name is unique: a second upload to the same name fails
  ([upload-artifact README L72-L74][ua-readme-72], [L288-L290][ua-readme-288]). Yet a re-run uploads the same name
  again and gets a second artifact with its own id: observed in our runs and in [deploy-pages#338][dp338]. Inferred
  from those logs: the rule holds per attempt, not per run. The README does not describe re-runs.
- `github.run_attempt` "begins at 1 for the workflow run's first attempt, and increments with each re-run";
  `github.run_id` does not change on a re-run ([contexts][docs-github-ctx]).
- A re-run of failed jobs also re-runs the jobs that depend on them; "jobs that aren't included keep their outputs from
  the previous attempt, which the newly run jobs can use" ([re-running workflows and jobs][docs-rerun]). The page says
  nothing about an earlier attempt's artifacts.
- The Pages API takes an `artifact_id` (or URL), an `environment` (default `github-pages`), a
  `pages_build_version` and an OIDC token. It takes no artifact name ([REST: create a Pages deployment][rest-pages]).
- "Be named `github-pages`" in `upload-pages-artifact`'s README is its rule for an artifact uploaded without that
  action ([README L63-L65][upa-readme]); it is the default `deploy-pages` looks for, and both actions document an
  input to change it ([README L46-L51][upa-readme], [DP README L55][dp-readme]). The `name` input was merged in
  2022 ([upload-pages-artifact#41][upa41]).
- The `github-pages` environment is the deployment's target, a separate thing from the artifact's name
  ([DP README L80][dp-readme]).

## Job layout in GitHub's own material

- `deploy-pages`' README: "We recommend this action to be used in a dedicated job", and the artifact "must have been
  uploaded in a previous step, either in the same job or a separate job" ([DP README L15, L74][dp-readme]). Both
  layouts are documented.
- Of the nine Pages starter workflows, eight upload in a `build` job and deploy in a `deploy` job that needs it
  (astro, gatsby, hugo, jekyll, jekyll-gh-pages, mdbook, nextjs, nuxtjs). Only `static.yml` does both in one job, as
  ours does ([pages/ at e3c451d][sw-dir], [static.yml L24-L43][sw-static]).

## The candidate fixes

### A. Name the artifact per attempt

`name: github-pages-${{ github.run_attempt }}` on `upload-pages-artifact` and the same value as `artifact_name` on
`deploy-pages`.

- Supported: both inputs are documented, and nothing read requires the literal name (previous two sections).
- Makes a re-run safe in our one-job layout: upload and lookup run in the same attempt, so the name matches exactly
  one artifact, whether failed jobs or all jobs are re-run. An earlier attempt's artifact can no longer be deployed by
  mistake, nor cause `Multiple artifacts` (by the filter at [DP api-client.js L79][dp-api]).
- Limit: it does nothing for the lag. A lookup that comes too early still fails with `No artifacts named`; the
  difference is that re-running then works.
- Inferred, not run by us: that the Pages service accepts an artifact with another name. One user reports deploying
  with a per-attempt name ([upload-artifact#585][ua585], comment of 2025-04-04).

### B. Time between upload and lookup

Two jobs, upload then deploy:

- It is the layout the README recommends and eight starters use (above).
- It puts about 5 to 7 s between upload and lookup in our runs (inferred, above). Limit: users measured lags of 5.75
  s and 46 s and report misses between jobs ([deploy-pages#451][dp451], [download-artifact#505][da505]). It lowers
  the odds; it is not a guarantee.
- "Re-run failed jobs" after a failed deploy re-runs only the deploy job: no second upload, and the artifact has long
  been listed. Safe with the default name.
- "Re-run all jobs" uploads `github-pages` again into the same run and fails with `Multiple artifacts`
  ([deploy-pages#338][dp338]), unless the name is per attempt.
- A and B do not combine by writing the same expression twice: after "re-run failed jobs" the deploy job is in attempt
  2 and would look for `github-pages-2`, while the upload job made `github-pages-1`. The name has to come from the
  upload job's output ([job outputs][docs-job-outputs]; kept across a partial re-run, [docs][docs-rerun]). That is more
  configuration than A in one job.

A documented wait or retry:

- None exists in either action (inputs above). `timeout`, `error_count` and `reporting_interval` act only after the
  deployment has been created ([DP deployment.js L138-L235][dp-deployment-check]).
- Workflow syntax can retry the step: `continue-on-error: true` on the deploy step, a wait, and a second deploy step
  under `if: steps.<id>.outcome == 'failure'` ([continue-on-error][docs-coe], [steps context][docs-steps-ctx]).
  Renovate merged this on 2026-11-25, retrying the deploy and not the upload ([renovate#48395][renovate]). Limit: it
  retries after any failure of the first step, and `environment.url` must fall back across the step ids.
- A fixed `sleep` step before the deploy is one line and costs its length on every deploy. Limit: no source bounds
  the lag; the figures above range from under 0.3 s to about 46 s.

### C. Anything better

- No. There is no newer release, no artifact-id input and no retry in `deploy-pages` (first section). The fixes exist
  only as open PRs: [#455][dp455] (retry) and [#399][dp399] (`artifact_id`).
- Rejected against our rules: a custom script that posts the deployment with the `artifact_id` output (it would
  re-implement the action's status polling and cancelling); a third-party delete-artifact action before the upload
  (the workaround in [upload-pages-artifact#97][upa97]; needs `actions: write`, and A does the same job with two
  inputs).

## For noggin

- (b) A, in the one job we have: two lines, documented inputs, safe for both kinds of re-run.
- (a) No documented option fixes the lag. The smallest change is a wait between the upload and the deploy; the
  sturdier one is the step retry above. Either is glue to remove when [deploy-pages#455][dp455] or [#399][dp399] is
  released. With A in place, a miss that outlasts the wait costs one safe "re-run failed jobs", not a wrong deploy.
- Inferred: 10 s covers every lag measured in the probe (5.75 s at most) and not the 46 s tail. The length is a guess.
- Splitting into two jobs buys about the same seconds as a short sleep, at the cost of a job and of passing the name
  through outputs. It is not needed for (b) once A is in.
- Chosen in #1117: A, and a 60 s wait before the deploy step. 60 s is past every lag measured above (46 s the
  longest) and is what one user in [deploy-pages#451][dp451] runs before the first attempt; it is still a guess at a
  lag no source bounds. The step retry was not taken: it would also deploy again after a failure that came later than
  the lookup, which nothing read says is harmless.
- Our own first attempts on main, 2026-11-27 and 28: 18 found the artifact 0.3 to 0.8 s after it was finalized, and
  three of the four lookups in the two failed runs missed it at 0.3 to 0.6 s (the jobs' logs, read 2026-11-28). The
  lag varies from one upload to the next; the gap did not.

## Not confirmed

- Why the list lags, and whether GitHub treats it as a fault: no maintainer or GitHub statement found.
- An upper bound for the lag.
- That a custom artifact name deploys end to end on our repository (first deploy after the change will show it).
- Whether the REST list lagged in our runs (not logged). Users report that it does not.
- Whether a second deploy step is harmless after a failure that came later than the lookup (a deployment already
  created). Not documented. Adjacent: `pages_build_version` is the commit SHA
  ([DP context.js L8][dp-context]), and users report that a second deployment of the same commit can be accepted and
  not served ([deploy-pages#383][dp383], open). That may touch Release's manual deploy of a commit already deployed;
  not checked here.
- Whether the two attempts' artifacts in run 46125318398 differed in content (not downloaded).

[dp-releases]: https://github.com/actions/deploy-pages/releases
[dp-api]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/api-client.js#L53-L129
[dp-deployment]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js#L74-L88
[dp-deployment-check]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/deployment.js#L138-L235
[dp-context]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/src/internal/context.js#L8-L14
[dp-action]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/action.yml#L7-L34
[dp-readme]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/README.md?plain=1#L15-L80
[dp-lock]: https://github.com/actions/deploy-pages/blob/368f82528645a54fb793d4d04e342629a3f51346/package-lock.json#L39-L42
[tk-client]: https://github.com/actions/toolkit/blob/176b40a8883d3e1ef8466fab7d35fd8a7df7428c/packages/artifact/src/internal/client.ts#L176-L198
[tk-list]: https://github.com/actions/toolkit/blob/176b40a8883d3e1ef8466fab7d35fd8a7df7428c/packages/artifact/src/internal/find/list-artifacts.ts#L115-L147
[tk-util]: https://github.com/actions/toolkit/blob/176b40a8883d3e1ef8466fab7d35fd8a7df7428c/packages/artifact/src/internal/shared/util.ts#L20-L68
[tk-proto]: https://github.com/actions/toolkit/blob/176b40a8883d3e1ef8466fab7d35fd8a7df7428c/packages/artifact/src/generated/results/api/v1/artifact.ts#L97-L131
[tk-twirp]: https://github.com/actions/toolkit/blob/176b40a8883d3e1ef8466fab7d35fd8a7df7428c/packages/artifact/src/internal/shared/artifact-twirp-client.ts#L73-L160
[tk-list-main]: https://github.com/actions/toolkit/blob/0c3a9c332b678ff1e776f93d728a4ad279803abe/packages/artifact/src/internal/find/list-artifacts.ts#L124-L158
[upa-action]: https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml#L4-L24
[upa-action-upload]: https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml#L82-L89
[upa-readme]: https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/README.md?plain=1#L46-L65
[ua-readme-65]: https://github.com/actions/upload-artifact/blob/bbbca2ddaa5d8feaa63e36b76fdaad77386f024f/README.md?plain=1#L65
[ua-readme-72]: https://github.com/actions/upload-artifact/blob/bbbca2ddaa5d8feaa63e36b76fdaad77386f024f/README.md?plain=1#L72-L74
[ua-readme-288]: https://github.com/actions/upload-artifact/blob/bbbca2ddaa5d8feaa63e36b76fdaad77386f024f/README.md?plain=1#L288-L290
[rest-list]: https://docs.github.com/en/rest/actions/artifacts#list-workflow-run-artifacts
[rest-pages]: https://docs.github.com/en/rest/pages/pages#create-a-github-pages-deployment
[docs-rerun]: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs
[docs-github-ctx]: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#github-context
[docs-steps-ctx]: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#steps-context
[docs-coe]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepscontinue-on-error
[docs-job-outputs]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idoutputs
[sw-dir]: https://github.com/actions/starter-workflows/tree/e3c451d60f119b71caebf13c98ac45da6e15b4b7/pages
[sw-static]: https://github.com/actions/starter-workflows/blob/e3c451d60f119b71caebf13c98ac45da6e15b4b7/pages/static.yml#L24-L43
[status]: https://www.githubstatus.com/history
[status-api]: https://www.githubstatus.com/api/v2/incidents.json
[run-a]: https://github.com/yellow-pine/noggin/actions/runs/46125318398
[run-b]: https://github.com/yellow-pine/noggin/actions/runs/46138133454
[dp305]: https://github.com/actions/deploy-pages/issues/305#issuecomment-1915359981
[dp338]: https://github.com/actions/deploy-pages/issues/338
[dp383]: https://github.com/actions/deploy-pages/issues/383
[dp399]: https://github.com/actions/deploy-pages/pull/399
[dp451]: https://github.com/actions/deploy-pages/issues/451
[dp455]: https://github.com/actions/deploy-pages/pull/455
[da505]: https://github.com/actions/download-artifact/issues/505
[da506]: https://github.com/actions/download-artifact/pull/506
[ua585]: https://github.com/actions/upload-artifact/issues/585#issuecomment-2779095324
[ua830]: https://github.com/actions/upload-artifact/issues/830
[upa41]: https://github.com/actions/upload-pages-artifact/pull/41
[upa97]: https://github.com/actions/upload-pages-artifact/issues/97
[upa110]: https://github.com/actions/upload-pages-artifact/issues/110
[tk2540]: https://github.com/actions/toolkit/pull/2540
[renovate]: https://github.com/renovatebot/renovate/pull/48395
