# Local Model Lab protocol

## Practical comparison requested after the CPU reference cohort

The user's current objective is to select the model that completes FPGA engineering tasks most reliably and quickly on this workstation. CPU-only is no longer a requirement for this new comparison. The historical CPU cohorts below retain their original controls and outcomes.

`scripts/run_local_model_lab_practical.py` reuses the existing M13 Local Agent, Ross tools, task seeds, fixed testbenches and sandbox. It measures CPU, ROCm and Vulkan configurations sequentially, then selects the fastest successfully measured configuration for each available roster model. Each GPU configuration first completes a partial-offload probe before full offload is attempted. Backend choice is based on a declared throughput proxy, `512 / prompt_tokens_per_second + 128 / generation_tokens_per_second`; this is a selection heuristic, not an engineering task result or proof of a globally optimal configuration.

- All OS-available logical CPUs are available to inference; the current machine supplies 24 threads. No four-core affinity or process-memory cap is imposed.
- Each measured final configuration uses three throughput repetitions. Partial GPU probes are readiness gates and are excluded from performance ranking.
- Engineering context is 16,384 tokens with a 2,048-token completion budget, the same task timeout/tool-call caps for every model, and the same A1 → B1 → B2 → A2 → A3 → B3 order. This is a new cohort, separate from the earlier 8,192-token CPU reference.
- T1/T2/T3 specifications, baseline bugs and fixed testbenches are unchanged. T1/T2 successful agent trials additionally undergo independent Vivado synthesis of the model-authored final sources. This post-agent synthesis does not imply the model autonomously diagnosed synthesis errors or achieved implementation/timing closure.
- Temporary test-model loads are declared. The production Qwen is unloaded before starting test models, one large model runs at a time, and the original Lemonade model/runtime configuration is restored and checked in `finally`. No `--save-options` or formal Agent model-setting change is used.
- Runtime launch settings, backend calibration JSON, actual offload evidence, model-load time, per-trial ledgers and tool/model/Ross traces are saved. CPU/GPU selection is reported explicitly; no silent fallback is counted as GPU PASS.
- Host memory, swap growth and targeted kernel fault guards remain active. A serious GPU/kernel fault stops the experiment. Missing models are recorded without downloading replacements.
- A malformed patch now receives structured correction feedback and enables the existing exact model-authored replacement tool where that task permits it. Failure traces preserve the submitted arguments. These common harness changes apply to every model and do not alter RTL solutions or testbench checks.

Run the practical comparison with existing resources:

```bash
python3 -u scripts/run_local_model_lab_practical.py
```

Raw output goes to `output/LOCAL_MODEL_LAB_PRACTICAL/<actual-run-id>/`. Historical Qwen/Gemma CPU results are references only; the new ranking must use the new complete cohorts, include all failures, and keep task-specific timing separate.

## Historical CPU reference protocol

The Lab compares local model artifacts on the M13 engineering tasks without changing the production Agent model. It reuses the fixed T1 Basic RTL Repair, T2 Multi-file RTL Engineering, and T3 Vitis HLS Engineering source, testbench, validator, Ross tools, and isolated-workspace policy.

## Fixed controls

- Five roster entries are in [`../../config/local_model_lab.json`](../../config/local_model_lab.json). A model must exist locally and be the model already active in a loopback llama.cpp server before a test can run.
- No model download, server start/stop, model hot swap, formal Agent setting change, cloud provider, or concurrent large-model load is performed by the runner. Any separately authorized manual model-load experiment is outside the runner's fixed-protocol guarantee; it must be labeled exploratory if it conflicts with the no-switch restriction, and must preserve the original launch/configuration record and verify restoration. Such a run must not be presented as an acceptance-grade controlled cohort.
- CPU is the engineering comparison backend. The active server must report the exact model path and launch with context 8192, 24 threads, 24 batch threads, and zero GPU layers. The settings are checked before a run.
- The interleaved order is A1 → B1 → B2 → A2 → A3 → B3, with three trials per arm. Each trial has a fresh workspace from the same seed.
- Per-task timeouts, completion-token caps, tool-call caps and validation caps are fixed in the JSON config and passed to the existing M13 runners. Patch cap remains enforced by Local Agent policy.
- The resource guard stops a trial if `MemAvailable` falls below `max(6 GiB, 12.5% of OS-visible RAM)` or swap grows by more than 2 GiB from that trial's baseline. Only one large model may be loaded.
- Ross runs require an explicitly configured local AMD Knowledge Base endpoint. Skill and MCP calls are traced. Non-Ross trials remove the Ross endpoint.
- Failures/timeouts remain in the ledger. Success-rate denominators include all attempted trials. Completion latency is calculated only from passing trials; P90 is reported only with at least three successes and is exploratory at this sample size.
- Model-load duration is `NOT_INSTRUMENTED`: the Lab refuses to load models and requires the selected model to be active before starting. Token, tool, XSim/HLS, source SHA256 and resource details remain per-trial evidence.

## Usage

Inventory only (no model load or inference):

```bash
python3 scripts/run_local_model_lab.py inventory
```

Rehash listed local candidate files sequentially:

```bash
python3 scripts/run_local_model_lab.py inventory --full-hash
```

Verify that Qwen3.8 Q4_K_XL is already active through Lemonade and matches the fixed CPU/context/thread profile:

```bash
python3 scripts/run_local_model_lab.py preflight qwen38
```

Run the complete T1/T2/T3 A/B cohorts only after the selected model is already active and the local Ross endpoint is available:

```bash
python3 scripts/run_local_model_lab.py run qwen38
```

The runner never starts or stops a model server. It reads Lemonade's loaded-model health response rather than its stale model registry, then verifies the backing `llama-server` process, model path, SHA256, context, thread count, and CPU-only setting. It fails closed on a mismatch or missing local Ross endpoint. Results go to a unique ignored `output/LOCAL_MODEL_LAB/<run-id>/` directory; only reviewed, bounded evidence and reports belong in Git.
