#!/usr/bin/env bash
set -euo pipefail
project=/home/shen/AI370-2
environment=$project/.venvs/npu21
site=$environment/lib/python3.12/site-packages
export RYZEN_AI_INSTALLATION_PATH=$environment
export XILINX_VITIS=$site
export XILINX_VITIS_AIETOOLS=$site
export LD_LIBRARY_PATH=$site/flexml/flexml_extras/lib:$site/onnxruntime/capi:$site/voe/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
exec bash "$project/scripts/npu21.sh" "$@"
