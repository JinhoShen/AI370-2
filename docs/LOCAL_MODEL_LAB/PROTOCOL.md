# Local Model Lab protocol

The Lab compares local model artifacts on the M13 engineering tasks without changing the production Agent model. It reuses the fixed T1 Basic RTL Repair, T2 Multi-file RTL Engineering, and T3 Vitis HLS Engineering source, testbench, validator, Ross tools, and isolated-workspace policy.

## Fixed controls

- Five roster entries are in [`../../config/local_model_lab.json`](../../config/local_model_lab.json). A model must exist locally and be the model already active in a loopback llama.cpp server before a test can run.
- No model download, server start/stop, model hot swap, formal Agent setting change, cloud provider, or concurrent large-model load is performed by the runner.
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
