#!/usr/bin/env bash
set -euo pipefail

VITIS_EMBED_ROOT=/home/shen/tools/Xilinx/vitis-embedded-2026.1/2026.1/Vitis
VIVADO_ROOT=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
source "$VITIS_EMBED_ROOT/settings64.sh"
export XILINX_VIVADO="$VIVADO_ROOT"
export RDI_DATADIR="$VITIS_EMBED_ROOT/data:$VIVADO_ROOT/data:$VIVADO_ROOT/../SharedData/data"
export TCL_LIBRARY="$VITIS_EMBED_ROOT/tps/tcl/tcl8.6"
export LD_LIBRARY_PATH="$VITIS_EMBED_ROOT/lib/lnx64.o:$VITIS_EMBED_ROOT/lib/lnx64.o/Ubuntu/24:${LD_LIBRARY_PATH-}"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$VITIS_EMBED_ROOT"
exec "$VITIS_EMBED_ROOT/bin/vitis-run" --mode hls --tcl \
  --input_file "$SCRIPT_DIR/hls_smoke.tcl" \
  --work_dir "$SCRIPT_DIR/work/hls-cli"
