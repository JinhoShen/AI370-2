# SP701 Host↔FPGA JTAG-to-AXI integration

Vivado 2026.1 design for a real host-to-fabric transaction on the SP701. The host issues AXI4-Lite writes/reads through the onboard FT4232H JTAG link and Vivado Hardware Manager. The FPGA performs a 32-bit bitwise-NOT transform and returns the result through an AXI-Lite register slave.

This is a bounded bring-up/control path, not a production data-plane, XRT accelerator, PCIe endpoint, or DDR test. It does not use or modify the system XRT/NPU stack.

Rebuild in Vivado 2026.1:

```bash
source /home/shen/tools/Xilinx/2026.1/2026.1/Vivado/settings64.sh
vivado -mode batch -source build.tcl
```

The only board pins are the SP701 differential 200 MHz system clock, with pins and LVDS standard taken unchanged from the installed official MIG-generated SP701 XDC. `constraints/sp701_sysclk.xdc` retains those exact board-source values and a 5 ns clock.

Open the project:

```bash
vivado /home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/vivado/SP701_Host_FPGA_JTAG_AXI.xpr
```

For a clean out-of-tree rebuild that preserves the existing GUI project and generated files, set `AI370_M12_BUILD_ROOT` to an empty directory before running `build.tcl`. The script writes the XPR, runs, and reports below that directory. It does not program the board.

```bash
AI370_M12_BUILD_ROOT=/absolute/path/to/empty/build-dir \
  vivado -mode batch -source /home/shen/AI370-2/projects/FPGA/SP701_Host_FPGA_JTAG_AXI/build.tcl
```
