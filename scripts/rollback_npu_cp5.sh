#!/usr/bin/env bash
# Authorized recovery of the precise M5 driver change; no whole-root restore.
set -euo pipefail
[[ $EUID -eq 0 ]]
project=/home/shen/AI370-2
checkpoint=$project/output/recovery/CP5-NPU-GATE-20260930T095450Z
[[ $(uname -r) == 6.17.0-14-generic ]]
(cd "$checkpoint" && sha256sum -c SHA256SUMS)
if fuser /dev/accel/accel0 >/dev/null 2>&1; then
  echo 'NPU is in use; refusing unsafe unload' >&2
  exit 1
fi
if dpkg-query -W -f='${Status}' xrt_plugin-amdxdna 2>/dev/null | grep -q 'install ok installed'; then
  dpkg --remove xrt_plugin-amdxdna
fi
if dkms status 2>/dev/null | grep -q '^xrt-amdxdna/2.21.260102.53.release'; then
  dkms remove xrt-amdxdna/2.21.260102.53.release --all
fi
rm -f /etc/udev/rules.d/99-amdxdna.rules
tar --acls --xattrs --numeric-owner -xpf "$checkpoint/platform.tar" -C / \
  lib/modules/6.17.0-14-generic/kernel/drivers/accel/amdxdna \
  usr/lib/firmware/amdnpu opt/xilinx/xrt/lib/libxrt_driver_xdna.so.2 \
  opt/ai370/npu boot/initrd.img-6.17.0-14-generic
if dkms status 2>/dev/null | grep -q 'installed'; then
  echo 'Other DKMS modules present; preserve dkms tool'
else
  dpkg --remove dkms
fi
depmod -a 6.17.0-14-generic
udevadm control --reload-rules
if lsmod | grep -q '^amdxdna '; then modprobe -r amdxdna; fi
modprobe amdxdna
udevadm trigger --subsystem-match=accel
udevadm settle
sha256sum -c "$checkpoint/module.sha256"
sha256sum -c "$checkpoint/firmware.sha256"
[[ $(modinfo -n amdxdna) == /lib/modules/6.17.0-14-generic/kernel/drivers/accel/amdxdna/amdxdna.ko.zst ]]
echo 'CP5 targeted NPU recovery complete; no package-registry overwrite'
