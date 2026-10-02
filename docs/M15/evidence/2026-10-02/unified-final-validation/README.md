# M15 unified pre-final validation evidence

Captured on 2026-10-02. `status-final.tsv` is the reconciled verdict table; `status-initial.tsv` preserves the first run's system-Python metadata parser errors. Those parser checks were rerun using the already-installed NumPy-enabled venv and all seven GGUF/sidecar files parsed. `models/sha256.txt`, `file-inventory.tsv`, and `model-summary.tsv` provide exact local integrity and metadata. Model inference logs are limited to the M7-selected IQ2 model at context 32, at most four output tokens, and one offloaded GPU layer. Qwen3.8 models were inventoried only.

`workstation/` retains HIP, Vulkan, strict NPU CNN/XRT, toolchain/Ross readiness and kernel-audit evidence. The FPGA was not programmed in M15; prior M11 DDR and M12 JTAG-to-AXI physical evidence remains separately recorded. `pre-vivado-checkpoint-restore.txt` is a successful restore of the earlier CP0 baseline only; that archive predates Vivado/Vitis. No current-state M15 checkpoint was made because the 250,470,367,232-byte (233.2 GiB) Xilinx tree exceeds the latest 156,526,895,104-byte (145.8 GiB) free space, and no external target was mounted.

The broad temporary `NOPASSWD: ALL` sudo rule was removed after workload tests. A `visudo -c` check remains deferred because no noninteractive root authorization remains after cleanup; no authorization bypass was attempted.
