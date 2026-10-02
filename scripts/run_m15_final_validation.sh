#!/usr/bin/env bash
# One controlled M15 software regression. No package/stack changes or FPGA programming.
set -uo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
stamp="$(date +%Y%m%dT%H%M%S%z)"
out="$repo/output/M15/unified-$stamp"
mkdir -p "$out/models"
suite_started="$(date --iso-8601=seconds)"
status_file="$out/status.tsv"
printf 'started=%s\nhead=%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" > "$out/run-metadata.txt"
: > "$status_file"

record() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" | tee -a "$status_file"; }
capture() {
  local name="$1"; shift
  if "$@" >"$out/$name.log" 2>&1; then record PASS "$name" 'exit 0'; return 0; else local rc=$?; record FAIL "$name" "exit $rc"; return "$rc"; fi
}
kernel_faults_since() {
  local start="$1" name="$2"
  journalctl -k --since "$start" --no-pager 2>"$out/$name-journal-error.log" | \
    rg -i 'amdgpu.*(page fault|vm_validate|not enough memory|device lost|reset|ring timeout|error)|TTM.*(corrupt|error)|soft lockup|amdxdna.*(error|fault|timeout)' \
    >"$out/$name-kernel-faults.log" || true
  [[ ! -s "$out/$name-kernel-faults.log" ]]
}

# Capture actual host/platform and the protected stack before tests.
{
  date --iso-8601=seconds
  uname -a
  cat /etc/os-release
  lscpu
  free -h
  df -h /
  printf '\n[protected packages]\n'
  dpkg-query -W -f='${binary:Package}\t${Version}\n' linux-image-"$(uname -r)" mesa-vulkan-drivers libdrm-amdgpu1 rocm-core hip-runtime-amd xrt-base xrt-npu xrt_plugin-amdxdna 2>&1
  printf '\n[amdxdna module]\n'
  modinfo amdxdna 2>&1 | rg '^(filename|version|signer|sig_key):' || true
  cat /sys/module/amdxdna/version 2>/dev/null || true
  printf '\n[swap]\n'
  cat /proc/swaps
} > "$out/platform-before.txt" 2>&1

# Existing bounded workstation verifier is the single M15 GPU/Vulkan/NPU/tool readiness pass.
started="$(date --iso-8601=seconds)"
verifier_ok=0
if scripts/verify_m14_workstation.sh >"$out/workstation-verifier.log" 2>&1; then
  verifier_ok=1
  record PASS 'GPU-Vulkan-XRT-NPU-tool-Ross verifier' 'existing guarded suite returned PASS_WITH_DEFERRED/zero failures; see nested summary'
else
  record FAIL 'GPU-Vulkan-XRT-NPU-tool-Ross verifier' 'guarded suite returned nonzero; inspect nested summary and kernel audit'
fi
cat "$out/workstation-verifier.log"
kernel_faults_since "$started" 'workstation-verifier' || record FAIL 'workstation verifier kernel audit' 'fault signature found; do not run further GPU tests'
if [[ -s "$out/workstation-verifier-kernel-faults.log" || "$verifier_ok" != 1 ]]; then
  gpu_safe=0
else
  gpu_safe=1
fi

# Inventory all full GGUF files supplied with this workstation's local resources.
model_dir="$repo/resources/Agent_Tools_Docs/04_Local_AI/GGUF"
find "$model_dir" -maxdepth 1 -type f -iname '*.gguf' -print0 | sort -z | \
  xargs -0 -r sha256sum > "$out/models/sha256.txt"
if [[ -x "$repo/.venvs/npu21/bin/python" ]] && "$repo/.venvs/npu21/bin/python" -c 'import numpy' >/dev/null 2>&1; then
  metadata_python="$repo/.venvs/npu21/bin/python"
else
  metadata_python=python3
fi
printf 'metadata_python=%s\n' "$metadata_python" > "$out/models/metadata-parser-runtime.txt"
python3 - "$model_dir" "$out/models/file-inventory.tsv" <<'PY'
from datetime import datetime
from pathlib import Path
import sys
root, destination = Path(sys.argv[1]), Path(sys.argv[2])
with destination.open("w", encoding="utf-8") as out:
    out.write("bytes\tmtime_local_iso\tpath\n")
    for path in sorted(root.glob("*.gguf")):
        st = path.stat()
        out.write(f"{st.st_size}\t{datetime.fromtimestamp(st.st_mtime).astimezone().isoformat()}\t{path}\n")
PY
while IFS= read -r -d '' model; do
  name="$(basename "$model")"
  if timeout 180s "$metadata_python" scripts/inspect_gguf_metadata_m7.py "$model" >"$out/models/${name}.metadata.json" 2>"$out/models/${name}.metadata.stderr"; then
    record PASS "GGUF metadata: $name" 'local llama.cpp gguf-py parsed GGUF metadata/tensor descriptors; payloads not loaded'
  else
    rc=$?
    record FAIL "GGUF metadata: $name" "metadata parser exit $rc"
  fi
done < <(find "$model_dir" -maxdepth 1 -type f -iname '*.gguf' -print0 | sort -z)
if rg -q 'd8d7842cc657d720f39546878e431937c84473aa130c36371669ac17c80c7361  .*/Qwen3.6-35B-A3B-Q8_0.gguf$' "$out/models/sha256.txt"; then
  record PASS 'Qwen3.6 Q8 integrity' 'SHA256 matches the recorded download digest'
else
  record FAIL 'Qwen3.6 Q8 integrity' 'expected SHA256 mismatch or file absent'
fi
if find "$repo/resources" -type f -iname '*qwen3*14b*.gguf' -print -quit | rg -q .; then
  record PASS 'Qwen3-14B model availability' 'candidate file found under resources'
else
  record DEFERRED 'Qwen3-14B CPU/Vulkan/ROCm' 'no Qwen3-14B GGUF exists under resources; no substitute model used'
fi

# M15 bounded inference uses the already-selected M7 IQ2 model. One layer only on GPU,
# 32-token context, <=4 generated tokens, one model at a time, cgroup swap disabled.
baseline_model="$model_dir/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf"
if [[ -r "$baseline_model" ]]; then
  for backend in cpu vulkan hip; do
    [[ "$backend" == cpu || "$gpu_safe" == 1 ]] || { record NOT_TESTED "M7 model $backend inference" 'stopped by prior M15 kernel-fault safety gate'; continue; }
    binary="$repo/output/M6/build-$backend/bin/llama-cli"
    device=none; layers=0
    case "$backend" in vulkan) device=Vulkan0; layers=1;; hip) device=ROCm0; layers=1;; esac
    available="$(awk '/^MemAvailable:/ {print $2*1024}' /proc/meminfo)"
    if (( available < 26843545600 )); then record DEFERRED "M7 model $backend inference" "resource guard: MemAvailable ${available} bytes < 25 GiB"; continue; fi
    started="$(date --iso-8601=seconds)"
    unit="ai370-m15-${backend}-$(date +%s)"
    command=(/usr/bin/timeout --signal=TERM --kill-after=5s 300s "$binary" --model "$baseline_model" --ctx-size 32 --batch-size 8 --ubatch-size 4 --threads 4 --threads-batch 4 --n-predict 4 --reasoning off --device "$device" --gpu-layers "$layers" --prompt 'Reply with exactly READY.' --single-turn --no-display-prompt --simple-io --verbose)
    if systemd-run --user --scope --quiet --unit="$unit" -p MemoryMax=18G -p MemorySwapMax=0 -p CPUQuota=400% -- "${command[@]}" >"$out/models/m7-iq2-${backend}.log" 2>&1; then
      generation_ok=0; backend_ok=0
      rg -q 'eval time =.*[1-9][0-9]* tokens' "$out/models/m7-iq2-${backend}.log" && generation_ok=1
      case "$backend" in
        cpu) rg -q 'CPU_Mapped model buffer size = *[1-9]' "$out/models/m7-iq2-${backend}.log" && backend_ok=1;;
        vulkan) rg -q 'offloaded 1/41 layers to GPU' "$out/models/m7-iq2-${backend}.log" && rg -q 'Vulkan0 model buffer size = *[1-9]' "$out/models/m7-iq2-${backend}.log" && backend_ok=1;;
        hip) rg -q 'offloaded 1/41 layers to GPU' "$out/models/m7-iq2-${backend}.log" && rg -q 'ROCm0 model buffer size = *[1-9]' "$out/models/m7-iq2-${backend}.log" && backend_ok=1;;
      esac
      if [[ "$generation_ok" == 1 && "$backend_ok" == 1 ]]; then record PASS "M7 model $backend inference" 'bounded generation completed and requested backend/device allocation was visible in the log'; else record FAIL "M7 model $backend inference" 'generation or actual backend/device allocation was not confirmed'; fi
    else
      rc=$?
      record FAIL "M7 model $backend inference" "bounded inference exit $rc"
    fi
    if [[ "$backend" != cpu ]]; then
      kernel_faults_since "$started" "m7-iq2-${backend}" || { record FAIL "M7 model $backend kernel audit" 'GPU/kernel fault signature found; stop all remaining GPU inference'; gpu_safe=0; }
      [[ ! -s "$out/m7-iq2-${backend}-kernel-faults.log" ]] || gpu_safe=0
    fi
  done
else
  record DEFERRED 'M7 local LLM inference' 'previously selected M7 IQ2 GGUF is absent'
fi

# Preserve M7.1 as an explicit open issue; its prior Vulkan command-submission/device-lost
# failure is not retried. Q8 CPU requires the existing >=44 GB gate; ROCm was gated on Vulkan.
record OPEN 'M7.1 Qwen3.6 Q8 Vulkan' 'existing bounded attempt produced RADV command-submission errors/device loss; keep OPEN and do not replay known kernel/driver failure'
q8_available="$(awk '/^MemAvailable:/ {print $2*1024}' /proc/meminfo)"
if (( q8_available >= 44000000000 )); then
  record NOT_TESTED 'Qwen3.6 Q8 CPU' 'model CPU smoke already has M7 evidence; no additional duplicate inference in final suite'
else
  record DEFERRED 'Qwen3.6 Q8 CPU' "resource guard requires 44 GB available RAM; current ${q8_available} bytes"
fi
record NOT_TESTED 'Qwen3.6 Q8 Vulkan/ROCm inference' 'Vulkan is a known device-lost/kernel error case; ROCm remains gated; no replay'
record NOT_TESTED 'Qwen3.8 candidate inference' 'the three new Qwen3.8 files are inventory candidates only; previous instruction limits them to inventory'

# Current end-of-suite targeted kernel log audit.
kernel_faults_since "$suite_started" 'final-suite' || record FAIL 'final targeted kernel audit' 'fault signature found'
if [[ ! -s "$out/final-suite-kernel-faults.log" ]]; then record PASS 'final targeted kernel audit' 'no targeted GPU/NPU fault signatures during final local-model stage'; fi
{
  date --iso-8601=seconds
  cat /proc/swaps
  awk '/^MemAvailable:|^SwapTotal:|^SwapFree:/ {print}' /proc/meminfo
  cat /sys/class/drm/card1/device/mem_info_gtt_used 2>/dev/null | sed 's/^/gtt_used_bytes=/' || true
  cat /sys/class/drm/card1/device/mem_info_vram_used 2>/dev/null | sed 's/^/vram_used_bytes=/' || true
  dpkg-query -W -f='${binary:Package}\t${Version}\n' linux-image-"$(uname -r)" mesa-vulkan-drivers libdrm-amdgpu1 rocm-core hip-runtime-amd xrt-base xrt-npu xrt_plugin-amdxdna 2>&1
} > "$out/platform-after.txt"
printf 'finished=%s\n' "$(date --iso-8601=seconds)" >> "$out/run-metadata.txt"
record BLOCKED 'Current-state recovery archive' 'available CP0 predates Vivado/Vitis installation; its 50 GiB archive plus the 234 GiB Xilinx install tree exceeds the 132 GiB free on the same filesystem'
record DEFERRED 'Off-device/full boot recovery' 'no external backup device is mounted; a current-state local checkpoint and full boot restore are still pending'
if [[ -x /home/shen/tools/Xilinx/2026.1/2026.1/Vitis/bin/vitis-run ]]; then
  vitis_env=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/settings64.sh
  if [[ -r "$vitis_env" ]] && bash -c 'source "$1" >/dev/null 2>&1; vitis-run --version' _ "$vitis_env" >"$out/vitis-run-version.log" 2>&1; then
    record PASS 'Vitis HLS runtime startup' 'vitis-run --version completed with sourced Vitis 2026.1 environment'
  else
    record FAIL 'Vitis HLS runtime startup' 'vitis-run version/startup check failed'
  fi
else
  record FAIL 'Vitis HLS runtime startup' 'installed vitis-run executable is missing'
fi
printf 'Detailed output: %s\n' "$out"
