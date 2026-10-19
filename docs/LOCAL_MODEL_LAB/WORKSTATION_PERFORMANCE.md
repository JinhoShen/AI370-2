# Workstation model performance — 2026-10-19

**RUNNING, incomplete.** User clarified that the objective is practical machine/model performance, without unnecessarily conservative CPU/RAM limits. This supersedes the previous execution order of repeating small engineering tasks first; original tasks/results remain unchanged.

## Measure useful performance

- Four current local model artifacts, full integrity verification, no downloads or new registrations.
- Speed first for every model: CPU with all available logical threads, Vulkan, and ROCm/HIP if a bounded partial-offload probe succeeds. Same 4K context, 512 input tokens and 128 output tokens, three measurements each, plus separate readiness smoke. Full GPU offload is proven from logs, never inferred from command flags alone.
- Record actual prompt/generation tokens per second, TTFT, request latency, load latency, backend/device/layers, threads, context, GPU busy, whole-device VRAM/GTT, process RSS, host memory/swap, paging rate and memory PSI.
- Model-specific tokenization provides the fixed input token count from the same repeated engineering-prose source. Token sequences/text prefixes can differ by tokenizer; retained requests show actual tokens and measured token counts. This is system throughput measurement, not answer-quality grading.
- Then take each model's observed safe speed winner through 8K/16K/32K context allocations, with 2K/4K/8K tested inputs and 256 generated tokens, three repetitions. Allocated context is not claimed as a fully tested input length. 32K is this initial matrix's upper point, **not a proven maximum hardware/model capacity**. A failed level stops larger levels for that profile.
- If the selected backend safely passed 16K, validate the actual Ross engineering workflow: fixed T1/T2/T3, three independent Ross trials each, model-authored repairs, independent XSim/HLS/Vivado markers. No Golden project is modified; no FPGA is programmed.
- Repeat cycles until user stop or a genuine safety gate. A previously pressure-blocked model/backend/context/layer profile is excluded from repeated pressure within the session. All failures, unsupported configurations and skipped exclusions are retained.

CPU/RAM utilization is not the acceptance target. GPU-bound decode, memory-bandwidth limits and a small RTL design can leave CPU/RAM headroom. No dummy RAM filling or unrelated synthetic load is added merely to raise percentages. CPUs are not restricted to four threads; no package/kernel/governor/driver/firmware tuning occurs.

## Updated resource policy

The old **64 MiB absolute swap-growth stop** is not used by the performance monitor. Small background swap changes are recorded, not automatically treated as model failure. Instead:

- Emergency MemAvailable below 1 GiB stops immediately.
- MemAvailable below max(2 GiB, 5% of OS-visible RAM) for 5 seconds stops.
- Sustained swap-out of at least 32 MiB/s for 10 seconds stops.
- Severe memory PSI with sustained low available memory stops.
- Matching GPU/kernel/OOM fault or unreadable kernel audit stops the relevant execution; severe kernel/stack gates stop the controller and do not reload the formal GPU profile.
- Disk free below 20 GiB, finite load/request/tool/profile deadlines and one large resident model remain guarded.

These are operational guards, not a guarantee that an OS/driver failure is impossible. The unchanged legacy engineering trial functions retain their own bounded resource/attempt/timeout rules; engineering limits are not silently relaxed to obtain PASS.

## Record and operate

Actual session: `output/HARDWARE_MODEL_PERFORMANCE/20261019T164651+0800/`.
Live state shared with UI: `output/model-endurance/status.json`.
UI: http://127.0.0.1:13306/ — shows current model/profile; stop button requests stop and formal-model restoration.

```bash
systemctl --user status ai370-model-evaluation.service
systemctl --user stop ai370-model-evaluation.service
```

Every configuration retains exact commands/profile, requests, raw SSE, three per-request timing records, load/offload logs, resource samples and kernel audit. `results.jsonl` and `summary.json` are updated after each case, with per-case checksums. Source/runtime/package snapshots and full model hashes are retained. No credentials/model binaries/cache trees are committed. Formal saved recipes remain unchanged; an orderly stop restores explicit Qwen ENGINEERING arguments and verifies them. No automatic restart after service failure or reboot is enabled.

Pure speed ranking is per fixed workload. Capacity and engineering success are separate columns; failed cases are not silently removed, and an unfinished matrix is not a universal winner or high-load stability PASS. Current loop measures the best observed backend at default measured batch/FA/f16 KV settings; a complete batch/KV/FA or thread-count sweep is **NOT YET EXECUTED**. Do not call those optimizations complete.

## Preserved transition

The previous UD Q4_K_M Non-Ross A1 repair passed, followed by a controller checksum variable-shadowing failure. The correction and independently verified original result are retained; its total wall duration stays UNKNOWN.

Under the corrected runner, UD Q4_K_M T1 Ross B1 completed PASS in 320.058 seconds including independent synthesis; whole-device GPU busy peaked at 100%. The bounded engineering cohort then received the controlled transition stop requested by the developer under the user's performance-direction change. A newly started T2 A1 was recorded CANCELLED rather than counted as model failure or PASS. Formal restoration PASS at 16:44:51 +08:00. These results are retained, not rerun as new samples.

Performance session started at 16:46:51 +08:00. First active case: UD Q4_K_M / Vulkan / 4K / 512 input / 128 output. One preliminary measured request showed 105.65 prompt tokens/s and 4.98 generation tokens/s, with ~30.37 seconds latency; **this one request is not a three-run average or final recommendation**. During this case a recorded sample showed GPU 99%, no swap-out and ~40 GiB OS-available RAM. Final per-case ledger takes precedence.

Framework checks: 72 unit tests PASS at startup. They test the policy, configuration generation and severe-fault classification; they are not substitutes for actual model performance results. No GPU fault is deliberately injected.

## First complete speed case — actual 2026-10-19

UD Q4_K_M Vulkan 4K/512-input/128-output completed all three measurements PASS. Median prefill **105.91 tokens/s**, generation **4.98 tokens/s**, request latency **30.32 seconds**. Kernel audit clean, no pressure guard. This is a measured initial profile, not a final machine/model winner. The runner continued to the full-24-thread CPU comparison. [Retained per-request results/resources](evidence/hardware-performance-2026-10-19/first-vulkan-case/README.md).
