# The CI images the jobs run in, by digest: never built, only read. Dependabot (docker, /ci/pins) proposes the digest
# main's CI Images run pushed to :main, which it can't do in a workflow's `container:` (#444); each workflow's Images
# job hands every line to its jobs as an output named after the stage.
FROM ghcr.io/yellow-pine/noggin-ci-base:main@sha256:f068d6e443985ce56ec81a404e5dff6f8bdab869aa519c1bf0ccf06046573d24 AS base
FROM ghcr.io/yellow-pine/noggin-ci-blender:main@sha256:82bd38c42623eee081627d2fdc24d02b7aec5323469f0c7b7791b6f691bd52a3 AS blender
