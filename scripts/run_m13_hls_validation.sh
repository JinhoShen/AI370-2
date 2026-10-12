#!/usr/bin/env bash
source /home/shen/tools/Xilinx/2026.1/2026.1/Vitis/settings64.sh
mkdir -p runs/hls-csim runs/hls-csynth

set +e
vitis-run --mode hls --csim --config hls_config.cfg --work_dir runs/hls-csim >runs/hls-csim.log 2>&1
csim_rc=$?
cat runs/hls-csim.log
if [ "$csim_rc" -ne 0 ] || ! grep -Fq 'PASS: 4 HLS C simulation vectors matched' runs/hls-csim.log; then
  echo "M13_HLS_CSIM_FAIL exit=$csim_rc"
  exit 20
fi
echo M13_HLS_CSIM_PASS

v++ -c --mode hls --part xc7s100fgga676-2 --config hls_config.cfg --work_dir runs/hls-csynth >runs/hls-csynth.log 2>&1
csynth_rc=$?
cat runs/hls-csynth.log
if [ "$csynth_rc" -ne 0 ] || ! find runs/hls-csynth -type f -name '*csynth.rpt' -print -quit | grep -q .; then
  echo "M13_HLS_CSYNTH_FAIL exit=$csynth_rc"
  exit 21
fi
echo M13_HLS_CSYNTH_PASS
echo M13_HLS_CSIM_PASS
echo M13_HLS_CSYNTH_PASS
