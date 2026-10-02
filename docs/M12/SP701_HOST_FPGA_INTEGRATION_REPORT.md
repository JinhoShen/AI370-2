# M12 — SP701 physical Host↔FPGA integration report

Date: 2026-10-02 (Asia/Taipei)
Scope: minimum safe physical host-to-fabric control/data path on the installed SP701.

## Verdict

**VERIFIED / PASS — physical Vivado JTAG-to-AXI control and data round-trip.** From the workstation, Vivado Hardware Manager used the SP701's existing FT4232H JTAG connection to issue AXI4-Lite writes into a programmed FPGA register block. FPGA logic performed a bitwise-NOT transform, and the host read back all four expected values. The FPGA remained visible on JTAG after the transactions.

**M12 overall remains IN PROGRESS / PARTIAL.** This closes the concrete physical Host↔FPGA bring-up blocker at the control/data-path level. It is not a Vitis/XRT application runtime, PCIe accelerator, high-throughput host data plane, GPU/NPU-to-FPGA AI workload, or M15 unified regression. Those scopes remain DEFERRED/NOT TESTED.

## Architecture decision

The earlier M12 gate asked for an SP701 `.xpfm` and XRT C++ host API. Current installed evidence shows no SP701 `.xpfm` among the eight Vitis embedded platforms and no XRT C++ headers; system XRT 2.21.75 is the protected XDNA/NPU runtime. Replacing system XRT to force an FPGA-card workflow would endanger the M5 Golden State and still would not create a supported SP701 platform.

The minimum currently supported physical path is instead **Vivado Hardware Manager → FT4232H JTAG → AMD JTAG-to-AXI Master v1.2 → AXI4-Lite register slave in the FPGA**. AMD's Vivado 2026.1 docs describe JTAG-to-AXI as a hardware runtime AXI/AXI-Lite transaction/debug path and support use without a processor. The local Ross Knowledge Base returned PG174 and UG908 material confirming the core and `create_hw_axi_txn` / `run_hw_axi` usage; exact query output is retained in [local KB results](evidence/host-fpga-jtag-axi-20261002/local-kb-results.md).

This is a real physical development/control path, not an application-facing XRT runtime. The M12 acceptance is therefore split: physical Host↔FPGA control/data round-trip is PASS; production host application and XRT acceleration remain DEFERRED. If M12 later requires a deployed host application, a separate board-specific transport (for example a verified SP701 USB-UART/MicroBlaze protocol) or a supported XRT accelerator board/platform will be needed.

## ACTUAL / VERIFIED build

| Item | Result |
|---|---|
| Board / FPGA | AMD/Xilinx SP701; board part `xilinx.com:sp701:part0:1.0`; live PART `xc7s100`; IDCODE `0x037C7093` |
| JTAG target | `127.0.0.1:3121/xilinx_tcf/Xilinx/46602010028A` |
| Tool | Vivado 2026.1, build 6511674; active Enterprise license |
| Project | `SP701_Host_FPGA_JTAG_AXI`; source project at `/home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI`; GUI project `/home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/vivado/SP701_Host_FPGA_JTAG_AXI.xpr` |
| IP / protocol | `xilinx.com:ip:jtag_axi:1.2`, 32-bit AXI4-Lite |
| Design function | Host writes register `0x00`; FPGA stores input and computes bitwise NOT; host reads result at `0x04` |
| Clock / constraints | SP701 differential 200 MHz system clock. Pin/IOSTANDARD/clock values copied from Vivado-generated SP701 MIG XDC retained by the official-preset M11 build. Bank-0 CFGBVS/CONFIG_VOLTAGE values match the M11 SP701 board constraints. No guessed pins. |
| Synthesis / implementation | PASS; routed design and bitstream complete |
| DRC | 0 errors. Remaining report findings are non-blocking IP/debug-core warnings/advisories; no severity overrides or suppressions. |
| Timing | PASS for specified clock constraints; WNS `+0.616 ns`, TNS `0.000 ns`, WHS `+0.052 ns`, THS `0.000 ns`; report states all specified timing constraints met and 0 unconstrained internal endpoints. |
| Utilization | 1,184 Slice LUTs (1.85%); 2,482 Slice Registers (1.94%) |
| Bitstream | Local ignored build artifact `.../vivado/SP701_Host_FPGA_JTAG_AXI.runs/impl_1/sp701_host_fpga_top.bit`, 3,687,023 bytes; SHA-256 `f06fe9533f85345a274005719dd22fd2bed48eb354c96668c8559afc00601bff`. It is not committed. |

## ACTUAL / VERIFIED physical transactions

The script first asserted the expected JTAG target and live FPGA family/IDCODE, then programmed only the FPGA's volatile configuration. The JTAG-to-AXI core appeared as `hw_axi_1`. Each write/read transaction was run over the live JTAG connection:

| Host write to `0x00` | FPGA read from `0x04` | Expected | Result |
|---:|---:|---:|---|
| `0x12345678` | `0xEDCBA987` | `~input` | PASS |
| `0x00000000` | `0xFFFFFFFF` | `~input` | PASS |
| `0xFFFFFFFF` | `0x00000000` | `~input` | PASS |
| `0xA5A5F00D` | `0x5A5A0FF2` | `~input` | PASS |

Post-transaction JTAG refresh still returned `xc7s100_0` and IDCODE `0x037C7093`. The operation did not access FPGA flash and did not run a DDR test. The new configuration is volatile; a power cycle removes it.

## Protected stack and boundaries

No package install, kernel/driver operation, or GPU/NPU command was run for this M12 build/program step. Kernel, Mesa/RADV, libdrm, ROCm/HIP, XRT, amdxdna and NPU firmware were not modified. No DDR traffic test or AI model inference was run.

The initial pre-program Hardware Manager refresh logged warnings because the FPGA still held the previous M11 bitstream and the new design's probes file was not yet associated. Programming succeeded; after programming Vivado detected the JTAG-to-AXI core and all AXI transactions passed. The full transcript preserves those pre-program warnings and successful post-program state.

## Rebuild and evidence

The durable source and build procedure are in [`projects/FPGA/SP701_Host_FPGA_JTAG_AXI`](../../projects/FPGA/SP701_Host_FPGA_JTAG_AXI/). To recreate the GUI project and bitstream with Vivado 2026.1:

```bash
source /home/shen/tools/Xilinx/2026.1/2026.1/Vivado/settings64.sh
vivado -mode batch -source /home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/build.tcl
```

To reopen the currently generated project:

```bash
vivado /home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/vivado/SP701_Host_FPGA_JTAG_AXI.xpr
```

Build reports, XDC, RTL snapshot, bitstream checksum and full physical transaction transcript are under [`evidence/host-fpga-jtag-axi-20261002/`](evidence/host-fpga-jtag-axi-20261002/). The `.bit` and generated Vivado caches are excluded from Git.

AMD references returned by the local KB: [JTAG to AXI Master PG174](https://docs.amd.com/v/u/en-US/pg174-jtag-axi), [Vivado 2026.1 UG908 JTAG-to-AXI hardware communication](https://docs.amd.com/r/en-US/ug908-vivado-programming-debugging/Hardware-System-Communication-Using-the-JTAG-to-AXI-Master-Debug-Core), [Vivado Tcl `create_hw_axi_txn` UG835](https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/create_hw_axi_txn), and [Vitis 2026.1 XRT and platform requirements UG1701](https://docs.amd.com/r/en-US/ug1701-vitis-accelerated-embedded/Installing-Xilinx-Runtime-and-Platforms).
