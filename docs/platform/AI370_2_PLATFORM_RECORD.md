# AI370-2 Platform Record

**採集日期：** 2026-10-01（Asia/Taipei）
**方法：** 本文件的 ACTUAL 系統欄位以本次主機唯讀命令重新採集；工具測試狀態引用帶日期的 M9/M10 evidence。此記錄是 2026.1 安裝與驗證快照，不代表未來版本不變。

## ACTUAL platform

| 項目 | 目前實際值 | 證據／辨識方式 |
|---|---|---|
| Machine | Micro Computer (HK) Tech Limited, AI Series；hostname `shen-AI-Series` | 本次 `hostnamectl`, DMI |
| CPU | AMD Ryzen AI 9 HX 370 w/ Radeon 890M；12 cores / 24 threads | 本次 `/proc/cpuinfo`, `lscpu` |
| RAM | 50,103,095,296 bytes（約 46.65 GiB） | 本次 `/proc/meminfo`, DMI |
| OS | Ubuntu 24.04.4 LTS (Noble), x86_64 | 本次 `/etc/os-release`, `dpkg` |
| Kernel | `6.17.0-14-generic` | 本次 `uname -r` |
| BIOS | Version `1.06`, date `2026-01-05` | 本次 DMI/`dmidecode` |
| Radeon GPU | AMD Radeon 890M Graphics, PCI `1002:150e`, amdgpu; ROCm target `gfx1150` | 本次 PCI/Vulkan/ROCm inventory |
| Mesa / RADV | Mesa Vulkan package `25.2.8-0ubuntu0.24.04.1`; RADV reports `25.2.8`, device `RADV GFX1150` | 本次 `dpkg-query`, `vulkaninfo --summary` |
| libdrm | `libdrm2` and `libdrm-amdgpu1` `2.4.125-1ubuntu0.1~24.04.1` | 本次 `dpkg-query` |
| ROCm / HIP | `rocm-core 7.2.1.70201-81~24.04`; `hip-runtime-amd 7.2.53211.70201-81~24.04` | 本次 `dpkg-query` |
| XDNA2 NPU | Strix NPU, PCI `0000:c6:00.1`, enumerated by XRT-SMI | 本次 `xrt-smi examine` |
| System XRT | `xrt-base 2.21.75`, `xrt-npu 2.21.75`, `xrt_plugin-amdxdna 2.21` | 本次 `dpkg-query` |
| amdxdna DKMS | Source/version `2.21.260102.53.release`; current-kernel installed module `/lib/modules/6.17.0-14-generic/updates/dkms/amdxdna.ko.zst`; source commit `6f881ad230142b707ca8ce5b33fca426a926c551` | 本次 `dkms status`, `modinfo` |
| NPU firmware | `1.1.2.64` | 本次 `xrt-smi examine` |
| Root filesystem | `/dev/nvme0n1p2`, ext4, 982,240,026,624 bytes total; 711,288,266,752 used; 220,981,243,904 available at capture | 本次 `findmnt`, `df -B1` |
| Unified Xilinx tree | `/home/shen/tools/Xilinx/2026.1/2026.1/{Vivado,Vitis}` | 本次 filesystem inspection; installer registry under `/home/shen/tools/Xilinx/2026.1/.xinstall/2026.1` |
| Vitis Embedded tree | `/home/shen/tools/Xilinx/vitis-embedded-2026.1/2026.1/Vitis` | 本次 filesystem inspection |

The memory and filesystem free-space values are point-in-time observations. Do not treat them as guaranteed capacity. The installed 46.65 GiB RAM is below UG1742's 64 GB minimum for Acceleration Development & Deployment; the local CLI/device/platform checks do not establish that full acceleration workloads meet that requirement.

## Xilinx 2026.1 installation and recognition state

| Area | State | Actual evidence and boundary |
|---|---|---|
| Vivado 2026.1 | INSTALLED / VERIFIED | Version/build, active license, batch Tcl, board/part lookup and SP701 RTL synthesis passed; see [`docs/M9/LICENSE_UNLOCKED_VALIDATION.md`](../M9/LICENSE_UNLOCKED_VALIDATION.md). |
| Vitis Unified 2026.1 | INSTALLED / VERIFIED | Startup/version, `v++ --version`, HLS runner and platform parser checks passed; see [`docs/M10/RESULT.md`](../M10/RESULT.md). |
| Vitis Embedded 2026.1 | INSTALLED / VERIFIED | Separate installation path above; startup/version logs are in M9 evidence. |
| Vitis HLS 2026.1 | INSTALLED / VERIFIED | SP701 C synthesis passed with report and generated RTL; M9/M10 evidence. |
| Vitis Acceleration components | INSTALLED / partial VERIFIED | Alveo/edge acceleration device module Add completed; CLI/version and eight embedded platform definitions parsed. Physical accelerator platform/runtime, hardware kernel implementation and execution are DEFERRED. |
| FPGA device families | INSTALLED | Installer records show initial Artix-7, Kria, Zynq UltraScale+ MPSoC; maintenance Add later selected only Spartan-7. Acceleration Add selected Alveo/edge and Versal acceleration device modules. Refer to installer summaries under M9 evidence. |
| Spartan-7 | INSTALLED / VERIFIED | Added through maintenance Add; Vivado resolves `xc7s100fgga676-2`, and synthesis/HLS synthesis passed. |
| SP701 board files | INSTALLED / VERIFIED recognition | Xilinx SP701 board parts `xilinx.com:sp701:part0:1.0` recognized; board XML source/install SHA-256 match is in M9 validation. JTAG and physical operation are DEFERRED. |
| Digilent board files | INSTALLED / VERIFIED recognition | Vivado recognizes Digilent Arty A7-35 `digilentinc.com:arty-a7-35:part0:1.0`, part `xc7a35ticsg324-1L`; no physical Arty operation claimed. |
| Xilinx Board Store | INSTALLED / VERIFIED for SP701 | Local store content was added; SP701 board XML source/install SHA-256 match recorded in M9 validation. Recognition is scoped to queried/tested definitions. |
| Embedded base platforms | INSTALLED / VERIFIED metadata parse | Eight `.xpfm` files listed and individually parsed by `platforminfo`: `kv260_base`, `vck190_base`, `vek280_base`, `vek385_base`, `vrk160_base`, `xilinx_vck190_base_202610_1`, `xilinx_vck190_base_dfx_202610_1`, `xilinx_vek280_base_202610_1`. This does not prove platform builds or hardware execution. |
| System XRT vs Vitis bundled XRT | Coexistence observed; FPGA compatibility UNKNOWN | System Ryzen AI stack remains XRT 2.21.75. Vitis bundled `xclbinutil` reports XRT metadata 2.19.0; with `XILINX_XRT=/opt/xilinx/xrt`, wrapper selects system XRT 2.21.75 utility. Acceleration Add did not replace system XRT. No FPGA accelerator card was enumerated, so FPGA card runtime compatibility is not verified. |

## Verified regressions and remaining limits

- HIP regression: PASS, 1,024 Radeon 890M / `gfx1150` results.
- Vulkan baseline regression: PASS, 1,024 RADV GFX1150 shader results with CPU fallback forbidden.
- XRT/NPU enumeration: PASS, Strix NPU, system XRT 2.21.75 and firmware 1.1.2.64.
- M5 CNN regression: PASS, 10 iterations; CPU fallback disabled; all profiled nodes used VitisAI; NPU counter increased; maximum CPU-reference absolute error 0.0. Exact counter and run log are in M9 evidence.
- SP701 JTAG target: DEFERRED; Hardware Manager found no target and the captured USB inventory contained no Xilinx/Digilent cable.
- Bitstream/programming and FPGA hardware execution: DEFERRED; none is claimed.
- FPGA XRT C++ host API: DEFERRED; M9 record reports XRT C++ development headers unavailable in the configured host package metadata.
- Ubuntu 24.04.4 native install and passing checks are actual local results. They do not establish official AMD support; current UG973 OS matrix stops at Ubuntu 24.04.3. See the separate official-vs-actual comparison in [`XILINX_2026_1_INSTALLATION_RECORD.md`](XILINX_2026_1_INSTALLATION_RECORD.md).
- Qwen3.6-35B-A3B Q8_0 Vulkan failure is a distinct M7.1 model/backend issue, recorded in [`docs/M7/QWEN36_Q8_SMOKE.md`](../M7/QWEN36_Q8_SMOKE.md); it was not the M9 Vulkan baseline regression and was not rerun as part of M9.

## M9 to M10 decision and validation history

Dates below are from Git commit metadata in Asia/Taipei; per-test outcomes and the original failure records remain in their cited documents and logs.

| Date / commit | Recorded decision or result |
|---|---|
| 2026-10-01 10:35, `68def7a` | Initial M9 gate retained a VM recommendation because 24.04.4 compatibility had not been confirmed; M9.0/M9.1 inventory and earlier records remain unchanged. |
| 2026-10-01 12:10, `6470ac3` | M9.0 precheck and FPGA resources/device/board/platform/license inventory committed. |
| 2026-10-01 12:37, `3ac9936` | User-selected native Ubuntu 24.04.4 route recorded; prior VM recommendation preserved; PRE-M9 native recovery checkpoint, baseline and APT simulations documented. |
| 2026-10-01 14:20, `6cdc0c4` | Native core Vivado/Vitis/Vitis Embedded/HLS installation completed from local verified installer; initial Vivado/HLS synthesis was BLOCKED by missing active license. |
| 2026-10-01 16:17, `f112bc3` | Acceleration device components added; CLI, XRT selection behavior and platform resources inventoried; system XRT left intact. |
| 2026-10-01 18:17, `a2c335b` | Separate Qwen Q8 low-load smoke evidence committed; Vulkan failure recorded as M7 issue, outside M9 PASS scope. |
| 2026-10-01 19:01, `0b8c922` | License became available; prior BLOCKED attempts preserved. Vivado/HLS synthesis passed. Initial absence of Spartan-7 support was fixed by adding only Spartan-7; SP701 and Arty recognition, Vivado synthesis/utilization, HLS synthesis and HIP/Vulkan/XRT/NPU/CNN regressions passed. M9 PASS and FPGA TOOLCHAIN WORKING STATE recorded. |
| 2026-10-01 19:03, `1d5f6fa` | M10 Vitis `v++`, SP701 HLS and individual parse of all eight embedded platforms passed. |

The commit sequence preserves the distinction between former VM planning, user-authorized native validation, intermediate license failure, and later PASS. See [`docs/M9/NATIVE_INSTALL_DECISION.md`](../M9/NATIVE_INSTALL_DECISION.md), [`docs/M9/NATIVE_INSTALL_RESULT.md`](../M9/NATIVE_INSTALL_RESULT.md), [`docs/M9/ACCELERATION_INSTALL_RESULT.md`](../M9/ACCELERATION_INSTALL_RESULT.md), [`docs/M9/LICENSE_UNLOCKED_VALIDATION.md`](../M9/LICENSE_UNLOCKED_VALIDATION.md), and [`docs/M10/RESULT.md`](../M10/RESULT.md). No original failure history is rewritten by this record.

## Rebuild / recovery sequence

1. Create and verify a fresh recovery checkpoint; record the exact installer and resource hashes.
2. Capture the protected host baseline: kernel, Mesa/RADV, libdrm, ROCm/HIP, system XRT, amdxdna DKMS and NPU firmware. Compare before/after; stop before any protected-stack version change.
3. Use the approved AMD/Xilinx 2026.1 installer and documented component selection. Do not treat this historical manual session as a finished automated installer.
4. Add only required device modules, then board definitions/platform resources; prove recognition with Vivado/Vitis queries.
5. Configure a valid license without putting license content, key, or hash into Git.
6. Run Vivado batch/Tcl, RTL synthesis/report and Vitis HLS synthesis/report; retain exit status and logs.
7. Run HIP, Vulkan baseline, XRT/NPU enumeration and M5 CNN regression; permit PASS only with confirmed backend/device and no fallback.
8. Test physical JTAG/programming only when the exact board/cable/target is present. Record hardware behavior separately from software toolchain validation.

This ordering is a rebuild guide, not an assertion that prior exploratory actions have been encapsulated in a script.
