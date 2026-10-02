# Ross HLS Skill bounded execution

Applied the installed Ross `hls-run-flow` CLI fallback for `csynth`, then ran the installed `hls-synth-report` helper against the resulting component. The output is for a disposable 32-bit invert component targeting `xc7s100fgga676-2` and is unrelated to physical M12 program state.

- Initial CLI preflight failed because Vitis required `--part` on the command line; retained as `attempt1-cli-preflight.log`.
- Corrected `v++ -c --mode hls --part xc7s100fgga676-2 --config ... --work_dir ...` exited 0.
- The same component then ran `vitis-run --mode hls --csim` with a four-vector test bench; all values matched and exit status was 0. The run-flow Skill C-simulation step is VERIFIED.
- `csynth.rpt` generated; report estimated 32 LUT, 0 BRAM/DSP, estimated Fmax 1184.83 MHz. The estimate is not a routed timing result.
- Report extraction skill exited 0 and produced `synth-report-skill.json`.
- The Vitis/Vivado log contains six unrelated installed board-file parser CRITICAL WARNING messages; synthesis and IP export completed with exit 0. They are preserved, not suppressed.
- This verifies the bounded C simulation, C synthesis and report skills only. It does not verify C/RTL cosimulation, implementation, Vitis Unified UI, Vivado MCP hardware control, or FPGA execution.

Source and config are in [`projects/FPGA/Ross_HLS_Skill_Smoke`](../../../../../projects/FPGA/Ross_HLS_Skill_Smoke/). The complete generated build directory stays under ignored `output/M13/` and is not committed.
