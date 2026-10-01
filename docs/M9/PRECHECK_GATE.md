# M9 Vivado/Vitis 2026.1 — PRECHECK / OS decision gate

日期：2026-10-01。狀態：GATE — 尚未安裝或解包 2026.1。

## Current machine and local resources

- Host: Ubuntu 24.04.4 LTS, kernel 6.17.0-14-generic, Ryzen AI 9 HX 370, 24 logical CPUs, 46 GiB visible RAM; 43 GiB was available at precheck. `/dev/kvm` exists and CPU exposes SVM virtualization.
- Filesystem containing repository/resources: 619 GiB free at precheck.
- Local installer: `resources/Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar`, 105,522,216,960 bytes (about 98.3 GiB), not extracted. `docs/SHA256SUMS.local` records expected SHA-256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`; the release asset remains in its existing resource location.
- The only locally inventoried Ubuntu ISO is `resources/Agent_Tools_Docs/01_OS/Ubuntu/ubuntu-24.04.1-desktop-amd64.iso`; there is no local 24.04.3 ISO. No VM was created and no installer component was selected.
- An external Transcend USB is now mounted at `/media/shen/Transcend` as exFAT. It contains `FPGAs_AdaptiveSoCs_Unified_SDI_2025.2_1114_2157_1.tar` (102,739,568,640 bytes; 2025.2) and Ubuntu 24.04.4 / 24.04.1 ISOs; it has about 7.6 GiB free. The 2025.2 archive's contents/checksum were not read or verified and it remains untouched. The USB does not contain the requested 24.04.3 ISO.
- No M9 device/board subset, license/entitlement, or intended Vivado-only versus Vitis Embedded versus Vitis Acceleration component set has been recorded.

## Existing compatibility evidence and boundary

`docs/MASTER_PLAN_REVIEW.md` records the completed release compatibility review and source citations: the 2026.1 support table marks Ubuntu 24.04.4 unsupported and 24.04.3 supported. A Vitis release document lists Kernel 6.17.0-14 in a tested configuration, but the review also records the applicable HWE caveat; a matching kernel string does not override the OS support entry. The host remains Ubuntu 24.04.4 because changing the AI/NPU host OS or kernel would break the validated M5/M6/M7 baseline.

The review estimates approximately 98.3 GiB to stage/extract the installer, 35 GB for Vitis Embedded or 200 GB for a full Vitis install depending on selected components. This machine has 619 GiB free for one selected installation or a VM disk plus extraction; capacity does not choose the supported-OS route. Vitis Embedded/HLS memory is listed as 32 GB minimum / 64 GB recommended; Vitis Acceleration lists 64 GB minimum / 80 GB recommended. Current visible RAM is 46 GiB, so a 32 GiB embedded-tool guest would be near the minimum and acceleration cannot meet the listed minimum in a VM on this host.

No new compatibility research, OS mutation, installer launch, VM creation, file copy, or license/device assumption was made at this gate. The external 2025.2 archive is an additional inventory item, not authorization to replace the planned 2026.1 release.

## Decision required before M9

Choose the supported execution environment and the desired 2026.1 scope before any installer step:

1. **Supported guest route (recommended for preserving the host):** provision an isolated Ubuntu 24.04.3 VM, which first requires obtaining that exact ISO and sizing a guest. Feasible candidate for Vivado / Embedded / HLS only; validate the 32 GiB minimum with the 46 GiB host and identify USB/JTAG/device passthrough needs. Vitis Acceleration cannot meet its stated 64 GiB RAM minimum on the current host.
2. **Native exception route:** explicitly accept Ubuntu 24.04.4 as an unsupported-OS local experiment for a selected Vivado/Vitis 2026.1 component set. Results must be labeled local-only, not officially supported. Keep changes isolated, record installer package diff and rollback, and do not replace Kernel/ROCm/Mesa/XRT/amdxdna/firmware without a separate gate.
3. **Defer M9:** leave the installer untouched until device subset, license entitlement, memory plan, and supported OS environment are settled.

After the environment choice, remaining required inputs are the target device/board subset, license availability/type, and Vivado-only / Vitis Embedded / Vitis Acceleration scope. No hardware board programming is part of M9 synthesis verification.
