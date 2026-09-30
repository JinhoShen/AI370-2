#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo in the local terminal.' >&2; exit 1; }
project=/home/shen/AI370-2
cd "$project/resources/Downloads"
names=(
  cmake_3.28.3-1build7_amd64.deb
  cmake-data_3.28.3-1build7_all.deb
  ninja-build_1.11.1-2_amd64.deb
  vulkan-tools_1.3.275.0+dfsg1-1_amd64.deb
  libvulkan-dev_1.3.275.0-1build1_amd64.deb
  glslc_2023.8-1build1_amd64.deb
  libshaderc1_2023.8-1build1_amd64.deb
  libjsoncpp25_1.9.5-6build1_amd64.deb
  librhash0_1.4.3-3build1_amd64.deb
)
packages=()
checks=$(mktemp)
trap 'rm -f "$checks"' EXIT
for name in "${names[@]}"; do
  relative="Ubuntu24.04/debs/$name"
  test -f "$relative"
  awk -v path="$relative" '$2 == path {print; found=1} END {if (!found) exit 1}' \
    "$project/docs/SHA256SUMS.downloads" >> "$checks"
  packages+=("./$relative")
done
sha256sum -c "$checks"
apt-get -s --no-download --no-install-recommends --no-upgrade --no-remove install "${packages[@]}"
echo 'Installing only listed local development/diagnostic packages; no upgrade/download/removal.'
apt-get --no-download --no-install-recommends --no-upgrade --no-remove install "${packages[@]}" \
  2>&1 | tee "$project/docs/M2_M4_INSTALL.log"
echo 'Installation complete. Agent must perform functional verification before phase PASS.'
