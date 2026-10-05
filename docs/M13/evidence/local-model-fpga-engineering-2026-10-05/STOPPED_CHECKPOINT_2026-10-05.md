# Local Model FPGA Engineering Test — Stopped Status

Date: 2026-10-05

## Verdict

`LOCAL_MODEL_FPGA_ENGINEERING_INCOMPLETE — STOPPED AT USER REQUEST`.
This is not a PASS or a model-failure verdict: the bounded correction cycle was
intentionally stopped before it was complete. No further model, simulator, or
Vivado test should be inferred from this record.

## Completed before stop

- Created the T7 deployment-kit skeleton at `/media/shen/T7/AI370-2/` with
  `README_FIRST.md`, `MASTER_MANIFEST.md`, `SHA256SUMS`, and the three requested
  top-level directories. The model directory contains `MODEL_MANIFEST.md`.
- This was a mapping-only setup. No existing T7 payload was copied, moved, or
  deleted. The `/media/shen/T7/照片` directory was not accessed.
- Created the isolated FPGA sandbox at
  `projects/FPGA/Local_AI_FPGA_Engineering_Test/`; no M11/M12 project was
  changed and no FPGA was programmed.
- The deterministic baseline completed Vivado synthesis and baseline XSim
  simulation successfully. These validate only the original behavior, not the
  requested Local Model change.
- Selected local model: `Qwen3.8-27B-UD-Q4_K_M.gguf`, CPU backend, context 4096.
  Inference was resource bounded (30 GiB memory limit, swap disabled for the
  inference scope, four CPU threads).

## Model-generated change and feedback

The task asked the model to add a mode in which control bit 1 makes the result
equal input plus configurable offset; otherwise the existing complement
operation remains. Its first response proposed the right behavior and supplied
a source diff, but the diff had an invalid hunk count. `git apply --check`
rejected it (`corrupt patch at line 15`), so it was never applied.

The first completed correction response received the exact parser error and
returned another malformed diff; `git apply --check` rejected that response as
well. A second bounded correction request was then interrupted at the user's
request. Its response is incomplete and was not evaluated or applied.

The sandbox RTL remains byte-identical to the saved original baseline. No
modified-source synthesis or new-mode simulation was run.

## Baseline-only implementation evidence

- Vivado synthesis: PASS for the unchanged baseline.
- Baseline XSim: PASS for legacy mode (`TEST_PASS baseline_and_selected_mode=0`).
- Baseline utilization: 56 Slice LUTs and 178 Slice Registers.
- Baseline timing report: WNS 7.359 ns, TNS 0 ns; the report says user timing
  constraints are met. This is a synthesis baseline under the sandbox's
  synthetic 100 MHz constraint, not board timing or post-route timing.
- FPGA implementation, bitstream, programming, and hardware behavior: NOT RUN.

## System impact

- No kernel, Mesa, ROCm, XRT, amdxdna, firmware, or driver changes were made.
- No GPU or NPU inference was run for this task.
- No FPGA programming was performed.
- A post-run kernel/GPU fault audit was not run.

## Resume boundary

Resume only when explicitly requested. The next test action, if authorized, is
to continue the same model correction request within the existing retry bound,
then review and validate any model-produced patch. Do not treat a Codex-authored
replacement patch as model success.
