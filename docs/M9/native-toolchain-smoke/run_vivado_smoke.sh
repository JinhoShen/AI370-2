#!/usr/bin/env bash
set -euo pipefail

VIVADO_ROOT=/home/shen/tools/Xilinx/2026.1/2026.1/Vivado
set +u # Vendor settings reference optional environment variables without defaults.
source "$VIVADO_ROOT/settings64.sh"
set -u
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "$VIVADO_ROOT/bin/vivado" -mode batch \
  -source "$SCRIPT_DIR/vivado_smoke.tcl" \
  -log "$SCRIPT_DIR/vivado-smoke.log" \
  -journal "$SCRIPT_DIR/vivado-smoke.jou"
