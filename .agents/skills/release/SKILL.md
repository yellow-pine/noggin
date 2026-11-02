---
name: release
description: "Release whatever is pending now: show the version and changelog, run Release Now, report the release."
disable-model-invocation: true
---

The user typed `/release`: that is the go-ahead, so run every step without asking again. Release Now turns on the
open release PR's auto-merge for whatever is pending (docs/adr/0010, CONTRIBUTING.md's Releases). Work in the repo's
root. Wait as CONTRIBUTING.md's "Waiting on CI" line says: each wait below is a `gh` command run in the background,
and you resume when its process exits.

## Steps

1. **Pending.** `gh pr list --state open --head release-please--branches--main --label "autorelease: pending"
   --json number,title,body,url`. No PR: say nothing is pending since the last release, and stop. Otherwise print the
   version (the title's `vX.Y.Z`), the PR's link and its changelog (the body's newest `## X.Y.Z` block, without
   release-please's header and footer).
2. **Release Now.** `gh workflow run release-now.yml` prints the run's URL; `gh run watch <id> --exit-status`.
   Cancelled (a newer Release Please run took its place in their shared queue): run it again. Failed: print
   `gh run view <id> --log-failed`'s error and stop.
3. **Merge.** Release Now marked the draft PR ready, which starts its checks; it merges once its required checks and
   Claude's review pass. Wait on PR `<n>` with the "Waiting on CI" line's loop, its `gh pr checks` given `--required`
   and its `gh pr view` asking for `state,mergeCommit,autoMergeRequest`:
   - `MERGED`: go on with its `mergeCommit.oid`.
   - Open with `autoMergeRequest` null (a Release Please update raced Release Now): run step 2 again, then this step.
   - Open with a red check: print the check and its link, and stop; the release waits on that fix.
   - Open and green (a Release Please update restarted the checks, or the review is still landing): wait again.
4. **Tag.** The merge's Release Please run tags `vX.Y.Z` and creates the GitHub Release:
   `gh run list -w release-please.yml -c <oid> --json databaseId` (it starts seconds after the merge; list again until
   it shows), then `gh run watch <id> --exit-status`. Cancelled (a newer push took its place in the queue): watch the
   newest Release Please run on main instead, which tags the same release. Then `gh release view vX.Y.Z --json url`.
5. **Assets and deploy.** The tag's Release Assets run attaches the Core program zip and the docs, and deploys to the
   `release` environment: `gh run list -w release.yml -b vX.Y.Z --json databaseId` (it starts seconds after the tag;
   list again until it shows), then `gh run watch <id> --exit-status`. The deploy:
   `gh api "repos/{owner}/{repo}/deployments?environment=release&ref=vX.Y.Z" --jq '.[0].statuses_url'`, then that
   URL's newest status (`state`, `environment_url`).

## Report

The tag, the GitHub Release's link, Release Assets' result with its run link, and the `release` deploy's state. A red
step: which one, its link and the failing line.
