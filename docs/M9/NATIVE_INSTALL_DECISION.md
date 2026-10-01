# M9 route change — native Ubuntu 24.04.4 validation

Date: 2026-10-01. This record captures the user's explicit route change and supersedes the earlier M9 execution route only from this point onward. The earlier VM recommendation and M9.0/M9.1 prechecks are preserved in their original files and commits.

## DECISION

- Host: Ubuntu 24.04.4 LTS, kernel `6.17.0-14-generic`.
- The earlier compatibility review did **not** confirm Ubuntu 24.04.4 as an officially supported OS for Vivado/Vitis 2026.1; see `docs/MASTER_PLAN_REVIEW.md` and the preserved VM recommendation in `docs/M9/PRECHECK_GATE.md`.
- The user explicitly selected native Vivado/Vitis 2026.1 installation and validation on this host. Do not wait for Ubuntu 24.04.3 media and do not create a VM.
- M9 evidence will be judged by actual installation and execution results. A successful install or smoke test is **not** evidence that AMD officially supports Ubuntu 24.04.4.
- Install scope: Vivado 2026.1, Vitis Embedded, and Vitis HLS. Vitis Acceleration is excluded.

## PRE-INSTALL RECOVERY CHECKPOINT

- Checkpoint: `output/recovery/PRE-M9-NATIVE-20261001T041447Z/`.
- Root archive: 73 GiB; SHA-256 `f2c02179e653b166e5530ca62322a509358327258385d728236105ba690f1938`.
- EFI archive: 6.2 MiB; SHA-256 `30e0565058015941328cbabf3d22b628a57e1be5e9ca3994e3e1990a1256dd94`.
- `scripts/verify_local_checkpoint.sh` verified both archive hashes and restored selected OS identity, account, package database, boot files, and EFI files into a temporary isolated directory: `SELECTED_FILE_RESTORE_PASS`.
- Limits: live, same-NVMe file-level checkpoint; not atomic; `resources/` and `output/` are excluded from `root.tar`; complete boot restore was not tested. The checkpoint is not an off-device backup.

## PRE-INSTALL STACK BASELINE

The timestamped raw report and its SHA-256 are kept root-only beside the checkpoint at `output/recovery/PRE-M9-NATIVE-20261001T041447Z/native-stack-baseline.txt`; report SHA-256: `507ed4cdffb4661c83c266b18111d7c63124933aa4183c24498466efdb0a3435`.

| Component | ACTUAL before M9 install |
|---|---|
| Host kernel | `6.17.0-14-generic`; amdgpu uses the in-kernel module with this vermagic. |
| Mesa/Vulkan | Mesa `25.2.8-0ubuntu0.24.04.1`; `vulkaninfo` enumerates AMD Radeon 890M (`RADV GFX1150`, driver `radv`) and llvmpipe. |
| libdrm | `2.4.125-1ubuntu0.1~24.04.1` (`libdrm2`, amdgpu/radeon/intel/nouveau runtime packages at the recorded baseline). |
| ROCm | `rocm-core 7.2.1.70201-81~24.04`; installed ROCm packages and versions are in the raw report. `rocminfo` enumerates `gfx1150` Radeon 890M and `aie2p` Strix NPU. |
| XRT | `xrt-base` and `xrt-npu` `2.21.75`; XRT commit `4eb1f4392a012b4e6eca759762389c612537f7c7`. |
| amdxdna | Loaded DKMS module `2.21.260102.53.release_20260309`, source commit `6f881ad230142b707ca8ce5b33fca426a926c551`, from `/updates/dkms/`, vermagic matches the current kernel. |
| NPU firmware | `xrt-smi examine` reports NPU firmware `1.1.2.64`; current `npu.dev.sbin` SHA-256 is recorded in the raw report. |
| Golden State | `ai370-2-npu-golden` points to M5 PASS commit `849377c8f2da4c8cc230fc97c1c12fb800899d48`. Existing full NPU CNN/no-fallback and HIP/Vulkan verification evidence remains in `docs/M5/reboot/`. |

The baseline probes confirmed enumeration and exact versions. They do not replace the requested post-install Vulkan/HIP/NPU regression suite.

## APT SIMULATION AND STOP

The Ubuntu branch of the installer archive's `installLibs.sh` was inspected without executing it. It calls `apt-get update` and then individually installs its broad dependency list; that script was not run.

1. Exact vendor dependency-name simulation is preserved in `docs/M9/apt-simulation-vendor-prerequisites.txt`. It exited 100 because current Ubuntu 24.04 APT metadata has no candidates for `libtinfo5` and `libncurses5`, and `libasound2` is a virtual package with no direct candidate. The installer archive itself contains Ubuntu/24 `libncurses.so.5` and `libtinfo.so.5`; this fact does not authorize replacing the vendor package list with hand-made system symlinks.
2. A candidate Ubuntu 24.04 package-name simulation is preserved in `docs/M9/apt-simulation-ubuntu24-candidate.txt`. It used `apt-get -s --no-upgrade --no-install-recommends` with the available Ubuntu 24 package names and `libasound2t64`. Even with `--no-upgrade`, APT planned **49 upgrades, 117 new installs, and 0 removals**. The plan includes Mesa/RADV changes: `mesa-vulkan-drivers`, `mesa-libgallium`, `libgl1-mesa-dri`, `libglx-mesa0`, `libegl-mesa0`, and `libgbm1` from `25.2.8-0ubuntu0.24.04.1` to `25.2.8-0ubuntu0.24.04.3`, plus `libegl1-mesa-dev` at `.3`.

**STOP:** This APT solver plan crosses the user's explicit graphics-stack gate. No dependency package was installed, no APT update was run, and the installer was not extracted or launched. Kernel, Mesa, libdrm, ROCm, XRT, amdxdna, firmware, and the M5 Golden State remain unmodified by this M9 attempt. M9 is not PASS.

## Next action after the gate is resolved

Recompute a precise install transaction against the unchanged host state. Proceed only if the approved Vivado/Vitis Embedded/HLS dependency transaction has no kernel, Mesa, libdrm, ROCm, XRT, amdxdna, or NPU firmware changes. Then install the selected components, verify actual tool versions, batch/Tcl, and minimal synthesis, and run the full host Vulkan/HIP/NPU Golden State regressions before any M9 PASS claim.
