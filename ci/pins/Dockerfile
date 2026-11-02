# The CI images the jobs run in, by digest: never built, only read. Dependabot (docker, /ci/pins) proposes the digest
# main's CI Images run pushed to :main, which it can't do in a workflow's `container:` (#444); each workflow's Images
# job hands every line to its jobs as an output named after the stage.
FROM ghcr.io/yellow-pine/noggin-ci-base:main@sha256:f068d6e443985ce56ec81a404e5dff6f8bdab869aa519c1bf0ccf06046573d24 AS base
FROM ghcr.io/yellow-pine/noggin-ci-blender:main@sha256:21bb3940c3e3e2d82f8c0b8869c2ee9dc387dbae8ede2a87d4e3607274ec4d06 AS blender
