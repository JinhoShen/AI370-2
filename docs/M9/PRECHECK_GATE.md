# M9 Vivado/Vitis 2026.1 — current gate status

M9.0 Precheck and M9.1 FPGA resource/device/board/platform/license inventory are complete. The execution route is the user-directed isolated Ubuntu 24.04.3 VM, preserving the validated Ubuntu 24.04.4 host and M5 GPU/NPU stack.

M9.2 has not started. The required Ubuntu 24.04.3 ISO is not present on current local/attached storage; only a verified Ubuntu 24.04.1 ISO is available. The 2026.1 installer is present and its full SHA-256 has been verified. Do not substitute 24.04.1 or start a native install on the unsupported host.

The M9 target device/board and applicable license entitlement remain UNKNOWN. No selected FPGA hardware was observed on PCIe; this does not block batch synthesis by itself, but it leaves the intended part and later JTAG path unresolved. The missing guest installation media is the immediate execution gate; do not install Vivado or create the VM before the exact 24.04.3 media and target/component scope are established.

Detailed evidence:

- `docs/M9/M9.0_PRECHECK.md`
- `docs/M9/M9.1_FPGA_INVENTORY.md`

No install, VM creation, package mutation, or FPGA programming has been performed.
