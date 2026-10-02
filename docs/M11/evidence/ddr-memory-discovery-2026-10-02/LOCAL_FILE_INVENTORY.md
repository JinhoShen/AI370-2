# SP701 DDR/MIG read-only discovery evidence

Date: 2026-10-02 (Asia/Taipei)  
Vivado install inspected: `/home/shen/tools/Xilinx/2026.1/2026.1/Vivado`

## Installed SP701 board files

Directory: `Vivado/data/boards/board_files/Xilinx/sp701/1.0`

| File | SHA-256 | Relevant evidence |
|---|---|---|
| `board.xml` | `cfeae7b990a0fc86b3ad128b58432ddbe475eab9f1da3ba4d7fa68514fecb856` | Board part `xc7s100fgga676-2`; `ddr3_sdram` interface; DDR3 module identity/capacity; 200 MHz `sys_diff_clock` interface. |
| `preset.xml` | `c5a7ee0bc0d8cbf290cfdce43a6d5b06382a099fde8d81a729bc2ef0a111164c` | `ddr3_sdram_preset` binds `mig_7series` to `mig.prj`. |
| `mig.prj` | `a1938c177c7c9f1559fafc5872e36905391245f1d7e142b1e01b94ad0731bd30` | MIG v4.2, DDR3 component `MT41K256M16XX-107`, differential 200 MHz system clock, 16-bit memory bus, 536,870,912-byte configured memory size, 64-bit AXI data width, 29-bit AXI address width, explicit pin selection. |
| `part0_pins.xml` | `13817490b442bdd5afb24727e0d41e06730d1de973d2f37b2ae176b6b1c45047` | Board component pin map used by the board definition. |

The board XML identifies DDR component `Micron MT8JTF12864HZ-1G6G1`, type DDR3, described as a `1 GB DDR3 memory SODIMM`. Its MIG project selects `MT41K256M16XX-107` and configures a 512 MiB address space. The two capacity statements are retained as-is; this discovery does not infer that the configured MIG range covers all module capacity.

The `sys_diff_clock` board interface maps `SYSCLK_P/N`, reports 200,000,000 Hz, and describes a SiTime SiT9102AI 2.5V LVDS differential oscillator. The MIG project uses differential system clock and system clock reference, with `InputClkFreq=200` MHz and `TimePeriod=2500` ps.

## MIG example resources and SP701-specific search

Installed IP directory: `Vivado/data/ip/xilinx/mig_7series_v4_2`.

The IP component metadata includes DDR3 example-design resources under `data/dlib/7series/ddr3_sdram/`, including `example_top.v`, simulation test bench, generated-design source templates and traffic-generator modules. This is an IP example template, not a pre-generated SP701 project.

Read-only search of the installed Vivado tree for SP701-named `.xdc`, `.xpr` and `.bd` files returned no files. The installed SP701 board directory contains `board.xml`, `preset.xml`, `mig.prj`, `part0_pins.xml`, image, changelog, license and metadata; there is no standalone `.xdc`, `.ucf`, `.sdc`, `.tcl` or pre-generated `.xpr` in that directory. MIG's board preset/project is the available board-specific configuration input; any project constraints must come from Vivado's board-aware MIG generation flow.

The MIG project includes explicit pin selections. No pin assignment, I/O standard, clock value or timing constraint was manually created or modified during this read-only discovery.

## Status boundary

- Board DDR interface and preset presence: VERIFIED by local files.
- MIG DDR3 example/traffic-generator template availability: VERIFIED by local IP metadata/resources.
- Pre-generated SP701 DDR test project/XDC: NOT FOUND in inspected installation.
- Generated SP701 MIG design/constraints: NOT GENERATED.
- DDR synthesis, implementation, timing, bitstream, programming and memory test: NOT RUN.
- No protected GPU/NPU/XRT stack files were changed.

See [`../../DDR_MEMORY_TEST_PLAN.md`](../../DDR_MEMORY_TEST_PLAN.md) for the proposed future build and physical-test flow.
