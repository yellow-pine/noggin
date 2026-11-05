#!/bin/sh
# Build the pinned native worker inside gx10-blender.Dockerfile, with /work persisted across attempts.
set -eu
cd /work
export LD_LIBRARY_PATH="/work/deps/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec 9>/work/install.lock
flock 9
trap 'cat /sys/fs/cgroup/memory.peak > /work/build-memory.peak; cat /sys/fs/cgroup/memory.events > /work/build-memory.events' EXIT
fetch() {
    file=$1 url=$2 checksum=$3
    [ -f "$file" ] || curl -fL --retry 3 "$url" -o "$file.part"
    [ -f "$file" ] || mv "$file.part" "$file"
    echo "$checksum  $file" | sha256sum -c -
}
fetch blender-5.2.3.tar.xz https://download.blender.org/source/blender-5.2.3.tar.xz 5c66e0ab20da26d684deecfc27e84c4d39e456daaa9112b47eeb45d0e0283876
fetch openvdb-13.0.0.tar.gz https://github.com/AcademySoftwareFoundation/openvdb/archive/refs/tags/v13.0.0.tar.gz 4d6a91df5f347017496fe8d22c3dbb7c4b5d7289499d4eb4d53dd2c75bb454e1
fetch sse2neon.tar.gz https://github.com/DLTcollab/sse2neon/archive/227cc413fb2d50b2a10073087be96b59d5364aea.tar.gz 3427a495743bb6fd1b5f9f806b80f57d67b1ac7ccf39a5f44aedd487fd7e6da1
fetch fmt-12.1.0.tar.gz https://github.com/fmtlib/fmt/archive/refs/tags/12.1.0.tar.gz ea7de4299689e12b6dddd392f9896f08fb0777ac7168897a244a6d6085043fea
fetch opencolorio-2.5.0.tar.gz https://github.com/AcademySoftwareFoundation/OpenColorIO/archive/refs/tags/v2.5.0.tar.gz 124e2bfa8a9071959d6ddbb64ffbf78d3f6fe3c923ae23e96a6bbadde1af55b6
fetch openimageio-3.1.13.1.tar.gz https://github.com/AcademySoftwareFoundation/OpenImageIO/archive/refs/tags/v3.1.13.1.tar.gz 0fc59b8e2708ded02d3793b8f3331f037ed49bfcde38158f05ac0e876ebb85b7
fetch eigen.tar.gz https://gitlab.com/libeigen/eigen/-/archive/8a1083e9bf41b91fdea6546681f806154efdc25a/eigen-8a1083e9bf41b91fdea6546681f806154efdc25a.tar.gz cc28a84fdec496c6777596350ea805519bf10f717d21044ae6ba3dd562183a26
fetch abseil-cpp-20250814.1.tar.gz https://github.com/abseil/abseil-cpp/releases/download/20250814.1/abseil-cpp-20250814.1.tar.gz 1692f77d1739bacf3f94337188b78583cf09bab7e420d2dc6c5605a4f86785a1
fetch ceres.tar.gz https://github.com/ceres-solver/ceres-solver/archive/0c70ed3a1a2d6ba47c06c7e8b3b040880bc474db.tar.gz bf0bcc78fae884e59dd893693e52510da7cc6866a7444fdae9ba8f19eae266cd
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
[ -d fmt-12.1.0 ] || tar -xzf fmt-12.1.0.tar.gz
cmake -S fmt-12.1.0 -B fmt-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/work/deps -DFMT_TEST=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
cmake --build fmt-build --parallel 8
cmake --install fmt-build
[ -d OpenColorIO-2.5.0 ] || tar -xzf opencolorio-2.5.0.tar.gz
cmake -S OpenColorIO-2.5.0 -B ocio-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/work/deps -DCMAKE_PREFIX_PATH=/work/deps \
    -DOCIO_BUILD_APPS=OFF -DOCIO_BUILD_TESTS=OFF -DOCIO_BUILD_GPU_TESTS=OFF \
    -DOCIO_BUILD_PYTHON=OFF -DOCIO_BUILD_DOCS=OFF -DOCIO_BUILD_BENCHMARKS=OFF
cmake --build ocio-build --parallel 8
cmake --install ocio-build
[ -d OpenImageIO-3.1.13.1 ] || tar -xzf openimageio-3.1.13.1.tar.gz
cmake -S OpenImageIO-3.1.13.1 -B oiio-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/work/deps -DCMAKE_PREFIX_PATH=/work/deps \
    -DBUILD_MISSING_DEPS=OFF -DOIIO_BUILD_TESTS=OFF -DOIIO_BUILD_TOOLS=ON \
    -DOIIO_BUILD_DOCS=OFF -DUSE_PYTHON=OFF -DUSE_OPENVDB=OFF -DUSE_OPENCV=OFF \
    -DUSE_FFMPEG=OFF -DUSE_LIBRAW=OFF -DUSE_PTEX=OFF
cmake --build oiio-build --parallel 8
cmake --install oiio-build
[ -d eigen-8a1083e9bf41b91fdea6546681f806154efdc25a ] || tar -xzf eigen.tar.gz
cmake -S eigen-8a1083e9bf41b91fdea6546681f806154efdc25a -B eigen-build -G Ninja \
    -DCMAKE_INSTALL_PREFIX=/work/deps -DBUILD_TESTING=OFF -DEIGEN_BUILD_DOC=OFF \
    -DEIGEN_BUILD_BLAS=OFF -DEIGEN_BUILD_LAPACK=OFF
cmake --install eigen-build
[ -d abseil-cpp-20250814.1 ] || tar -xzf abseil-cpp-20250814.1.tar.gz
cmake -S abseil-cpp-20250814.1 -B abseil-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/work/deps -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DABSL_BUILD_TESTING=OFF -DABSL_ENABLE_INSTALL=ON -DCMAKE_CXX_STANDARD=20
cmake --build abseil-build --parallel 8
cmake --install abseil-build
[ -d ceres-solver-0c70ed3a1a2d6ba47c06c7e8b3b040880bc474db ] || tar -xzf ceres.tar.gz
cmake -S ceres-solver-0c70ed3a1a2d6ba47c06c7e8b3b040880bc474db -B ceres-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/work/deps -DCMAKE_PREFIX_PATH=/work/deps \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF \
    -DEigen3_DIR=/work/deps/share/eigen3/cmake -Dabsl_DIR=/work/deps/lib/cmake/absl
cmake --build ceres-build --parallel 8
cmake --install ceres-build
cmake -S blender-5.2.3 -B blender-build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/work/install -DCMAKE_INSTALL_RPATH=/work/deps/lib \
    -DCMAKE_PREFIX_PATH=/work/deps -DOPENVDB_ROOT_DIR=/work/deps \
    -DOpenImageIO_DIR=/work/deps/lib/cmake/OpenImageIO \
    -DOpenColorIO_DIR=/work/deps/lib/cmake/OpenColorIO -Dfmt_DIR=/work/deps/lib/cmake/fmt \
    -DEigen3_DIR=/work/deps/share/eigen3/cmake -DCeres_DIR=/work/deps/lib/cmake/Ceres \
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
rm -f install/ready.json
cmake --install blender-build
uv pip install --python /usr/bin/python3.13 --require-hashes \
    --target /work/install/share/blender/5.2/python/lib/python3.13/dist-packages \
    -r /work/runtime-requirements.txt
install/bin/blender -b --factory-startup --version
install/bin/blender --python-exit-code 1 -b --factory-startup --python-expr "import bpy; assert bpy.app.version == (5,2,3); assert bpy.app.build_options.openvdb; t=bpy.data.node_groups.new('Native SDF check','GeometryNodeTree'); [t.nodes.new(n) for n in ('GeometryNodeMeshToSDFGrid','GeometryNodeSDFGridOffset','GeometryNodeSDFGridBoolean','GeometryNodeSDFGridMean')]; print('native build: startup and SDF nodes verified')" > startup.log 2>&1
cat startup.log
if grep -Eq 'Traceback|ModuleNotFoundError|Exception in module register' startup.log; then exit 1; fi
mkdir -p bin
cat > bin/blender <<'SH'
#!/bin/sh
exec /work/install/bin/blender --python-exit-code 1 "$@"
SH
chmod +x bin/blender
printf '%s\n' '{"version":"5.2.3","source_sha256":"5c66e0ab20da26d684deecfc27e84c4d39e456daaa9112b47eeb45d0e0283876","openvdb":true}' > install/ready.json.tmp
mv install/ready.json.tmp install/ready.json
