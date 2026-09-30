#!/usr/bin/env bash
# File-level recovery material only; no system restore or driver changes.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Requires sudo' >&2; exit 1; }
project=/home/shen/AI370-2
checkpoint="$project/output/recovery/CP5-NPU-GATE-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$checkpoint"
uname -a > "$checkpoint/kernel.txt"
dpkg-query -W > "$checkpoint/packages.txt"
modinfo amdxdna > "$checkpoint/amdxdna.txt"
lsmod > "$checkpoint/lsmod.txt"
find /usr/lib/firmware/amdnpu -type f -exec sha256sum {} + > "$checkpoint/firmware.sha256"
sha256sum "$(modinfo -n amdxdna)" > "$checkpoint/module.sha256"
tar --acls --xattrs --numeric-owner --one-file-system --exclude=boot/efi \
  -C / -cpf "$checkpoint/platform.tar" etc boot var/lib/dpkg/status \
  lib/modules/6.17.0-14-generic/kernel/drivers/accel/amdxdna \
  usr/lib/firmware/amdnpu opt/xilinx/xrt opt/ai370/npu \
  2> "$checkpoint/tar.stderr"
tar --numeric-owner -C /boot/efi -cpf "$checkpoint/efi.tar" .
(cd "$checkpoint" && sha256sum platform.tar efi.tar > SHA256SUMS && sha256sum -c SHA256SUMS)
scratch=$(mktemp -d "$checkpoint/restore-check.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
tar --acls --xattrs --numeric-owner -xpf "$checkpoint/platform.tar" -C "$scratch"
for relative in boot/vmlinuz-6.17.0-14-generic boot/initrd.img-6.17.0-14-generic \
  lib/modules/6.17.0-14-generic/kernel/drivers/accel/amdxdna/amdxdna.ko.zst \
  usr/lib/firmware/amdnpu/17f0_10/npu.sbin.1.0.0.63.zst var/lib/dpkg/status; do
  cmp "/$relative" "$scratch/$relative"
done
mkdir "$scratch/efi"
tar -xpf "$checkpoint/efi.tar" -C "$scratch/efi"
test -d "$scratch/efi/EFI"
printf '%s\n' 'ARCHIVE_SHA_AND_SELECTED_RESTORE_PASS' \
  'LIVE_FILE_LEVEL; SAME_NVME; FULL_BOOT_RESTORE_NOT_TESTED' > "$checkpoint/STATUS"
printf '%s\n' "$checkpoint"
