# M12 AI + FPGA Integration — software coexistence smoke

Date: 2026-10-01 (Asia/Taipei). This is the first M12 software-only validation slice. It does not close M12 and does not claim physical FPGA execution.

## Scope and guardrails

- Reused the existing M5 NPU Golden State and M9/M10 FPGA software installation.
- No Kernel, Mesa/RADV, libdrm, ROCm/HIP, system XRT, amdxdna DKMS, NPU firmware or FPGA package was changed.
- Ran the already verified GPU/NPU smoke binaries sequentially in one host session. CPU fallback was forbidden for the Vulkan and NPU checks.
- This bounded smoke is not a high-load, long-duration, FPGA-card, JTAG, bitstream-programming or host-to-FPGA hardware test.

## ACTUAL baseline

| Area | Observed state | Evidence boundary |
|---|---|---|
| GPU | Radeon 890M, RADV GFX1150; HIP and Vulkan test binaries available | Device output from this run |
| NPU | XRT 2.21.75, amdxdna 2.21.260102.53.release, firmware 1.1.2.64, BDF `0000:c6:00.1` | `xrt-smi examine -r all` from this run |
| FPGA software | Vivado/Vitis/Vitis Embedded 2026.1 installed; `v++` and `platforminfo` report v2026.1 | Direct version commands and M9/M10 records |
| FPGA hardware | No JTAG target or physical accelerator card evidence | M11 remains DEFERRED |

## VERIFIED smoke results

The following sequence completed with exit status 0 at approximately 20:13 Asia/Taipei:

1. HIP: Radeon 890M / `gfx1150`, `PASS: 1024 HIP GPU results verified`.
2. Vulkan: Radeon 890M / RADV GFX1150, `PASS: 1024 GPU shader results verified; CPU fallback forbidden`.
3. NPU CNN: ten VitisAI inferences, CPU fallback disabled, all profiled nodes on `VitisAIExecutionProvider`, `/dev/accel/accel0` on `amdxdna_accel_driver` / `0000:c6:00.1`, NPU hardware time delta `14,731,075 ns`, maximum CPU-reference error `0.0`.
4. XRT/NPU enumeration: XRT `2.21.75`, amdxdna `2.21.260102.53.release`, firmware `1.1.2.64`, NPU Strix present.

No matching `amdgpu`, `amdxdna`, XRT, page-fault, TTM, GPU-reset, hang or soft-lockup error was emitted by the kernel-log filter during the bounded test window.

## M12 status

**VERIFIED:** software coexistence smoke for the existing Radeon GPU and XDNA2 NPU, with the installed FPGA toolchain present and unchanged.

**NOT VERIFIED:** a practical host↔FPGA workload, FPGA runtime/card compatibility, XRT C++ host API (headers remain unavailable), JTAG, implementation/bitstream programming, physical FPGA execution, or sustained resource contention.

M12 remains **IN PROGRESS**. The next M12 slice requires selecting a concrete host↔FPGA data/control workload; physical execution remains dependent on M11 hardware target availability. M7.1 and M8 remain OPEN/DEFERRED as recorded in the Roadmap.
