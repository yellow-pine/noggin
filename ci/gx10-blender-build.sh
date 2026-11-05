#!/bin/sh
# Build the pinned native worker inside gx10-blender.Dockerfile, with /work persisted across attempts.
set -eu
cd /work
fetch() {
    file=$1 url=$2 checksum=$3
    [ -f "$file" ] || curl -fL --retry 3 "$url" -o "$file.part"
    [ -f "$file" ] || mv "$file.part" "$file"
    echo "$checksum  $file" | sha256sum -c -
}
fetch blender-5.2.3.tar.xz https://download.blender.org/source/blender-5.2.3.tar.xz 5c66e0ab20da26d684deecfc27e84c4d39e456daaa9112b47eeb45d0e0283876
fetch openvdb-13.0.0.tar.gz https://github.com/AcademySoftwareFoundation/openvdb/archive/refs/tags/v13.0.0.tar.gz 4d6a91df5f347017496fe8d22c3dbb7c4b5d7289499d4eb4d53dd2c75bb454e1
fetch sse2neon.tar.gz https://github.com/DLTcollab/sse2neon/archive/227cc413fb2d50b2a10073087be96b59d5364aea.tar.gz 3427a495743bb6fd1b5f9f806b80f57d67b1ac7ccf39a5f44aedd487fd7e6da1
[ -d blender-5.2.3 ] || tar -xJf blender-5.2.3.tar.xz
[ -d openvdb-13.0.0 ] || tar -xzf openvdb-13.0.0.tar.gz
mkdir -p deps/include
tar -xzf sse2neon.tar.gz --strip-components=1 -C deps/include --wildcards '*/sse2neon.h'
cmake -S openvdb-13.0.0 -B vdb-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/work/deps \
    -DOPENVDB_BUILD_BINARIES=OFF -DOPENVDB_BUILD_UNITTESTS=OFF \
    -DOPENVDB_BUILD_PYTHON_MODULE=OFF -DOPENVDB_BUILD_NANOVDB=ON -DOPENVDB_CORE_STATIC=OFF \
    -DNANOVDB_BUILD_TOOLS=OFF -DUSE_LOG4CPLUS=OFF
cmake --build vdb-build --parallel 8
cmake --install vdb-build
cmake -S blender-5.2.3 -B blender-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/work/install \
    -DCMAKE_PREFIX_PATH=/work/deps -DOPENVDB_ROOT_DIR=/work/deps \
    -DWITH_LIBS_PRECOMPILED=OFF -DWITH_INSTALL_PORTABLE=OFF \
    -DWITH_OPENVDB=ON -DWITH_TBB=ON -DWITH_NANOVDB=ON \
    -DWITH_HEADLESS=OFF -DWITH_GHOST_X11=ON -DWITH_GHOST_WAYLAND=OFF \
    -DWITH_OPENGL_BACKEND=ON -DWITH_VULKAN_BACKEND=OFF \
    -DWITH_CYCLES=ON -DWITH_CYCLES_OSL=OFF -DWITH_CYCLES_EMBREE=OFF \
    -DWITH_CYCLES_DEVICE_CUDA=ON -DWITH_CYCLES_DEVICE_OPTIX=OFF \
    -DWITH_AUDASPACE=OFF -DWITH_CODEC_FFMPEG=OFF -DWITH_INPUT_NDOF=OFF \
    -DWITH_USD=OFF -DWITH_ALEMBIC=OFF -DWITH_MATERIALX=OFF \
    -DWITH_OPENIMAGEDENOISE=OFF -DWITH_CYCLES_PATH_GUIDING=OFF
grep -q '^WITH_OPENVDB:BOOL=ON$' blender-build/CMakeCache.txt
grep -q '^WITH_TBB:BOOL=ON$' blender-build/CMakeCache.txt
cmake --build blender-build --parallel 8
cmake --install blender-build
install/bin/blender -b --factory-startup --version
