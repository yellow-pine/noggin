#!/bin/sh
# Rebase a PR onto origin/main from this session and push it (CONTRIBUTING.md, #429). --help says how.
set -eu

die() { echo "rebase_pr: $*" >&2; exit 1; }

case ${1:-} in
'' | -h | --help)
	cat <<'EOF'
usage: scripts/rebase_pr.sh <pr> [--take]   (run from one of this session's worktrees, ../noggin-wt/<session>/<branch>)

Rebases PR <pr> onto origin/main in this session's worktree of its branch (made if missing), runs make check-light,
pushes --force-with-lease against the head it read, and prints the new head. Refuses while the PR is labelled
session:<another session> (--take swaps the label to this session's), while a rebase is in progress, or when
check-light fails. An unlabelled PR gets this session's label.

gh pr update-branch <pr> is the alternative that rewrites nothing: GitHub merges main into the branch, no force push.
EOF
	exit 0
	;;
esac
pr=$1 take=${2:-}

top=$(git rev-parse --show-toplevel)
case $top in */noggin-wt/*/*) ;; *) die "run from one of this session's worktrees, ../noggin-wt/<session>/<branch>" ;; esac
rest=${top#*/noggin-wt/}
session=${rest%%/*}

info=$(gh pr view "$pr" --json headRefName,headRefOid,labels \
	--jq '.headRefName, .headRefOid, (.labels[].name | select(startswith("session:")))')
owner=$(echo "$info" | sed -n 3p)
owner=${owner#session:}
[ -z "$owner" ] || [ "$owner" = "$session" ] || [ "$take" = --take ] ||
	die "PR #$pr is labelled session:$owner; --take to take it from that session"
branch=$(echo "$info" | sed -n 1p)
head=$(echo "$info" | sed -n 2p)

git fetch -q origin main "$branch"
wt=${top%%/noggin-wt/*}/noggin-wt/$session/$branch
if [ ! -d "$wt" ]; then
	if git worktree list --porcelain | grep -qx "branch refs/heads/$branch"; then
		# the session it was taken from still has the branch: moving it would leave that worktree's files out of step
		git worktree add -q --detach "$wt" "$head"
	elif git show-ref -q --verify "refs/heads/$branch"; then
		git worktree add -q "$wt" "$branch"
	else
		git worktree add -q -b "$branch" "$wt" "$head"
	fi
fi
cd "$wt"
on=$(git symbolic-ref -q --short HEAD || true) # empty when detached
[ -z "$on" ] || [ "$on" = "$branch" ] || die "$wt has $on checked out, not PR #$pr's $branch"
for d in rebase-merge rebase-apply; do
	[ ! -e "$(git rev-parse --git-path $d)" ] || die "a rebase is in progress in $wt; finish it (git rebase --continue) or abort it first"
done

if [ "$owner" != "$session" ]; then
	gh label create "session:$session" --color ededed --force >/dev/null
	gh pr edit "$pr" --add-label "session:$session" ${owner:+--remove-label "session:$owner"} >/dev/null
fi

if ! git merge-base --is-ancestor "$head" HEAD; then
	git merge-base --is-ancestor HEAD "$head" || die "$wt and PR #$pr's head $head have diverged; reconcile them first"
	git reset -q --keep "$head" # catch up on what was pushed from elsewhere
fi
git rebase -q origin/main ||
	die "rebase stopped in $wt: resolve, git rebase --continue, make check-light, then git push --force-with-lease=$branch:$head origin HEAD:$branch"
make check-light
# --no-verify: the pre-push hook would only run check-light again
git push -q --no-verify --force-with-lease="$branch:$head" origin "HEAD:$branch"
git rev-parse HEAD
