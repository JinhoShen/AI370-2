#!/usr/bin/env bash
set -u
vivado_root=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
expected_tb=b73d5d68ef19be5723c2e7ee43441e61001fb4a3426596ff3608a9f093834280
actual_tb=$(sha256sum "$PWD/sim/tb_local_model_axi_lite.sv" | cut -d' ' -f1)
if [[ "$actual_tb" != "$expected_tb" ]]; then echo "GUARD_FAIL testbench changed"; exit 90; fi
attempt_file="$PWD/.attempt-count"
count=0
[[ -f "$attempt_file" ]] && read -r count < "$attempt_file"
if (( count >= 3 )); then echo "GUARD_FAIL maximum 3 total validation attempts reached"; exit 91; fi
count=$((count+1)); printf '%s\n' "$count" > "$attempt_file"
run_dir="$PWD/runs/attempt-$count"
mkdir -p "$run_dir"
cd "$run_dir"
set +u
source "$vivado_root/settings64.sh"
set -u
if ! xvlog --sv -work xil_defaultlib "$PWD/../../rtl/local_model_axi_lite.v" "$PWD/../../rtl/axi_result_datapath.v" "$PWD/../../sim/tb_local_model_axi_lite.sv" > xvlog.log 2>&1; then
  # Workspace-relative source paths keep every source under the bounded workspace bind.
  echo "XSim compile failed (attempt=$count)"; tail -n 30 xvlog.log; exit 1
fi
if ! xelab xil_defaultlib.tb_local_model_axi_lite -s "tb_attempt_$count" > xelab.log 2>&1; then
  echo "XSim elaboration failed (attempt=$count)"; tail -n 30 xelab.log; exit 1
fi
if ! xsim "tb_attempt_$count" -testplusarg TEST_NEW_MODE -runall > xsim.log 2>&1; then
  echo "XSim simulation failed (attempt=$count)"; tail -n 40 xsim.log; exit 1
fi
if ! grep -q '^TEST_PASS multi_file_mode=1' xsim.log; then echo "XSim PASS marker missing (attempt=$count)"; tail -n 40 xsim.log; exit 2; fi
echo "TEST_PASS multi_file_mode=1 attempt=$count"
tail -n 8 xsim.log
