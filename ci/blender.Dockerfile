# The CI image for the jobs that run Blender (docs/adr/0009, #288): the base image (BASE: on main the digest
# images.yml just pushed, on a PR the base it just built) plus Blender from the official tarball, sha256-checked, and
# Mesa's EGL and llvmpipe, where Eevee renders in software. download.blender.org answers 403 to some runners (#367), so
# the tarball falls back to Blender's official mirrors (mirror.blender.org's ?mirrorlist); any of them must match the hash
ARG BASE
FROM $BASE
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libegl1 libegl-mesa0 libgl1-mesa-dri \
 && rm -rf /var/lib/apt/lists/*
ARG BLENDER=5.2.2
ARG BLENDER_SHA256=84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168
RUN for mirror in download.blender.org mirror.clarkson.edu/blender mirrors.ocf.berkeley.edu/blender plug-mirror.rcac.purdue.edu/blender; do \
      curl -fsSL --retry 2 -o /tmp/blender.tar.xz https://$mirror/release/Blender${BLENDER%.*}/blender-$BLENDER-linux-x64.tar.xz \
      && echo "$BLENDER_SHA256  /tmp/blender.tar.xz" | sha256sum -c && break; \
    done \
 && mkdir /opt/blender && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && rm /tmp/blender.tar.xz \
 && ln -s /opt/blender/blender /usr/local/bin/blender \
 && blender -b --factory-startup --version
USER runner
