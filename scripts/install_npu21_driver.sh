#!/usr/bin/env bash
# Use only within the explicitly approved DKMS/firmware change gate.
set -euo pipefail
[[ $EUID -eq 0 ]]
cd /home/shen/AI370-2
[[ $(uname -r) == 6.17.0-14-generic ]]
plugin=resources/Agent_Tools_Docs/03_RyzenAI/XRT_NPU/xrt_plugin.2.21.260102.53.release_24.04-amd64-amdxdna.deb
dkms_deb=resources/Downloads/NPU-Research/dkms_3.0.11-1ubuntu13_all.deb
echo "802696333ef159bc0cbf9ba65f89acc5e3fb3023d461c3ad1307fe7a05436ccb  $plugin" | sha256sum -c -
echo "18d098c65e3002040afc11f80656e84377551a5d1bdcd3933cdf6ae2e58dcd75  $dkms_deb" | sha256sum -c -
dpkg-query -W -f='${Version}' xrt-base | grep -qx '2.21.75'
dpkg-query -W -f='${Version}' xrt-npu | grep -qx '2.21.75'
if fuser /dev/accel/accel0 >/dev/null 2>&1; then exit 1; fi
simulation=$(apt-get -s --no-install-recommends install "./$dkms_deb" "./$plugin")
printf '%s\n' "$simulation"
grep -q '^0 upgraded, .*0 to remove' <<< "$simulation"
while read -r name; do
  [[ $name == dkms || $name == xrt_plugin-amdxdna ]] || exit 1
done < <(awk '/^Inst / {print $2}' <<< "$simulation")
# dpkg uses the exact local DEBs; no fetching or dependency upgrade.
dpkg -i "$dkms_deb" "$plugin"
printf '%s\n' 'KERNEL=="accel*",DRIVERS=="amdxdna",GROUP="render",MODE="0660"' > /etc/udev/rules.d/99-amdxdna.rules
udevadm control --reload-rules
udevadm trigger --subsystem-match=accel
udevadm settle
update-initramfs -u -k 6.17.0-14-generic
