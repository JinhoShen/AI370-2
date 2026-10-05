# Local Model FPGA engineering test

This is an isolated, synthesis-only sandbox for testing whether the local Qwen3.8 model can modify an existing FPGA design from a written change request and respond to Vivado tool feedback.

- No M11/M12 source, project, reports, bitstream or Golden evidence is edited.
- FPGA target for synthesis: `xc7s100fgga676-2`; no board I/O, implementation, bitstream, JTAG or programming is used.
- Baseline is a deterministic AXI4-Lite register block with input, control, result and offset registers. Original operation returns bitwise NOT of input.
- Local Model's requested change is in `docs/M13/evidence/local-model-fpga-engineering-2026-10-05/task_spec.md`.
- `src/local_model_axi_lite.v` now contains the reviewed Qwen3.8-27B-UD-Q4_K_XL model-produced change. The untouched baseline is preserved in `docs/M13/evidence/local-model-fpga-engineering-2026-10-05/original/`.
- `sim/tb_local_model_axi_lite.sv` provides an independent functional oracle. Without a plusarg it checks the legacy operation; `TEST_NEW_MODE` checks addition/offset, returning to legacy mode, and 32-bit wraparound.
- Vivado build products and generated project files belong under ignored `output/M13/Local_AI_FPGA_Engineering_Test/`.

Only Codex may run Vivado, XSim, or shell commands. The Local Model received the spec and source as prompt text and returned unified diff text; it had no tool or shell access. The selected patch passed XSim and synthesis, but no implementation, bitstream, or physical test was run. Candidate failures and the retained stop checkpoint are documented under `docs/M13/evidence/local-model-fpga-engineering-2026-10-05/`.
