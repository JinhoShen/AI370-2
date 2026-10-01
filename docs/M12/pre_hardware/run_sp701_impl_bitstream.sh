#!/usr/bin/env bash
set -euo pipefail
VIVADO_ROOT=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
set +u
source "$VIVADO_ROOT/settings64.sh"
set -u
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "$VIVADO_ROOT/bin/vivado" -mode batch \
  -source "$SCRIPT_DIR/sp701_impl_bitstream.tcl" \
  -log "$SCRIPT_DIR/sp701_impl_bitstream.log" \
  -journal "$SCRIPT_DIR/sp701_impl_bitstream.jou"
