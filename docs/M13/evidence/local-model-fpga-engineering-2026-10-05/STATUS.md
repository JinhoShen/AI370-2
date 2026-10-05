# Local Model FPGA Engineering Test — Current Status

Date: 2026-10-05

## Verdict

`LOCAL_MODEL_FPGA_ENGINEERING_PASS — bounded supervised patch workflow, Qwen3.8-27B-UD-Q4_K_XL CPU candidate`.

This is a synthesis-only sandbox result. It does not establish autonomous end-to-end Ross/local-answer integration, implementation timing, bitstream generation, or SP701 hardware behavior. M13 overall remains IN PROGRESS.

## Verified candidate

Qwen3.8-27B-UD-Q4_K_XL produced a minimal conditional change using existing `control_reg[1]`, `input_reg`, and `offset_reg`. The model received the exact source, task contract, a prior patch-parser failure, and the correct hunk context/counts. Its patch passed `git apply --check`, was applied unchanged, and the modified source passed the sandbox testbench for add mode, legacy mode, and 32-bit overflow. Vivado 2026.1 synthesis then exited 0 for `xc7s100fgga676-2`.

The resulting source and complete raw model response, patch, verifier output, XSim transcript, Vivado log, utilization report, timing report, and checksums are preserved in this directory. No Codex-authored RTL correction was made.

## Candidate comparison

See [MODEL_RESIDENCY_COMPARISON.md](MODEL_RESIDENCY_COMPARISON.md). The selected Q4_K_XL run used CPU-only inference, all 24 threads, 4096 context, a 30 GiB memory cap, per-run swap disabled, and a 900-second timeout. Peak RSS was 19,585,876 KiB; swap use was 0. The test was model-assisted patch generation with verifier feedback, not an always-on server benchmark.

Qwen3.8-27B-UD-Q4_K_M remained unsuccessful after its bounded correction budget: generated patches had invalid hunk counts and were not applied. Qwen3.8 Uncensored Q4_K_M produced semantically plausible RTL but repeated malformed hunk counts after one parser-feedback correction. Qwen3.5-9B introduced conflicting duplicate register cases and repeated the issue after one correction. Neither failing candidate patch was applied.

## Scope boundaries and impact

- Only the isolated project `projects/FPGA/Local_AI_FPGA_Engineering_Test/` was changed.
- Functional XSim passed for the requested behavior.
- Vivado synthesis passed with 123 Slice LUTs and 178 Slice Registers.
- Synthesis timing report: WNS 6.316 ns, TNS 0 ns, against the sandbox's synthetic 100 MHz clock constraint. External input/output delays are absent; this is not board timing sign-off.
- Implementation, physical timing, bitstream generation, FPGA programming, JTAG, and hardware execution: NOT RUN.
- GPU/NPU inference was not used. Kernel, Mesa, ROCm, XRT, amdxdna, NPU firmware, and drivers were not changed.
- The earlier user-requested stop checkpoint is retained at [STOPPED_CHECKPOINT_2026-10-05.md](STOPPED_CHECKPOINT_2026-10-05.md); subsequent authorized work is recorded here without erasing that history.
