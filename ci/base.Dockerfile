# The CI base image (docs/adr/0009, #288): the system tools uv can't install for the jobs that run in it
# (checks.yml's Site and Code), from pinned sources (gh the one exception, below), and uv's Python with the venv synced
# from uv.lock (#725), which a job links as its .venv.
# .github/workflows/images.yml builds it and -blender on top; the jobs run them by the :main tag. Dependabot bumps the
# FROM digests below after its two-week cooldown, where the registry dates the release (ADR 0012).
FROM node:24.22.2-trixie-slim@sha256:54f84b4cf8432b21aaffd5d3ce8d41e12cea0d10d33c09d2f3c9879d49d6b446 AS node
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
      ca-certificates curl git jq python3 shellcheck unzip xz-utils zstd \
      ngspice libgl1 libgomp1 \
      libice6 libsm6 libx11-6 libxcursor1 libxext6 libxfixes3 libxi6 libxkbcommon0 libxrender1 libxxf86vm1 \
 && rm -rf /var/lib/apt/lists/*
# gh from GitHub CLI's signed apt repo, as cli/cli's docs/install_linux.md has it, its keyring checked against the
# sha256 published there. Not pinned and no 14-day cooldown, by exception (ADR 0012, #529): this step takes the newest
# gh whenever it rebuilds (a new Ubuntu digest above, or no cache), where Ubuntu's archive froze it at 2.45, built with
# a Go whose stdlib Grype flags
ARG GH_KEYRING_SHA256=6084d5d7bd8e288441e0e94fc6275570895da18e6751f70f057485dc2d1a811b
RUN keyring=/etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && install -d -m 755 /etc/apt/keyrings \
 && curl -fsSL -o "$keyring" https://cli.github.com/packages/githubcli-archive-keyring.gpg \
 && echo "$GH_KEYRING_SHA256  $keyring" | sha256sum -c \
 && chmod go+r "$keyring" \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=$keyring] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/* \
 && gh --version
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=yq /usr/bin/yq /usr/local/bin/yq
COPY --from=node /usr/local/bin/node /usr/local/bin/
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
# a newer npm than the one Node bundles, for the security fixes in npm's own modules (#532): the registry's tarball,
# checked against the sha512 the registry publishes (`npm view npm@$NPM dist.integrity`, base64, here in hex) and
# unpacked over the bundled npm, all `npm install -g` does for npm, which Scorecard counts unpinned whatever its
# argument (#563, docs/research/2026-11-02-scorecard-npm-pinning.md). The first check fails the build once Node bundles
# this npm or a newer one: then drop the step
ARG NPM=11.21.1
ARG NPM_SHA512=613ccbe90044257c87713bb426251ced128ca7e9b3949b65eeb18b98445a5d441e14720c73d6ad76be86f4cf42f2f0d66efe347a9a13400ccd2f6fcfb5954385
RUN printf '%s\n' "$(npm -v)" "$NPM" | sort -CuV \
 && curl -fsSL -o /tmp/npm.tgz "https://registry.npmjs.org/npm/-/npm-$NPM.tgz" \
 && echo "$NPM_SHA512  /tmp/npm.tgz" | sha512sum -c \
 && dir=/usr/local/lib/node_modules/npm && rm -rf "$dir" && mkdir "$dir" \
 && tar -xzf /tmp/npm.tgz -C "$dir" --strip-components=1 && rm /tmp/npm.tgz \
 && test "$(npm -v)" = "$NPM"
# the venv sits on another mount than uv's cache (no hard links)
ENV UV_LINK_MODE=copy

# Chrome for Testing at Playwright's channel="chrome" path (site/smoke.pw.mjs), with the packages its deb.deps lists,
# which the site's mermaid-cli (a devDependency, site/site.test.mjs) drives too. A container has no user namespaces for
# Chrome's sandbox: Playwright passes --no-sandbox, mermaid-cli's Puppeteer does not, so it gets a wrapper that does
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
RUN useradd -u 1001 -m runner && install -d -o runner /opt/npm /opt/uv
USER runner
ENV PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chrome-no-sandbox PUPPETEER_SKIP_DOWNLOAD=true \
    npm_config_cache=/opt/npm npm_config_prefer_offline=true

# uv's Python (.python-version) and the venv synced from uv.lock (#725): a job links /opt/uv/venv as its checkout's
# .venv, so uv run downloads nothing, or only what a newer uv.lock changed. Last, so a lock change rebuilds this alone;
# images.yml rebuilds it on main whenever these three files change
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python
COPY --chown=runner pyproject.toml uv.lock .python-version /opt/uv/project/
RUN UV_PROJECT_ENVIRONMENT=/opt/uv/venv uv sync --directory /opt/uv/project --frozen --no-cache
