#!/usr/bin/env bash
set -euo pipefail
export XILINX_XRT=/opt/xilinx/xrt
export LD_LIBRARY_PATH=/opt/ai370/npu/xrt21-shim/lib:/opt/xilinx/xrt/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export PATH=/opt/xilinx/xrt/bin:$PATH
exec "$@"
