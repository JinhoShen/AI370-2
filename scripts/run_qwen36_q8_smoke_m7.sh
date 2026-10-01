#!/usr/bin/env bash
set -euo pipefail

repo=/home/shen/AI370-2
model=$repo/resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.6-35B-A3B-Q8_0.gguf
backend=${1:?usage: run_qwen36_q8_smoke_m7.sh cpu|vulkan|rocm}
evidence=$repo/docs/M7/evidence/qwen36-35b-a3b-q8
mkdir -p "$evidence"
case "$backend" in
  cpu) bin=$repo/output/M6/build-cpu/bin/llama-cli; device=none; layers=0; memory_limit=39G; min_available=44000000000 ;;
  vulkan) bin=$repo/output/M6/build-vulkan/bin/llama-cli; device=Vulkan0; layers=1; memory_limit=32G; min_available=37000000000 ;;
  rocm) bin=$repo/output/M6/build-hip/bin/llama-cli; device=ROCm0; layers=1; memory_limit=32G; min_available=37000000000 ;;
  *) echo "unknown backend: $backend" >&2; exit 2 ;;
esac
[[ -x "$bin" && -r "$model" ]]
if [[ "$backend" == rocm ]]; then
  [[ -f "$evidence/vulkan-smoke.rc" && $(<"$evidence/vulkan-smoke.rc") == 0 ]] || {
    echo "REFUSED: ROCm inference requires a successful Vulkan smoke first" >&2
    exit 4
  }
fi

if [[ ${2-} != --in-scope ]]; then
  unit="qwen36-q8-${backend}-$(date +%s)"
  exec systemd-run --user --scope --quiet --unit="$unit" \
    -p MemoryMax="$memory_limit" -p MemorySwapMax=0 -p CPUQuota=400% \
    -- "$0" "$backend" --in-scope \
    > "$evidence/$backend-smoke.log" 2>&1
fi

started=$(date --iso-8601=seconds)
mem_before=$(awk '/^MemAvailable:/ {print $2 * 1024}' /proc/meminfo)
if (( mem_before < min_available )); then
  echo "ABORT: MemAvailable=${mem_before}, requires >=${min_available} bytes" >&2
  exit 3
fi
vm_before=$(awk '/^pswp(in|out) / {print $1 "=" $2}' /proc/vmstat | tr '\n' ' ')
cgroup=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
{
  echo "backend=$backend"
  echo "binary=$bin"
  echo "model=$model"
  echo "start=$started"
  echo "memavailable_before_bytes=$mem_before"
  echo "memory.max=$(cat "/sys/fs/cgroup$cgroup/memory.max")"
  echo "memory.swap.max=$(cat "/sys/fs/cgroup$cgroup/memory.swap.max")"
  echo "vmstat_swap_before=$vm_before"
  echo "command=llama-cli -m <model> -c 64 -b 8 -ub 4 -t 4 -tb 4 -n 4 --reasoning off --device $device --gpu-layers $layers -p 'Reply with exactly READY.' --single-turn --no-display-prompt --simple-io --verbose"
  echo
} > "$evidence/$backend-run-metadata.txt"

set +e
/usr/bin/time -v /usr/bin/timeout --signal=TERM --kill-after=5s 600s \
  "$bin" --model "$model" --ctx-size 64 --batch-size 8 --ubatch-size 4 \
  --threads 4 --threads-batch 4 --n-predict 4 --reasoning off \
  --device "$device" --gpu-layers "$layers" \
  --prompt 'Reply with exactly READY.' --single-turn --no-display-prompt --simple-io --verbose \
  >> "$evidence/$backend-smoke.log" 2>&1
run_rc=$?
set -e
finished=$(date --iso-8601=seconds)
mem_after=$(awk '/^MemAvailable:/ {print $2 * 1024}' /proc/meminfo)
vm_after=$(awk '/^pswp(in|out) / {print $1 "=" $2}' /proc/vmstat | tr '\n' ' ')
{
  echo "finish=$finished"
  echo "exit_code=$run_rc"
  echo "memavailable_after_bytes=$mem_after"
  echo "vmstat_swap_after=$vm_after"
  echo "memory.peak=$(cat "/sys/fs/cgroup$cgroup/memory.peak")"
  echo "memory.swap.peak=$(cat "/sys/fs/cgroup$cgroup/memory.swap.peak")"
} >> "$evidence/$backend-run-metadata.txt"
echo "$run_rc" > "$evidence/$backend-smoke.rc"
journalctl -k --since "$started" --until "$finished" --no-pager > "$evidence/kernel-$backend.log" 2>&1
exit "$run_rc"
