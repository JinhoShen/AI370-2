# M11 SP701 Physical FPGA Validation — JTAG identification checkpoint

**Status: IN PROGRESS — USB and JTAG target/device identification VERIFIED; programming and physical execution NOT TESTED.**

Date: 2026-10-02 (Asia/Taipei).

## Read-only detection

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

## Evidence

Raw USB descriptor, read-only Tcl probe, Vivado log/journal, hw_server discovery log and SHA-256 manifest are in [`evidence/2026-10-02-jtag-detection/`](evidence/2026-10-02-jtag-detection/). The Vivado log includes unrelated board-file parser warnings; target scan, target open and device-property reads succeeded. DNA absence is a property limitation, not a JTAG detection failure.
