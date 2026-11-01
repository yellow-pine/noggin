# The CI base image (docs/adr/0009, #288): the system tools uv can't install for the jobs that run in it
# (site-checks.yml's site; check.yml's code once main has pushed an image with ngspice), from pinned sources; `uv sync` in the job brings our Python packages.
# .github/workflows/images.yml builds it and -blender on top; the jobs pin them by digest. Dependabot bumps the FROM
# digests below after its two-week cooldown, where the registry dates the release (ADR 0012).
FROM node:24.22.0-trixie-slim@sha256:a6155384446670e9719bdc4fd0ebe4d4b29fb32a8d6aa523da3547a6cfbcf22c AS node
FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv
FROM mikefarah/yq:4.54.1@sha256:4b3d9475d65571d28cbb19544d3820ec2945e4c8b2f18279394282b8dc3a592e AS yq

FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
LABEL org.opencontainers.image.source=https://github.com/yellow-pine/noggin
ARG DEBIAN_FRONTEND=noninteractive
# python3: scripts/ci_budget.py's (uv downloads the venv's, .python-version); ngspice: model/electrical.py's SPICE circuit,
# which spicelib runs in batch mode; libgl1 and the X libraries:
# what VTK (under CadQuery) and Blender load even in the background; the rest what the jobs' steps call (the runner
# image's)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl gh git jq make python3 shellcheck unzip xz-utils zstd \
      ngspice libgl1 libgomp1 \
      libice6 libsm6 libx11-6 libxcursor1 libxext6 libxfixes3 libxi6 libxkbcommon0 libxrender1 libxxf86vm1 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=yq /usr/bin/yq /usr/local/bin/yq
COPY --from=node /usr/local/bin/node /usr/local/bin/
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
# the venv sits on another mount than uv's cache (no hard links)
ENV UV_LINK_MODE=copy

# Chrome for Testing at Playwright's channel="chrome" path (web/test_viewer.py), with the packages its deb.deps lists,
# and mermaid-cli (test_site.py) at mkdocs.yml's versions (ci/test_images.py) in npx's cache, driving that Chrome.
# A container has no user namespaces for Chrome's sandbox: Playwright passes --no-sandbox, mermaid-cli's Puppeteer
# does not, so it gets a wrapper that does
ARG CHROME=155.0.8059.84
ARG CHROME_SHA256=cf0f049892dea22e6a6db26d47ed0d7776b7158edcbec4634086633df8bafcbc
RUN curl -fsSL -o /tmp/chrome.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROME/linux64/chrome-linux64.zip \
 && echo "$CHROME_SHA256  /tmp/chrome.zip" | sha256sum -c \
 && mkdir -p /opt/google && unzip -q /tmp/chrome.zip -d /opt/google && rm /tmp/chrome.zip \
 && mv /opt/google/chrome-linux64 /opt/google/chrome \
 && apt-get update && apt-get satisfy -y --no-install-recommends "$(paste -sd, /opt/google/chrome/deb.deps)" \
 && rm -rf /var/lib/apt/lists/* \
 && printf '#!/bin/sh\nexec /opt/google/chrome/chrome --no-sandbox "$@"\n' > /usr/local/bin/chrome-no-sandbox \
 && chmod +x /usr/local/bin/chrome-no-sandbox

# the jobs run as the runner's user (uid 1001), who owns the checkout, so git trusts it
RUN useradd -u 1001 -m runner && install -d -o runner /opt/npm
USER runner
ENV PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chrome-no-sandbox PUPPETEER_SKIP_DOWNLOAD=true \
    npm_config_cache=/opt/npm npm_config_prefer_offline=true
ARG MERMAID=11.17.2
ARG MERMAID_CLI=11.17.1
RUN printf 'graph TD\n  A --> B\n' > /tmp/a.mmd \
 && npx -y -p @mermaid-js/mermaid-cli@$MERMAID_CLI -p mermaid@$MERMAID mmdc -q -i /tmp/a.mmd -o /tmp/a.svg \
 && rm -r /tmp/a.* $npm_config_cache/_cacache   # the tarballs: npx runs the installed tree (_npx)
