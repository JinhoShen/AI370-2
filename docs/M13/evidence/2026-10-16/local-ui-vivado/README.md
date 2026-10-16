# Local UI → Ross/Qwen → XSim → Vivado synthesis — actual acceptance

**PASS, 2026-10-16 11:55:26.101593–12:00:13.168597 +08:00; elapsed 287.066 seconds.** Request was submitted through the same loopback UI HTTP API with its per-session request token. No cloud/Codex runtime. Existing Qwen3.8-27B-UD-Q4_K_XL formal ENGINEERING service was reused; exact post-run runtime verifier PASS.

The model read the unchanged task and RTL, invoked genuine Ross Skill and local KB MCP, received an actual baseline XSim failure, authored one accepted RTL patch, and obtained the fixed testbench's terminal PASS on the second XSim execution. proof-audit.json independently checks patch provenance and Ross/validation results. The testbench and fixed runner were not modified.

After the model repair, the UI's trusted executor ran real Vivado 2026.1 batch synthesis in the existing Bubblewrap sandbox with host NIC visibility for the already installed license. The fixed Tcl targets xc7s100fgga676-2 and reads only the final model-authored RTL. Exit 0 and LOCAL_UI_VIVADO_SYNTHESIS_PASS, utilization report and timing report all present. Hash before/after synthesis proves the controller did not change RTL. The synthesis step is controller-orchestrated, not a separate model-authored Tcl/MCP call or synthesis-error repair loop.

Utilization: 123 Slice LUTs, 178 Slice Registers, 0 BRAM tiles, 0 DSPs. A 10 ns aclk clock is declared for report generation; I/O delays are unconstrained. Timing report is REPORT_ONLY, **not timing closure**. No implementation, bitstream, FPGA programming, full-board hardware validation or arbitrary-project control is claimed.

62 unit tests PASS, including trusted synthesis command/sandbox arguments and rejection of zero exit without the terminal marker/reports. Targeted kernel audit found no matching new faults. Formal model unchanged. No protected stack, package, driver, firmware or license modification; T7 not accessed. Real UI long-job cancellation and other models' use of this new mode remain NOT_TESTED.

Raw logs stay under output/local-ui/20261016T115526-418a2f. Git-view log/report formatting removes only trailing whitespace; original/curated SHA256 values are in curated-log-normalization.json. Sources and model trace are copied verbatim. Build caches and generated simulator binaries are excluded.
