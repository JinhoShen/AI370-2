# SP701 DDR3 Memory Test Vivado project

Formal project name: `SP701_DDR3_Memory_Test`
Vivado project file: `SP701_DDR3_Memory_Test.xpr`
Board: `xilinx.com:sp701:part0:1.0` / `xc7s100fgga676-2`

This project is built from the installed Vivado 2026.1 SP701 board definition and its `ddr3_sdram_preset` MIG project. The MIG input is preserved here as `config/sp701_mig.prj`; its SHA-256 must match the evidence/report. No DDR pins, I/O standards, or timing constraints may be guessed or manually substituted.

`create_project.tcl` creates a MIG configuration project from the preserved `config/sp701_mig.prj`, opens the official MIG IP example project, and saves the resulting traffic-generator project under this directory. `prepare_project.tcl` restores the required official example synthesis sources from Vivado's local generated example when absent, adds the documented wrapper/ILA, and saves the project. Run both in Vivado 2026.1 batch mode to recreate from the tracked configuration. A clean-checkout rebuild has not yet been independently exercised; the current project was generated and built on this workstation.

Generated MIG/ILA HDL, XDC and Vivado run/cache products remain local and are excluded from Git. Their relevant configuration, the final generated MIG XDC, reports, post-synthesis/post-route DCP checkpoints, programming transcript and ILA capture are retained in the M11 evidence directory. No `.bit` is tracked.

Example recreation commands (Vivado 2026.1 installation path may vary):

```bash
vivado -mode batch -source create_project.tcl
vivado -mode batch -source prepare_project.tcl
vivado /home/shen/AI370-2/projects/FPGA/SP701_DDR3_Memory_Test/SP701_DDR3_Memory_Test.xpr
```

Open the finished design with:

```bash
vivado /home/shen/AI370-2/projects/FPGA/SP701_DDR3_Memory_Test/SP701_DDR3_Memory_Test.xpr
```

The project is not a PASS claim by itself. The M11 report records actual build, programming and physical DDR results separately.
