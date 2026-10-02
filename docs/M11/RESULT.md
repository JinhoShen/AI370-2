# M11 SP701 Physical FPGA Validation

**Status: IN PROGRESS — SP701 JTAG identity VERIFIED; bounded DDR3 physical hardware test PASS; post-program regression and integration scope remains open.**

Date: 2026-10-02 (Asia/Taipei).

## Read-only detection

This section records the original read-only JTAG checkpoint. Its statements that programming and physical execution were not tested describe that earlier checkpoint and are superseded by the DDR3 run below; historical evidence is retained.

| Item | Result |
|---|---|
| USB | `0403:6011`, manufacturer `Xilinx`, product `SP701`, FT4232H; serial `46602010028` |
| Vivado / hw_server | Vivado 2026.1 connected to locally started `hw_server` at `TCP:127.0.0.1:3121` |
| JTAG target | One target: `127.0.0.1:3121/xilinx_tcf/Xilinx/46602010028A` |
| FPGA device | One device: `xc7s100_0` |
| Hardware Manager PART | `xc7s100` |
| IDCODE | Binary `00000011011111000111000010010011`; hex `0x037C7093` |
| DNA | Not exposed as a property by this Vivado `hw_device`; query returned the recorded unavailable-property response |
| Full board part | Installed Xilinx SP701 board definition maps to `xc7s100fgga676-2`. Hardware Manager's `PART` property reports the family string `xc7s100`, not package/speed suffix. |

The USB manufacturer/product/serial and JTAG target serial agree, and Hardware Manager identifies a Spartan-7 100 device. Together with the installed SP701 board definition, this confirms the attached SP701 target and its expected `xc7s100fgga676-2` board part. The package/speed suffix comes from the board definition, not a direct property returned by the live JTAG query.

## Boundaries

- No FPGA programming, bitstream load, flash operation or design write occurred.
- This confirms JTAG visibility and device identity only. It does not pass bitstream generation, programming, observable hardware execution or post-program regression.
- Existing M12 bitstream gate remains: the current smoke design lacks verified board I/O constraints and is blocked by NSTD-1/UCIO-1; its timing is unconstrained.

## Original DDR memory test design discovery (before hardware run)

**Read-only discovery: VERIFIED. Physical DDR test: NOT RUN.** Vivado 2026.1's installed SP701 board definition provides a `ddr3_sdram` board interface and `ddr3_sdram_preset` for `mig_7series`. The local board component lists a Micron `MT8JTF12864HZ-1G6G1` 1 GB DDR3 SODIMM; the supplied MIG configuration selects `MT41K256M16XX-107`, a 16-bit memory bus, and 512 MiB configured MIG address space. The board's differential system clock is 200 MHz. MIG 7-series DDR3 example/traffic-generator templates are installed, but no pre-generated SP701 project or standalone SP701 DDR XDC was found. The future design must be generated through the board-aware MIG flow and use its generated constraints without guessed pins or timing.

No DDR MIG design was generated, built or programmed in this discovery. The physical test plan and hashed local-file inventory are recorded in [`DDR_MEMORY_TEST_PLAN.md`](DDR_MEMORY_TEST_PLAN.md) and [`evidence/ddr-memory-discovery-2026-10-02/LOCAL_FILE_INVENTORY.md`](evidence/ddr-memory-discovery-2026-10-02/LOCAL_FILE_INVENTORY.md). These findings do not close M11 or alter the existing JTAG-only verdict.

## Evidence

Raw USB descriptor, read-only Tcl probe, Vivado log/journal, hw_server discovery log and SHA-256 manifest are in [`evidence/2026-10-02-jtag-detection/`](evidence/2026-10-02-jtag-detection/). The Vivado log includes unrelated board-file parser warnings; target scan, target open and device-property reads succeeded. DNA absence is a property limitation, not a JTAG detection failure.

## Bounded SP701 DDR3 hardware test — PASS

On 2026-10-02, the official SP701 MIG 7-series configuration was built, programmed to the verified SP701, and exercised with the MIG example traffic generator. Synthesis and implementation passed, blocking DRC count was zero, routed timing met constraints (WNS +0.994 ns, TNS 0.000 ns), and programming returned startup status HIGH. During a 30-second physical run, calibration remained asserted, MIG write/read status event counters reached 14,210,117 / 6,558,522, and the official sticky compare/error signal remained zero. Post-test JTAG access and FPGA IDCODE remained available.

The actual traffic configuration is a 16 MiB window (`0x00000000`–`0x00ffffff`), not the full 512 MiB MIG address space or 1 GB physical SODIMM. Completion pulses and per-pattern completion were not captured; the example provides no total numeric error counter. These limits are retained in the [DDR3 hardware test report](SP701_DDR3_Memory_Test_Report.md) and [evidence directory](evidence/ddr3-hardware-test-2026-10-02/). This DDR test PASS does not assert full M11/M12 completion.
