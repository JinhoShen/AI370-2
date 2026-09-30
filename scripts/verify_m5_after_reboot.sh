#!/usr/bin/env bash
# Runs once on the next boot; failed verification invokes approved CP5 recovery.
set -euo pipefail
[[ $EUID -eq 0 ]]
project=/home/shen/AI370-2
cd "$project"
state=$project/output/M5/reboot.pending
[[ -f $state ]]
before=$(cat "$state")
now=$(cat /proc/sys/kernel/random/boot_id)
[[ $before != "$now" ]] || { echo 'A new boot is required'; exit 1; }
report=$project/docs/M5/reboot
mkdir -p "$report"
chown shen:shen "$report"
exec > "$report/verification.txt" 2>&1
rollback_on_error() {
  result=$?
  trap - EXIT
  if [[ $result -ne 0 ]]; then
    echo "VERIFICATION FAILED ($result); collecting evidence and recovering CP5"
    journalctl -k -b --no-pager > "$report/kernel-failure.txt"
    if bash scripts/rollback_npu_cp5.sh > "$report/rollback.txt" 2>&1; then
      runuser -u shen -- timeout 30 output/M3/hip-compute > "$report/rollback-hip.txt" 2>&1 || true
      runuser -u shen -- timeout 20 output/M4/build/vulkan-compute output/M4/build/verify.spv > "$report/rollback-vulkan.txt" 2>&1 || true
      echo 'M5_FAIL_CP5_RECOVERED' > "$report/STATUS"
    else
      echo 'M5_FAIL_RECOVERY_INCOMPLETE_SEE_LOG' > "$report/STATUS"
    fi
    rm -f "$state"
    chown -R shen:shen "$report"
    runuser -u shen -- git add docs/M5/reboot || true
    runuser -u shen -- git commit -m 'M5: record reboot verification failure and CP5 recovery' || true
  fi
  exit "$result"
}
trap rollback_on_error EXIT
date -u --iso-8601=seconds
printf 'Boot before: %s\nBoot now: %s\n' "$before" "$now"
[[ $(uname -r) == 6.17.0-14-generic ]]
mokutil --sb-state > "$report/secure-boot.txt"
modinfo amdxdna > "$report/module.txt"
[[ $(modinfo -n amdxdna) == */updates/dkms/amdxdna.ko.zst ]]
grep -q '2.21.260102.53.release' /sys/module/amdxdna/version
dkms status > "$report/dkms.txt"
grep -q '2.21.260102.53.release.*6.17.0-14-generic.*installed' "$report/dkms.txt"
runuser -u shen -- bash scripts/npu21.sh /opt/xilinx/xrt/bin/unwrapped/xrt-smi examine -r all > "$report/xrt-examine.txt" 2>&1
grep -Eq 'RyzenAI-npu4|NPU Strix' "$report/xrt-examine.txt"
grep -q '0000:c6:00.1' "$report/xrt-examine.txt"
grep -q 'NPU Firmware Version.*1.1.2.64' "$report/xrt-examine.txt"
runuser -u shen -- env NPU_OUTPUT_DIR=output/M5/reboot-cnn NPU_RESULT_FILE=docs/M5/reboot/cnn-result.json \
  bash scripts/ryzenai21.sh timeout 180 .venvs/npu21/bin/python verify/npu_cnn.py > "$report/cnn.txt" 2>&1
runuser -u shen -- timeout 30 output/M3/hip-compute > "$report/hip.txt" 2>&1
runuser -u shen -- timeout 20 output/M4/build/vulkan-compute output/M4/build/verify.spv > "$report/vulkan.txt" 2>&1
grep -q 'PASS: 1024' "$report/hip.txt"
grep -q 'PASS: 1024' "$report/vulkan.txt"
journalctl -k -b --no-pager > "$report/kernel.txt"
# Signature warning is a policy warning when Secure Boot is disabled and
# the exact requested module has already passed the path/version checks.
python3 verify/m5_kernel_policy.py "$report/kernel.txt" "$report/secure-boot.txt" /sys/module/amdxdna/version > "$report/kernel-policy.txt"

# All functional gates passed. Documentation errors must not roll back working hardware.
trap - EXIT
python3 - <<'PY'
from pathlib import Path
import json, shutil
project=Path('/home/shen/AI370-2')
result=json.loads((project/'docs/M5/reboot/cnn-result.json').read_text())
shutil.copyfile(project/result['profile_path'],project/'docs/M5/reboot/ort-profile.json')
(project/'docs/M5/reboot/RESULT.md').write_text('# M5 PASS — NPU Golden State\n\nFull post-reboot verification passed: exact DKMS 2.21.260102.53.release, firmware 1.1.2.64, XRT XDNA2 detection, CNN VitisAI-only execution with CPU fallback disabled, positive NPU hardware time, CPU reference correctness and HIP/Vulkan regression. See cnn-result.json, ort-profile.json, module.txt, xrt-examine.txt and kernel-policy.txt. Expected signature warning under disabled Secure Boot is recorded as WARNING. Previous policy false negative and CP5 recovery are preserved in ../retry/previous-policy-false-negative/.\n')
p=project/'docs/BUILD_PROGRESS.md'
s=p.read_text()
lines=s.splitlines()
lines=[('| M5 NPU | PASS | docs/M5/reboot/STATUS；重開機後DKMS/firmware、CNN正確性、硬體usage、no-fallback及HIP/Vulkan通過 |' if line.startswith('| M5 NPU |') else line) for line in lines]
p.write_text('\n'.join(lines)+'\n')
PY
echo 'M5_PASS_MODEL_CORRECT_NO_CPU_FALLBACK_POST_REBOOT' > "$report/STATUS"
printf '\n## Reboot validation\n\nM5 PASS: see reboot/STATUS, cnn-result.json, XRT/module/version and HIP/Vulkan evidence.\n' >> docs/M5/RESULT.md
rm -f "$state"
chown -R shen:shen "$report"
chown shen:shen docs/M5/RESULT.md
chown shen:shen docs/BUILD_PROGRESS.md
runuser -u shen -- git add docs/M5/reboot docs/M5/RESULT.md docs/BUILD_PROGRESS.md
runuser -u shen -- git commit -m 'M5 PASS: establish NPU Golden State after full post-reboot verification'

runuser -u shen -- git tag -a ai370-2-npu-golden -m "M5 verified NPU Golden State: XRT 2.21, DKMS 2.21.260102.53.release, firmware 1.1.2.64"
