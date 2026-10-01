#!/usr/bin/env bash
set -u
project=/home/shen/AI370-2
cd "$project"
out="$project/output/M14"
mkdir -p "$out"
started=$(date --iso-8601=seconds)
fail=0
deferred=0
pass() { printf 'PASS %s\n' "$*"; }
fail_item() { printf 'FAIL %s\n' "$*"; fail=1; }
defer() { printf 'DEFERRED %s\n' "$*"; deferred=1; }
printf 'M14_VERIFIER_START=%s\n' "$started"
printf 'KERNEL=%s\n' "$(uname -r)"
printf 'OS=%s\n' "$(. /etc/os-release; printf '%s %s' "$ID" "$VERSION_ID")"
printf '\n[protected-stack]\n'
for pkg in rocm-core hip-runtime-amd xrt-base xrt-npu xrt_plugin-amdxdna; do
  if dpkg-query -W -f='${Status} ${Version}\n' "$pkg" 2>/dev/null | rg -q '^install ok installed'; then
    dpkg-query -W -f="$pkg='\${Version}'\\n" "$pkg"
  else
    fail_item "$pkg not installed"
  fi
done
mod=$(modinfo -n amdxdna 2>/dev/null || true)
ver=$(cat /sys/module/amdxdna/version 2>/dev/null || true)
[[ "$mod" == */updates/dkms/* ]] && pass "amdxdna DKMS path" || fail_item "amdxdna DKMS path"
[[ "$ver" == 2.21.260102.53.release* ]] && pass "amdxdna version $ver" || fail_item "amdxdna version '$ver'"
printf '\n[gpu]\n'
if timeout 30 output/M3/hip-compute >"$out/hip.log" 2>&1 && rg -q 'PASS: 1024' "$out/hip.log"; then pass 'HIP gfx1150'; else fail_item 'HIP'; fi
if timeout 20 output/M4/build/vulkan-compute output/M4/build/verify.spv >"$out/vulkan.log" 2>&1 && rg -q 'PASS: 1024' "$out/vulkan.log"; then pass 'Vulkan RADV'; else fail_item 'Vulkan'; fi
printf '\n[npu]\n'
if bash scripts/npu21.sh /opt/xilinx/xrt/bin/unwrapped/xrt-smi examine -r all >"$out/xrt.log" 2>&1 && rg -q 'NPU Strix' "$out/xrt.log" && rg -q 'XRT' "$out/xrt.log"; then pass 'XRT/NPU enumeration'; else fail_item 'XRT/NPU enumeration'; fi
if NPU_OUTPUT_DIR="$out/npu" NPU_RESULT_FILE="$out/npu-result.json" bash scripts/ryzenai21.sh timeout 180 .venvs/npu21/bin/python verify/npu_cnn.py output/M5/quicktest/quicktest/test_model.onnx >"$out/npu.log" 2>&1 && test -s "$out/npu-result.json"; then
  python3 - "$out/npu-result.json" <<'PY'
import json, sys
r=json.load(open(sys.argv[1]))
assert r.get('status') == 'PASS'
assert r.get('cpu_fallback_disabled') is True
assert r.get('profile_node_providers') == ['VitisAIExecutionProvider']
assert r.get('npu_hardware_time_delta_ns', 0) > 0
assert max(r.get('max_abs_errors', [1])) == 0.0
PY
  [ $? -eq 0 ] && pass 'NPU strict no-fallback CNN' || fail_item 'NPU result checks'
else
  fail_item 'NPU strict no-fallback CNN'
fi
printf '\n[fpga-software]\n'
viv=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado
vpp=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/bin/v++
pi=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis/bin/platforminfo
"$viv" -version 2>"$out/vivado-version.log" | head -1 | rg -q 'v2026.1' && pass 'Vivado 2026.1' || fail_item 'Vivado version'
"$vpp" --version >"$out/vpp-version.log" 2>&1 && rg -q 'v2026.1' "$out/vpp-version.log" && pass 'v++ 2026.1' || fail_item 'v++ version'
"$pi" --version >"$out/platforminfo-version.log" 2>&1 && rg -q 'v2026.1' "$out/platforminfo-version.log" && pass 'platforminfo 2026.1' || fail_item 'platforminfo version'
test -s docs/M9/evidence/license-unlocked-2026.1/synthesis/hls-sp701-csynth.rpt && pass 'HLS SP701 report' || fail_item 'HLS report'
test -s output/M12/pre-hardware/post_route.dcp && pass 'SP701 post-route DCP' || fail_item 'SP701 post-route DCP'
test -s output/M12/pre-hardware/utilization_implemented.rpt && pass 'SP701 utilization report' || fail_item 'SP701 utilization report'
test -s output/M12/pre-hardware/timing_summary.rpt && defer 'SP701 timing report is unconstrained' || fail_item 'SP701 timing report missing'
test -s output/M12/pre-hardware/m12_sp701.bit && pass 'SP701 bitstream' || defer 'SP701 bitstream blocked by board constraints'
printf '\n[local-llm]\n'
if test -x output/M6/build-cpu/bin/llama-cli || test -x output/M6/build-cpu/bin/llama-gemma3-cli; then
  test -f resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.6-35B-A3B-Q8_0.gguf && defer 'Local LLM readiness only; regression not run in M14' || defer 'Local LLM model resource unavailable'
else
  defer 'llama.cpp CPU binary not found'
fi
printf '\n[ross]\n'
defer 'Ross not installed; AMD credential download gate remains open'
printf '\n[kernel-audit]\n'
journalctl -k --since "$started" --no-pager 2>/dev/null | rg -i 'page fault|ttm|soft lockup|gpu reset|ring timeout|amdgpu.*error|amdxdna.*error' >"$out/kernel-errors.log" || true
if test ! -s "$out/kernel-errors.log"; then pass 'No targeted kernel errors during verifier'; else fail_item 'Targeted kernel errors recorded'; fi
printf '\nM14_VERIFIER_END=%s\n' "$(date --iso-8601=seconds)"
printf 'M14_SUMMARY fail=%s deferred=%s\n' "$fail" "$deferred"
exit "$fail"
