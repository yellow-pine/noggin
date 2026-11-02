# The CI image for the jobs that run Blender (docs/adr/0009, #288): the base image (BASE: on main the digest
# images.yml just pushed, on a PR the base it just built) plus Blender from the official tarball, sha256-checked, and
# Mesa's EGL and llvmpipe, where Eevee renders in software. download.blender.org answers 403 to some runners (#367), so
# the tarball falls back to Blender's official mirrors (mirror.blender.org's ?mirrorlist); any of them must match the hash.
# Blender's own pip then uninstalls the bundled requests, urllib3, certifi and idna (only its remote asset libraries
# import them), setuptools and pip itself: nothing we run imports them, and they carried open CVEs (#530)
# BASE's default is a digest-pinned base only so Scorecard counts the FROM as pinned (it reads a ${ARG} default, #533);
# images.yml always passes BASE, so a stale default is never built in CI
ARG BASE=ghcr.io/yellow-pine/noggin-ci-base:main@sha256:09ff172cb483f580f174dda58bc12d7394d9e1615ed79043178289ad732c436d
FROM ${BASE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libegl-mesa0 libgl1-mesa-dri \
 && rm -rf /var/lib/apt/lists/*
ARG BLENDER=5.2.3
ARG BLENDER_SHA256=78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec
RUN for mirror in download.blender.org mirror.clarkson.edu/blender mirrors.ocf.berkeley.edu/blender plug-mirror.rcac.purdue.edu/blender; do \
      curl -fsSL --retry 2 -o /tmp/blender.tar.xz https://$mirror/release/Blender${BLENDER%.*}/blender-$BLENDER-linux-x64.tar.xz \
      && echo "$BLENDER_SHA256  /tmp/blender.tar.xz" | sha256sum -c && break; \
    done \
 && mkdir /opt/blender && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && rm /tmp/blender.tar.xz \
 && py=$(ls /opt/blender/${BLENDER%.*}/python/bin/python3.*) && "$py" -m pip uninstall -y -q requests urllib3 certifi idna setuptools pip \
 && ln -s /opt/blender/blender /usr/local/bin/blender \
 && blender -b --factory-startup --version
USER runner
