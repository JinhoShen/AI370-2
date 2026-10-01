# M9 continuation — Vitis Acceleration components and local resources

Date: 2026-10-01 (Asia/Taipei). This is an addendum to [NATIVE_INSTALL_RESULT.md](NATIVE_INSTALL_RESULT.md); it preserves the original installation and license-gate record. Host remains Ubuntu 24.04.4 LTS. Native installation is local validation, not a claim of official OS support.

## Component inventory and outcome

| Component | Status | Evidence / limit |
|---|---|---|
| Vivado 2026.1 | INSTALLED, version VERIFIED | Tool version/startup evidence remains in `evidence/native-2026.1/logs/`. Batch Tcl and RTL synthesis remain BLOCKED by missing license. |
| Vitis Unified 2026.1 | INSTALLED, version VERIFIED | `evidence/acceleration-2026.1/logs/tool-versions.log`; original tree retained. |
| Vitis Embedded 2026.1 | INSTALLED, startup previously VERIFIED | Separate prefix `/home/shen/tools/Xilinx/vitis-embedded-2026.1`; no reinstall in this continuation. |
| Vitis HLS 2026.1 | INSTALLED, version VERIFIED | `evidence/acceleration-2026.1/logs/tool-versions.log`; HLS synthesis remains BLOCKED by Vivado license. |
| Initial device families | INSTALLED | Artix-7, Kria SOM/Starter Kits, and Zynq UltraScale+ MPSoCs were installed before this continuation. Add-mode installer confirmed these existing selections were locked and unchanged. |
| Acceleration device support | INSTALLED | AMD/Xilinx 2026.1 installer Add completed successfully for `Install devices for Alveo and edge acceleration platforms`, including child selections `Devices for Alveo and edge acceleration platforms` and `Versal Devices for Alveo and edge acceleration platforms`. Installer log records all three selected entries checked. See `evidence/acceleration-2026.1/logs/install-summary.txt` and `evidence/acceleration-2026.1/logs/acceleration-add-config.txt`. |
| Vitis acceleration CLI | VERIFIED | `v++`, `vitis-run`, `platforminfo`, `emconfigutil`, and `xclbinutil` execute and report 2026.1 in `evidence/acceleration-2026.1/logs/tool-versions.log`. |
| FPGA kernel compile/synthesis | BLOCKED | Tool CLI is present; a licensed Vivado synthesis/build was not possible. No kernel build is claimed. |
| Host development tools | INSTALLED / VERIFIED | System `g++`, `make`, and `cmake` are present. XRT C++ development headers are absent from the installed runtime; no `xrt-dev` package candidate is available in configured APT metadata. FPGA host API compilation is therefore DEFERRED. No ABI or compatibility shim was introduced. |
| System XRT / NPU runtime | VERIFIED for existing NPU | System packages remain `xrt-base 2.21.75`, `xrt-npu 2.21.75`, and `xrt_plugin-amdxdna 2.21`; XRT-SMI detects NPU Strix and firmware 1.1.2.64. See `evidence/acceleration-2026.1/logs/xrt-examine.log` and `evidence/acceleration-2026.1/logs/runtime-linkage.txt`. |
| XRT for FPGA acceleration | DEFERRED / UNKNOWN for FPGA card | The installer added device support without installing a standalone host XRT package or requesting a system XRT replacement. Vitis `xclbinutil` defaults to its bundled tool build (XRT metadata 2.19.0); when `XILINX_XRT=/opt/xilinx/xrt` is explicitly set, the Vitis wrapper dispatches to the existing system `xclbinutil` (XRT 2.21.75). Both version checks pass, demonstrating the two tool paths coexist without package replacement. See `evidence/acceleration-2026.1/logs/xrt-selection.log`. No Alveo/FPGA card is enumerated, so FPGA runtime compatibility and execution remain unverified; system XRT was not changed. |
| 2026.1 embedded platforms | VERIFIED | `platforminfo -l` enumerates all eight installed base `.xpfm` files; `platforminfo -p` successfully reads each. Platform reports and generated-version data are in `evidence/acceleration-2026.1/logs/platforminfo-list.json` and `evidence/acceleration-2026.1/logs/platforminfo-individual.txt`. All are embedded platforms; this is not evidence of an Alveo card platform. |
| AMD/Xilinx and Digilent board definitions | INSTALLED; tool recognition UNKNOWN | Added the local Xilinx Board Store archive (SHA-256 in `evidence/acceleration-2026.1/logs/boardstore-source.sha256`): 417 `board.xml` definitions parsed as well-formed XML, no destination-path conflicts. Existing Digilent files remain; total Vivado repository has 456 board definitions, including `arty/C.0/board.xml`. Vivado Tcl board-part enumeration is not VERIFIED because the license gate prevents Vivado Tcl startup. See `evidence/acceleration-2026.1/board-resources.json`. |
| Physical FPGA card / platform execution | DEFERRED | No physical Alveo accelerator card was enumerated. No hardware build, programming, or kernel execution is claimed. |
| Vitis IP Cache, PDM, DocNav | NOT INSTALLED | These optional modules were not selected; not required for the verified CLI/platform inventory above. |
| Vivado/HLS synthesis license | BLOCKED / DEFERRED | This is the existing license gate, not an installation failure. No license activation or synthesis retry was done. |

## Installer and XRT safeguards

The local installer archive remains SHA-256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`. The successful Add operation was launched from the registered installation's own `xsetup` entrypoint so the installer recognized the existing tree. It changed only the user-local AMD/Xilinx installation and board repository. No APT/dpkg transaction, `installLibs.sh`, reboot, kernel, Mesa/RADV, libdrm, ROCm, XRT, amdxdna, firmware, or Golden State change occurred. The initial attempt to use the unpacked installer image for Add was rejected before installation; the subsequent registered Add completed successfully.

The Acceleration Add selection does not itself install or replace system XRT. The default Vitis utility reports bundled build metadata XRT 2.19.0. With `XILINX_XRT=/opt/xilinx/xrt`, the Vitis wrapper selects the installed system XRT 2.21.75 `xclbinutil`; both modes pass version checks. System XRT-SMI enumerates the NPU. Actual FPGA-card runtime compatibility remains DEFERRED. No system XRT transition was attempted.

## Post-install Golden State regression

All three regression checks passed after the Add operation:

- HIP: Radeon 890M / `gfx1150`, 1,024 GPU results.
- Vulkan: Radeon 890M / RADV `gfx1150`, 1,024 GPU shader results; CPU fallback forbidden.
- NPU CNN: 10 iterations, CPU fallback disabled, all profiled nodes on `VitisAIExecutionProvider`, NPU hardware counter increased by 14,621,744 ns, maximum CPU-reference absolute error 0.0.

Logs and the retained ORT profile are under `evidence/acceleration-2026.1/`; `npu-regression.json` carries the exact output and profile reference. XRT-SMI separately reports NPU Strix, driver `amdxdna_accel_driver`, XRT 2.21.75, and firmware 1.1.2.64.

## M9 status

**Acceleration device support: INSTALLED. Vitis acceleration CLI: VERIFIED. Embedded platform enumeration: VERIFIED. GPU/NPU Golden State regression: PASS. FPGA card/runtime execution and XRT host API development: DEFERRED/UNKNOWN. Vivado/RTL/HLS synthesis: BLOCKED by license. M9 remains NOT PASS until the license-gated synthesis criteria are completed.** No FPGA TOOLCHAIN WORKING STATE or M9 PASS tag is created by this partial continuation.
