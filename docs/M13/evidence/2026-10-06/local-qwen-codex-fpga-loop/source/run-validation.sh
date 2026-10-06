#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tag="${RUN_TAG:-attempt}"
out="$root/build/$tag"
mkdir -p "$out"
source /home/shen/tools/Xilinx/2026.1/2026.1/Vivado/settings64.sh
if ! xvlog --sv -work xil_defaultlib "$root/rtl/local_model_axi_lite.v" "$root/sim/tb_local_model_axi_lite.sv" >"$out/xvlog.log" 2>&1; then
  echo "XVLOG=FAIL run=$tag"
  tail -n 40 "$out/xvlog.log"
  exit 11
fi
if ! xelab xil_defaultlib.tb_local_model_axi_lite -s "tb_$tag" >"$out/xelab.log" 2>&1; then
  echo "XELAB=FAIL run=$tag"
  tail -n 60 "$out/xelab.log"
  exit 12
fi
if ! xsim "tb_$tag" -testplusarg TEST_NEW_MODE -runall >"$out/xsim.log" 2>&1; then
  echo "XSIM=FAIL run=$tag"
  tail -n 80 "$out/xsim.log"
  exit 13
fi
if ! RUN_TAG="$tag" vivado -mode batch -source "$root/scripts/synth.tcl" -log "$out/vivado.log" -journal "$out/vivado.jou" >"$out/vivado.stdout.log" 2>&1; then
  echo "VIVADO_SYNTH=FAIL run=$tag"
  tail -n 80 "$out/vivado.stdout.log"
  tail -n 80 "$out/vivado.log" 2>/dev/null || true
  exit 14
fi
if ! rg -q "TEST_PASS baseline_and_selected_mode=1" "$out/xsim.log"; then
  echo "XSIM_PASS_MARKER=FAIL run=$tag"
  tail -n 80 "$out/xsim.log"
  exit 15
fi
if ! rg -q "CODEX_QWEN_VIVADO_SYNTHESIS=PASS" "$out/vivado.log"; then
  echo "VIVADO_PASS_MARKER=FAIL run=$tag"
  tail -n 80 "$out/vivado.log"
  exit 16
fi
printf 'VALIDATION_PASS run=%s xsim=PASS vivado_synthesis=PASS\n' "$tag"
