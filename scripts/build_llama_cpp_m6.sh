#!/usr/bin/env bash
set -euo pipefail

repo=/home/shen/AI370-2
archive=$repo/resources/Downloads/LocalAI/llama.cpp/llama.cpp-v0.5.0-7fe450e19305.tar.gz
sha256=a6861d549427f814dc591c439e08206f67ffaba0248344d421589abf18199e67
source_commit=7fe450e19305b828c199d602c23a8337aaa1f03b
root=$repo/output/M6
src=$root/source
backend=${1:?usage: build_llama_cpp_m6.sh cpu|vulkan|hip}

case "$backend" in cpu|vulkan|hip) ;; *) echo "unsupported backend: $backend" >&2; exit 2;; esac
echo "$sha256  $archive" | sha256sum --check --status || { echo 'llama.cpp archive SHA mismatch' >&2; exit 1; }
mkdir -p "$root"
if [[ ! -f $src/CMakeLists.txt ]]; then
    mkdir -p "$src"
    tar -xzf "$archive" --strip-components=1 -C "$src"
fi

build=$root/build-$backend
args=(-S "$src" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON
      -DLLAMA_BUILD_COMMIT="$source_commit" -DLLAMA_BUILD_NUMBER=0
      -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF)
case "$backend" in
  cpu)
    args+=(-DGGML_VULKAN=OFF -DGGML_HIP=OFF)
    ;;
  vulkan)
    args+=(-DGGML_VULKAN=ON -DGGML_HIP=OFF)
    ;;
  hip)
    args+=(-DGGML_VULKAN=OFF -DGGML_HIP=ON -DGPU_TARGETS=gfx1150)
    ;;
esac
if [[ $backend == hip ]]; then
    HIPCXX=/opt/rocm-7.2.1/lib/llvm/bin/clang HIP_PATH=/opt/rocm-7.2.1 \
      cmake "${args[@]}"
else
    cmake "${args[@]}"
fi
cmake --build "$build" --parallel "${M6_BUILD_JOBS:-8}"
"$build/bin/llama-cli" --version
"$build/bin/llama-server" --version
"$build/bin/llama-cli" --list-devices
