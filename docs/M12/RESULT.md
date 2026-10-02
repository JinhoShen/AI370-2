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

## M12.1 host↔FPGA integration gate

The installed 2026.1 platform inventory was checked without changing the toolchain. The eight parsed `.xpfm` files target KV260, VCK190, VEK280, VEK385 and VRK160 embedded platforms; none targets the SP701 Spartan-7 part. The current system XRT installation exposes runtime libraries and NPU tools but no `xrt*.h` development headers, and the M9 record already marks the XRT C++ host API DEFERRED. `v++` therefore has no safe, hardware-relevant host build path for the current SP701 setup.

**M12.1 status: DEFERRED / UNKNOWN.** A future host↔FPGA workload needs either a matching platform/runtime and headers or an actual SP701-specific supported flow. `hw_emu`/`hw` options visible in `v++` help are capability declarations, not evidence that a compatible platform or FPGA target is available. No emulation or hardware result is claimed.

## Phase A pre-hardware implementation gate

The existing minimal `m9_adder` smoke design was taken from the saved RTL through implementation using Vivado 2026.1 and the SP701 part `xc7s100fgga676-2`. No synthesis or implementation rerun was needed after the initial run; the retained log and artifacts were inspected.

| Sub-item | Verdict | Evidence / boundary |
|---|---|---|
| Synthesis | PASS | `synth_design completed successfully`; 0 synthesis errors in `pre_hardware/sp701_impl_bitstream.log` |
| Optimization / placement | PASS | `opt_design`, `place_design` completed; precondition DRC had 0 errors |
| Route | PASS | `route_design completed successfully`; `output/M12/pre-hardware/post_route.dcp` exists and is readable, SHA-256 `d609124ddac694fe7ae8edb8a60a0e7abbbdf2b1d6231775f1eef3631082fc64` |
| Utilization | VERIFIED | `utilization_implemented.rpt`: 4 LUTs, 5 registers, 14 bonded I/O, 1 BUFG |
| Timing | UNCONSTRAINED / NOT VALIDATED | No user timing constraints; five registers have no clock constraint and input/output delays are absent; WNS/TNS are `NA` |
| Bitstream | BLOCKED BY BOARD CONSTRAINT | `write_bitstream` stopped at DRC `NSTD-1` and `UCIO-1`: all 14 ports have default IOSTANDARD and no LOC. Bitgen was not run. No severity override was used. |
| HLS | PASS (prior evidence) | SP701 `m9_adder` C synthesis and reports are retained in M9 evidence |
| hw_server | SOFTWARE READY | Vivado 2026.1 `hw_server` started and listened on TCP port 3122 in a local readiness probe; no target was connected or programmed |
| Physical SP701 | HARDWARE PENDING / NOT TESTED | No JTAG target evidence tonight |

The installed SP701 Board Store data includes `part0_pins.xml` with named pin mappings and a differential `SYSCLK_P/N` pair, but it does not provide a complete XDC mapping for this generic single-ended `clk`, `a`, `b` and `sum` top-level interface. Mapping those ports to guessed pins or converting the clock without a defined design interface would be unsafe. No constraint was added and no bitstream was fabricated by downgrading DRC severity.

Phase A therefore remains **PRE-HARDWARE PARTIAL**: synthesis, placement, route, utilization, checkpoint and HLS are verified; timing is not validated; bitstream and hardware programming remain pending a proper SP701 design/XDC interface.

## 2026-10-02 SP701 JTAG identification update

After the user set SW13 to JTAG mode, re-powered the board, and the Vivado 2026.1 Linux cable rules were installed, a read-only Hardware Manager probe detected one SP701 target. The USB identity (`Xilinx` / `SP701`, FT4232H serial `46602010028`) matched the Vivado JTAG target serial; `get_hw_devices` returned `xc7s100_0`, PART `xc7s100`, IDCODE `0x037C7093`. The installed SP701 board definition maps the board to `xc7s100fgga676-2`; the live hardware PART property does not expose package/speed suffix. DNA is not exposed as a property by this `hw_device`.

This closes **JTAG target/device identification only**. No bitstream was loaded or programmed, and FPGA execution remains untested. The NSTD-1/UCIO-1 board-constraint block and unconstrained timing for the existing M12 smoke design remain unchanged. Full log, Tcl and checksums are retained in [M11 JTAG evidence](../M11/evidence/2026-10-02-jtag-detection/).

## Later M11 DDR hardware update

The statements above describe the M12 smoke design and its state at that checkpoint. A separate M11 design using the official SP701 MIG DDR3 preset was later programmed and passed a bounded 16 MiB physical DDR write/read/compare test. This does not resolve the M12 smoke design's missing I/O constraints, and does not verify an application-level host↔FPGA integration path. See the [M11 DDR3 report](../M11/SP701_DDR3_Memory_Test_Report.md).
