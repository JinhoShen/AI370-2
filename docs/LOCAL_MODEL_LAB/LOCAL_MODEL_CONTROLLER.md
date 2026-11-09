# AI370 local-model controller

`scripts/local_model_controller.py` is the one long-running controller for the quality-evaluation workflow. It owns controller state, health telemetry, arm commands, and the child quality runner. The existing `run_quality_pilot.py` remains responsible for frozen-corpus preflight, model loading, task execution, validators, and per-sample safety guards.

## Safety model

- Startup mode is `MONITORING`: it only records RAM, Swap, `pswpin`/`pswpout`, memory PSI, and current per-process `VmSwap`.
- It permits only one owned child runner and takes an advisory lock to prevent two controllers from running.
- An `ARM_PILOT` request has a unique ID and explicit approval. The controller records it once, so it does not relaunch after service restart.
- It will not rerun a Pilot when `output/QUALITY_MODEL_VALIDATION/status.json` says `PILOT_COMPLETE`. After a documented remediation it reports `PILOT_REMEDIATION_READY`; otherwise it reports `WAITING_FOR_REVIEW`.
- `STOP` creates the runner stop marker and interrupts only the controller-owned runner process group. It does not stop desktop, embedding, or other services.
- A controller safety stop is carried in a dedicated sidecar before the runner is interrupted. This keeps `SAFETY_STOP` distinct from a user stop or Ctrl+C in the session report.
- `RUN_REMEDIATION_FIXTURES` runs post-Pilot unit and frozen-corpus fixtures without loading a candidate model. The controller applies its RAM, Swap, and PSI stop limits to this child process.
- Per-sample guards classify small swap-out activity as `WARN` evidence. It becomes a runtime stop only with corroborating pressure (sustained low available RAM, sustained high PSI, swap-in plus substantial swap-out), a 64 MiB swap-growth limit, a model-server failure, or a kernel/OOM/GPU fault.
- After a runtime `SAFETY_STOP`, the controller writes a read-only diagnosis. It distinguishes confirmed measurements from an unknown swap source and does not retry automatically.
- It never edits model configuration, corpus, scoring, prompts, or formal Agent settings.

## Commands

Run once interactively for a foreground controller:

```bash
python3 scripts/local_model_controller.py serve
```

Read current controller state:

```bash
python3 scripts/local_model_controller.py status
```

Arm a new Pilot only when the quality state permits it:

```bash
python3 scripts/local_model_controller.py arm-pilot --request-id pilot-YYYYMMDD-01
```

Request a clean stop:

```bash
python3 scripts/local_model_controller.py stop --request-id stop-YYYYMMDD-01
```

Run post-Pilot remediation fixtures:

```bash
python3 scripts/local_model_controller.py run-remediation-fixtures --request-id remediation-YYYYMMDD-01
```

For persistent operation, copy `scripts/ai370-local-model-controller.service` to `~/.config/systemd/user/`, then run `systemctl --user daemon-reload` and `systemctl --user enable --now ai370-local-model-controller.service`.

Live files are written under `output/LOCAL_MODEL_CONTROLLER/`:

- `status.json`: current controller state and most recent health sample.
- `telemetry.jsonl`: append-only health history.
- `events.jsonl`: append-only controller events.
- `command.json`: last durable command.
- `runner-<request-id>.log`: owned runner stdout/stderr.
- `diagnostics/<timestamp>/safety-stop-diagnosis.json`: evidence-bounded post-stop diagnosis, when a runtime safety stop occurs.

The controller does not launch another 216-sample cycle. It launches V2/V3 only after a reviewed runner plan that carries forward frozen V1 evidence without rerunning or overwriting it.

After a remediation fixture passes and the controller freezes that reviewed V2/V3 plan, it automatically launches exactly one V2/V3 matrix: 9 models × 8 tasks × 2 variants. It first runs the existing five-minute read-only preflight. A preflight block or runtime safety gate stops the controller-owned work and preserves the evidence; it does not retry automatically.
