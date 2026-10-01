# M9 native toolchain installation — installed; software validation PASS

Date: 2026-10-01 (Asia/Taipei). This is the execution follow-up to the native route decision in `NATIVE_INSTALL_DECISION.md`. The previously recorded VM recommendation, M9.0/M9.1 inventory, PRE-M9 checkpoint, baseline, and APT simulations remain unchanged. Installation proceeded from the user-authorized local 2026.1 archive; no VM was created.

## ACTUAL installation

- Installer: `resources/Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar`; previously verified SHA-256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`.
- The archive was unpacked to `/home/shen/tools/Xilinx/installer-2026.1` and run in local batch mode. No account sign-in was required to install.
- Vitis Unified Software Platform 2026.1 was installed at `/home/shen/tools/Xilinx/2026.1`. Selected device modules were Artix-7, Kria SOM and Starter Kit, and Zynq UltraScale+ MPSoC. The Alveo/edge acceleration device module, Vitis IP Cache, and license-key post-install option were not selected. Vitis Acceleration target-support and workload validation remain deferred.
- Vitis Embedded Development 2026.1 was installed at `/home/shen/tools/Xilinx/vitis-embedded-2026.1`. The installer batch `Add` action did not accept this product config against the existing installation, so the installer-directed fresh install used a separate destination; neither installation tree was overwritten.
- The local Digilent board source archive (`f87ead045f21873e99234d8f4c4d6e3b8bb35da8dbffac64167f06d94a3532d6`) was extracted from its `new/board_files` tree into the Vivado board repository. The Arty A7-35 definition identifies part `xc7a35ticsg324-1L`, matching the selected Artix-7 family. The archive is local board-definition support; no physical board was detected or programmed.
- `installLibs.sh` was not run. No APT package transaction, APT update, kernel/Mesa/libdrm/ROCm/XRT/amdxdna/firmware mutation, or reboot was performed during this installation. The installation and extracted files are user-owned under `/home/shen/tools/Xilinx`.

## VERIFIED tool results

| Check | Result | Evidence |
|---|---|---|
| `vivado -version` | PASS — Vivado v2026.1, SW build 6511674 | `evidence/native-2026.1/logs/vivado-version.log` |
| `vitis -v` | PASS — Vitis v2026.1, SW build 6511674 | `evidence/native-2026.1/logs/vitis-version-confirm.log` |
| Vitis IDE startup | PASS — Vitis Unified IDE window opened and created its workspace | `evidence/native-2026.1/logs/vitis-gui-startup.log` |
| Vitis Embedded CLI and IDE startup | PASS — Vitis v2026.1; separate Embedded workspace/IDE launched | `evidence/native-2026.1/logs/vitis-embedded-start.log`, `vitis-embedded-gui-startup.log` |
| `vitis_hls -version` | PASS — Vitis HLS v2026.1, SW build 6493734. The installed HLS binary uses the vendor library/Tcl paths recorded in the runner. | `evidence/native-2026.1/logs/vitis-hls-version.log` |
| Vivado batch/Tcl smoke and RTL synthesis | Historical attempt BLOCKED BY LICENSE; current licensed SP701 RTL synthesis PASS. | Historical: `evidence/native-2026.1/logs/vivado-smoke-console.log`; current: `evidence/native-2026.1/logs/vivado-sp701-smoke-console.log` |
| HLS C synthesis | Historical attempt BLOCKED BY LICENSE; current licensed SP701 HLS synthesis PASS. | Historical: `evidence/native-2026.1/logs/hls-smoke-vitis-run.log`; current: `evidence/native-2026.1/logs/hls-license-smoke-console.log` and `evidence/license-unlocked-2026.1/synthesis/hls-sp701-csynth.rpt` |

The `installLibs.sh` notice after installation was treated as a broad vendor recommendation, not proof that all listed packages are required. Actual Vitis, Vitis Embedded, Vivado-version, Vitis IDE, and HLS-version processes started. HLS needed its shipped `libxv_hls_support.so`, Tcl 8.6.14, `RDI_DATADIR`, and its tool data directory; these were supplied from the installed tool tree. No system ABI symlink was created. The later synthesis failure is an explicit Vivado license check, not an unresolved loader error.

## VERIFIED protected-stack regression after installation

- HIP: PASS, 1,024 Radeon 890M / `gfx1150` results.
- Vulkan: PASS, 1,024 Radeon 890M / RADV `gfx1150` shader results; CPU fallback forbidden.
- NPU CNN: PASS, 10 iterations, CPU fallback disabled, all profiled nodes on `VitisAIExecutionProvider`, NPU engine counter increased by 14,709,940 ns, maximum CPU-reference error 0.0.
- Raw NPU result and ORT profile are in `evidence/native-2026.1/npu-regression.json` and `evidence/native-2026.1/profiles/`. HIP/Vulkan logs are under `evidence/native-2026.1/logs/`.
- M5 Golden State tag remains `ai370-2-npu-golden` at `849377c8f2da4c8cc230fc97c1c12fb800899d48`; this regression adds post-install evidence and does not replace the M5 record.

## Historical license gate and current status

The original installation-time Vivado/HLS attempts were blocked because the local license had not yet been configured. Those logs remain unchanged as historical evidence. Following license configuration, all required native software-toolchain checks passed; see [LICENSE_UNLOCKED_VALIDATION.md](LICENSE_UNLOCKED_VALIDATION.md).

**Current result: M9 software toolchain validation PASS; FPGA TOOLCHAIN WORKING STATE established.** Hardware/JTAG validation remains DEFERRED because no target is attached. Ubuntu 24.04.4 official support for Vivado/Vitis 2026.1 remains unconfirmed; successful native execution is not an official-support claim. The smoke sources and launch scripts are versioned under `native-toolchain-smoke/`; generated work is ignored.

## Evidence index

- Installer selections and reproducible configs: `evidence/native-2026.1/configs/`.
- Complete installer logs: `evidence/native-2026.1/logs/vitis-unified-installer.log` and `vitis-embedded-installer.log`.
- Tool version/startup, license-gate, and GPU/NPU regression logs: `evidence/native-2026.1/logs/`.
