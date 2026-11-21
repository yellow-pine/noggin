# Native GX10 build dependencies (#979). Compile and runtime files stay in its private tool workspace.
FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates cmake curl git ninja-build pkg-config xz-utils \
      python3-dev python3-numpy libboost-iostreams-dev libboost-system-dev libboost-thread-dev \
      libblosc-dev libepoxy-dev libfftw3-dev libfmt-dev libfreetype-dev libfribidi-dev \
      libharfbuzz-dev libjpeg-dev libopenexr-dev libopenimageio-dev libopencolorio-dev \
      libpng-dev libpugixml-dev libtbb-dev libtiff-dev libwebp-dev libxml2-dev libyaml-cpp-dev \
      libzstd-dev zlib1g-dev libx11-dev libxi-dev libxcursor-dev libxfixes-dev libxinerama-dev \
      libxkbcommon-dev libxrandr-dev libxxf86vm-dev libegl1-mesa-dev libgl1-mesa-dev \
      libgl1-mesa-dri libegl-mesa0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends openimageio-tools ngspice rsync \
 && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends libeigen3-dev libosd-dev libopenjp2-7-dev libsndfile1-dev \
 && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends libceres-dev libgmp-dev libdraco-dev libmeshoptimizer-dev \
 && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends cython3 python3-zstandard \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /uvx /usr/local/bin/
RUN useradd --uid 1000 --create-home builder
USER builder
ENV PATH=/work/install/bin:$PATH
ENV LD_LIBRARY_PATH=/work/deps/lib
WORKDIR /work
