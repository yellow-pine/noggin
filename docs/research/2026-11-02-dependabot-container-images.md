# Dependabot and the workflows' container images (2026-11-02, #444)

For #444: the `docker` entry for `/.github/workflows` (the jobs' `container: image: ghcr.io/yellow-pine/noggin-ci-…:main@sha256:…`)
failed every run, so the digests never moved. Can Dependabot bump a workflow's `container:` image, and does it refresh
the digest of a tag that is not a version (`:main`)?

## What the runs say

Every `docker in /.github/workflows` update job failed with `dependency_file_not_found`: "No Dockerfiles nor Kubernetes
YAML found in /.github/workflows" (Dependabot Updates runs 41362037760 and 41365267166, 2026-11-01/02).

## The source (dependabot/dependabot-core, `main`, read 2026-11-02)

- **The `docker` ecosystem reads Dockerfiles and Kubernetes YAML only.** `docker/lib/dependabot/docker/file_fetcher.rb`
  fetches files whose name matches `/dockerfile|containerfile/i`, plus the YAML files the shared fetcher keeps.
  `docker/lib/dependabot/shared/shared_file_fetcher.rb` keeps a `.yml`/`.yaml` only if it looks like a Helm chart or
  a Kubernetes resource: `likely_kubernetes_resource?` wants top-level `apiVersion` and `kind` keys. A workflow has
  neither (and GitHub rejects keys a workflow does not define), so the directory has no file it reads.
- **The `github-actions` ecosystem reads only `uses:`.** `github_actions/lib/dependabot/github_actions/file_parser.rb`
  walks the workflow's `uses` declarations and skips `docker://` ones ("TODO: Support Docker references"); `container:`
  is never read.
- **A non-version tag gets digest updates.** `docker/lib/dependabot/docker/update_checker.rb`
  (`digest_requirement_up_to_date?`): for a `tag@sha256:digest` whose tag is not comparable (its comments name
  `latest`, `alpine`, distro codenames), the expected digest is the tag's current one in the registry, so a new push to
  `:main` is proposed. The digest-only refresh respects `cooldown` (`digest_within_cooldown?`), so the entry keeps none.
- **Registry access:** `ghcr.io/yellow-pine/noggin-ci-base` and `-blender` are public packages (`gh api
  orgs/yellow-pine/packages/container/noggin-ci-base`: `visibility: public`), so Dependabot needs no `registries:`.

## So

Dependabot cannot bump a pin that lives in a workflow's `container:`. The pins move to a Dockerfile it reads
(`ci/pins/Dockerfile`, one `FROM <image>:main@sha256:… AS <name>` per image, never built), in a directory of its own so
the `/ci` entry's 14-day cooldown and images.yml's `ci/*.Dockerfile` trigger leave it alone, and the jobs read their
image from it: a job's `container.image` takes `needs` outputs, so a small `Images` job reads the file first.
