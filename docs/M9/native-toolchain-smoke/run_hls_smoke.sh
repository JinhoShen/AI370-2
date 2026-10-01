#!/usr/bin/env bash
set -euo pipefail

VITIS_ROOT=/home/shen/tools/Xilinx/2026.1/2026.1/Vitis
VIVADO_ROOT=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
set +u # Vendor settings reference optional environment variables without defaults.
source "$VITIS_ROOT/settings64.sh"
set -u
export XILINX_VIVADO="$VIVADO_ROOT"
export RDI_DATADIR="$VITIS_ROOT/data:$VIVADO_ROOT/data:$VIVADO_ROOT/../SharedData/data"
export TCL_LIBRARY="$VITIS_ROOT/tps/tcl/tcl8.6"
export LD_LIBRARY_PATH="$VITIS_ROOT/lib/lnx64.o:$VITIS_ROOT/lib/lnx64.o/Ubuntu/24:${LD_LIBRARY_PATH-}"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$VITIS_ROOT"
exec "$VITIS_ROOT/bin/vitis-run" --mode hls --tcl \
  --input_file "$SCRIPT_DIR/hls_smoke.tcl" \
  --work_dir "$SCRIPT_DIR/work/hls-cli"
