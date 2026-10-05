# Vitis HLS C/RTL co-simulation and implementation smoke

**Date:** 2026-10-05 (Asia/Taipei)
**Target:** `xc7s100fgga676-2`
**Design:** isolated combinational `invert32` HLS component; four fixed vectors.

This is a Vitis 2026.1 CLI tool-flow check using the existing M13 smoke source. The prior csynthesis/C-simulation evidence is retained at `../../2026-10-02/hls-skill-smoke/`. This run added RTL co-simulation and Vivado implementation. These later steps were run directly with `vitis-run`; they were not invoked autonomously through the Ross Skill or Codex agent.

## Results

- C/RTL co-simulation: **PASS**, exit 0. All four expected values matched in the RTL simulator. Full log: `cosim.log`.
- Vivado synthesis / implementation / route: **PASS for this isolated HLS component**, `vitis-run --impl` exit 0. The routed DRC report shows zero errors, and the route report records zero unrouted nets. Full log: `implementation.log`.
- Routed utilization: 10 slices, 32 LUTs, 0 registers, 0 DSP, 0 BRAM.
- Timing: **NOT VALIDATED**. This combinational component has no sequential path; the timing report reports 34 partially constrained input ports. The logged WNS 3.321 ns is therefore not a board timing-closure claim.
- Physical FPGA: **NOT TESTED**. No bitstream was generated or programmed; this project has no SP701 board I/O pin constraints and is not the M11/M12 project.

## Reproduction

From the repository root:

```bash
source /home/shen/tools/Xilinx/2026.1/2026.1/Vitis/settings64.sh
vitis-run --mode hls --cosim \
  --config projects/FPGA/Ross_HLS_Skill_Smoke/hls_config.cfg \
  --work_dir output/M13/ross-hls-cosim-implementation-20261005/cosim-work-corrected
vitis-run --mode hls --impl \
  --config projects/FPGA/Ross_HLS_Skill_Smoke/hls_config.cfg \
  --work_dir output/M13/ross-hls-cosim-implementation-20261005/cosim-work-corrected
```

Generated work files remain under ignored `output/M13/`; only source, logs and concise reports are retained here. No FPGA was programmed and no protected GPU/NPU stack was changed.
