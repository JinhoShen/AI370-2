# M11 SP701 onboard DDR3 hardware test plan

**Discovery status:** local board preset and MIG example path VERIFIED by read-only inspection.
**Discovery record status:** Historical read-only plan, superseded by the execution documented in [`SP701_DDR3_Memory_Test_Report.md`](SP701_DDR3_Memory_Test_Report.md). At discovery time no bitstream was generated/programmed and no DDR access occurred.

## Confirmed board and MIG configuration

The installed Vivado 2026.1 SP701 board definition is `xilinx.com:sp701:part0:1.0`, targeting `xc7s100fgga676-2`. Its board interface `ddr3_sdram` is `xilinx.com:interface:ddrx_rtl:1.0`, names component `ddr3_sdram`, and selects the `ddr3_sdram_preset` for `xilinx.com:ip:mig_7series`.

The board component identifies a Micron `MT8JTF12864HZ-1G6G1` DDR3 SODIMM and describes its capacity as 1 GB. The supplied MIG project selects `DDR3_SDRAM/Components/MT41K256M16XX-107`, configures a 16-bit memory data bus, and sets `C0_MEM_SIZE` to 536,870,912 bytes (512 MiB). Therefore, the defensible test scope from this preset is its configured 512 MiB MIG address space; this plan does not claim coverage of the full 1 GB module.

The board definition exposes `sys_diff_clock` as the MIG system clock interface at 200 MHz. `mig.prj` selects a differential system clock, uses the system clock as the reference clock, and sets `InputClkFreq=200` MHz and `TimePeriod=2500` ps. The board file describes the oscillator as a SiTime SiT9102AI differential 200 MHz source. The preset includes explicit MIG pin selections; no pin, I/O standard, or timing value is to be guessed or manually substituted.

## Available official design path

Vivado includes the `mig_7series_v4_2` IP and its DDR3 example-design templates, including example top-level/test-bench resources and traffic-generator RTL. AMD UG586 states that generating a 7-series DDR2/DDR3 MIG design produces user and example designs; the example includes a synthesizable traffic generator that is verified in simulation and hardware. The local installation does not contain a pre-generated SP701 `.xpr` project or a standalone SP701 `.xdc`/`.ucf` file. The board-specific input is the installed SP701 board definition and its `mig.prj`; MIG must generate the project-specific user/example design and constraints from that preset.

Use Vivado's board-aware MIG flow: create a temporary project for the SP701 board part, instantiate `mig_7series` through the `ddr3_sdram` board interface, apply the board's `ddr3_sdram_preset`, and generate/open the MIG example design. Before implementation, inspect the generated XDC and IP configuration to verify they came from this board preset and preserve the board pin selections. Do not add hand-written DDR pins, I/O standards, or timing constraints. Stop if the generated project does not bind the board interface/preset correctly or has unresolved DDR pin/clock constraints.

## Proposed minimal physical test (future authorized hardware phase)

1. Build and implement the generated MIG example design using the supplied SP701 preset and generated constraints. Require clean blocking DRCs and reviewed timing reports before producing a bitstream. Save the exact source/preset hashes, Vivado/IP versions, reports, DCP, and bitstream SHA-256.
2. In the later physical-test step, program only the resulting test bitstream through Vivado Hardware Manager. Programming is expressly outside this read-only discovery.
3. Observe `init_calib_complete` with the generated example's debug interface/ILA. Require it to assert within a recorded timeout; otherwise fail as calibration timeout and capture available MIG calibration/debug signals.
4. Run the MIG example traffic generator on a bounded, documented address range first. The example writes generated patterns, reads them back, and compares returned data. Use the generated VIO/traffic controls where the generated design exposes them; use ILA to capture calibration, traffic control, write/read activity, compare error and first-error details. Confirm the exact control/signal names against the generated design before the physical run.
5. Record generated write/read command and data counters. MIG example error status is useful for detecting and locating a mismatch, but its status path latches first-error information; it is not a total mismatch counter. If a numeric error count is required, add a small documented saturating counter in the test wrapper, incremented on each valid compare mismatch. Do not represent a sticky error bit as an error count.
6. PASS criteria: calibration completes; bounded test reports completed writes and reads; expected traffic completes before timeout; mismatch counter is zero; no MIG compare/error status is asserted. Any calibration timeout, nonzero mismatch, incomplete traffic, or inaccessible result is FAIL/INCONCLUSIVE, never PASS.

The initial board test should exercise a small bounded range and short run. Larger address coverage or long-duration testing should be a separate, explicitly recorded extension after the first test is stable.

## Evidence to retain for the future run

- Board revision/identity, JTAG device, and selected Vivado board/part.
- Board-file, preset and MIG project SHA-256; Vivado and MIG IP versions.
- Generated project source/XDC manifest and confirmation that no hand-guessed DDR constraints were used.
- Synthesis/implementation/DRC/timing/utilization reports and exit status.
- Bitstream path, byte size and SHA-256.
- Program action/time and Hardware Manager log (only when programming is authorized).
- Calibration result and timeout, tested address range, pattern/traffic configuration, writes/reads, data counts, comparison error count, first mismatch details, elapsed cycles/time, verdict.
- ILA/VIO capture or equivalent raw observation evidence.

## Official references

- AMD, [UG586: Example Design](https://docs.amd.com/r/en-US/ug586_7Series_MIS/Example-Design): MIG generation produces an example design with synthesizable traffic generator and hardware-validation use.
- AMD, [UG586: Run the Example Design](https://docs.amd.com/r/en-US/ug586_7Series_MIS/Run-the-Example-Design): implementation and hardware-run flow for the MIG example.
- AMD, [UG586: Traffic Generator](https://docs.amd.com/r/en-US/ug586_7Series_MIS/example_design/rtl/traffic_gen): describes the example traffic generator stimulus.
- AMD, [UG586: Isolating the Data Error](https://docs.amd.com/r/en-US/ug586_7Series_MIS/Isolating-the-Data-Error): MIG traffic-generator error isolation with debug capture.

## Limitations recorded at discovery time

- This is design discovery and a proposed test only; no MIG core was generated, no synthesis/implementation was run for this DDR design, no bitstream was created or programmed, and no DDR access occurred.
- The board file's module-capacity description (1 GB) differs from the supplied MIG project's configured address space (512 MiB). Reconcile only with authoritative board/MIG evidence if full-module coverage is later required.
- The generated example's exact debug/control ports and whether its default traffic sequence covers the intended bounded range must be verified from the generated output before the hardware run.
- Current M12 smoke-design bitstream blocker (unconstrained top-level I/O) is separate. The DDR design must use the board-aware MIG-generated constraints and pass its own DRC/timing review.

## Execution outcome (2026-10-02)

The planned SP701 DDR3 test was subsequently executed. The bounded 16 MiB physical MIG traffic test passed with calibration asserted and no sticky MIG compare/error indication; synthesis, implementation, DRC, timing, bitstream programming and post-test JTAG checks passed. See the [formal hardware report](SP701_DDR3_Memory_Test_Report.md) and [dated evidence](evidence/ddr3-hardware-test-2026-10-02/). The run did not cover the full 512 MiB MIG configured range or 1 GiB SODIMM, and this result alone does not close overall M11/M12.
