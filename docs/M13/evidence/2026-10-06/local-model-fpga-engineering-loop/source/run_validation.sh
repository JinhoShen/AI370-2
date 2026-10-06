#!/usr/bin/env bash
set -u
root=$(cd -- "$(dirname -- "$0")" && pwd)
vivado_root=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
expected_tb=55ccf9c733802b60af8d8f6e94c0aaf9d8d67ddedbf4ae7b0748076e050759f1
actual_tb=$(sha256sum "$root/sim/tb_local_model_axi_lite.sv" | cut -d' ' -f1)
if [[ "$actual_tb" != "$expected_tb" ]]; then echo "GUARD_FAIL testbench changed"; exit 90; fi
attempt_file="$root/.attempt-count"
count=0
[[ -f "$attempt_file" ]] && read -r count < "$attempt_file"
if (( count >= 3 )); then echo "GUARD_FAIL maximum 3 total validation attempts reached"; exit 91; fi
count=$((count+1)); printf '%s\n' "$count" > "$attempt_file"
run_dir="$root/runs/attempt-$count"
mkdir -p "$run_dir"
cd "$run_dir"
set +u
source "$vivado_root/settings64.sh"
set -u
if ! xvlog --sv -work xil_defaultlib "$root/rtl/local_model_axi_lite.v" "$root/sim/tb_local_model_axi_lite.sv" > xvlog.log 2>&1; then
  echo "XSim compile failed (attempt=$count)"; tail -n 30 xvlog.log; exit 1
fi
if ! xelab xil_defaultlib.tb_local_model_axi_lite -s "tb_attempt_$count" > xelab.log 2>&1; then
  echo "XSim elaboration failed (attempt=$count)"; tail -n 30 xelab.log; exit 1
fi
if ! xsim "tb_attempt_$count" -testplusarg TEST_NEW_MODE -runall > xsim.log 2>&1; then
  echo "XSim simulation failed (attempt=$count)"; tail -n 40 xsim.log; exit 1
fi
if ! grep -q '^TEST_PASS baseline_and_selected_mode=1' xsim.log; then echo "XSim PASS marker missing (attempt=$count)"; tail -n 40 xsim.log; exit 2; fi
echo "TEST_PASS baseline_and_selected_mode=1 attempt=$count"
tail -n 8 xsim.log
