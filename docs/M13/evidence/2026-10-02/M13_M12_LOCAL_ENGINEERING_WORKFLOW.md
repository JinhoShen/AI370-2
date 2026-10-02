# M13 engineering workflow evidence — M12 SP701 JTAG-to-AXI

Date: 2026-10-02 (Asia/Taipei).

## Workflow

The configured Ross Local Knowledge Base MCP was used for the live M12 engineering question, not for a repeated demo. The query returned PG174/UG908 confirmation that JTAG-to-AXI v1.2 supports Spartan-7 hardware AXI/AXI-Lite transactions and the UG835 Tcl transaction syntax. The raw query output is in [M12 local KB results](../../../M12/evidence/host-fpga-jtag-axi-20261002/local-kb-results.md).

The installed `vivado-revision-control` Agent Skill was consulted for source/rebuild handoff. Its project policy keeps generated XPR/cache files out of Git and favors durable RTL/XDC/Tcl sources. The M12 project uses `build.tcl` and `program_and_smoke.tcl` as its reproducible source path; a generated Vivado GUI project remains available locally.

Vivado IP catalog data was queried locally and returned `xilinx.com:ip:jtag_axi:1.2`; its protocol setting was configured as 32-bit AXI4-Lite. The design was synthesized, implemented, routed, timed and programmed through Vivado batch mode. Four live physical JTAG-to-AXI transactions passed with expected transformed readbacks. See the [M12 integration report](../../../M12/SP701_HOST_FPGA_INTEGRATION_REPORT.md) and its build/program evidence.

## M13 status effect

**VERIFIED:** local-KB-assisted AMD FPGA engineering research materially informed the selected M12 physical interface and transaction implementation; the resulting SP701 hardware interaction is real, with retained build and JTAG evidence. This is one bounded M13 local engineering workflow result.

**NOT VERIFIED by this workflow:** the Vivado MCP did not execute the hardware transactions; those were performed with Vivado 2026.1 batch Tcl. No Ross autonomous design changes, Vitis/HLS skill execution, local answer-generation model, or end-to-end air-gapped agent was tested. M13 remains IN PROGRESS.
