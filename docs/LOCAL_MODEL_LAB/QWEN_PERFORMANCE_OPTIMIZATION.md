# Qwen performance optimization — 2026-10-14

**Final status: PARTIAL_SAFE_PROFILES_READY.** Three conservative recommendations are ready for review and have **not** been applied. The original formal Qwen CPU service was restored with identical argv; real local API/Agent read-file readiness PASS. ROCm tuning stopped at a swap guard; omitted configurations are NOT_TESTED, not UNSUPPORTED or PASS.

## Phase 0 / baseline

The prior practical model comparison completed at `2026-10-13T21:48:31+08:00`; no T2/T3 process was active when this optimization began. Qwen completed T1/T2/T3, 18/18 PASS, with independent RTL synthesis and HLS verification. It was not interrupted or rerun. GPT-OSS and Devstral remain NOT_INSTALLED and the fifth roster slot unspecified. [Prior results](RESULT.md), [exact prior ledger](evidence/practical-2026-10-13/result.json).

This run started `2026-10-14T18:11:44.593425+08:00` and completed measurements/restoration `2026-10-14T18:25:08.985892+08:00`. Native raw evidence: `/home/shen/AI370-2/output/QWEN_PERFORMANCE_OPTIMIZATION/20261014T181144+0800`. [Curated measurements and restoration](evidence/qwen-performance-2026-10-14/result.json).

Only artifact: `/home/shen/AI370-2/resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf`; **17,559,178,144 bytes**; SHA256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` (**full rehash PASS**). Stat before/after hashing agrees. GGUF architecture `qwen35` / UD Q4_K_XL filename / Q4_K_M metadata label are from the prior verified metadata, not a newly invented model version.

CPU: AMD Ryzen AI 9 HX 370, 12 physical cores / 24 logical CPUs; all 24 available, boost enabled. Linux-visible RAM is 48,928,804 KiB (~46.7 GiB); user-reported installed physical RAM is 64 GB. These are separate quantities; this run does not infer a BIOS allocation explanation. GPU: Radeon 890M, ROCm0 / RADV GFX1150 Vulkan0. Kernel `6.17.0-14-generic`, ROCm core `7.2.1.70201-81~24.04`; exact packages/device lists are saved as baseline evidence. Lemonade `2026.39.1`; llama.cpp `0.5.0-dev`, commit `7fe450e19305b828c199d602c23a8337aaa1f03b`. No software updates.

Original formal service: Lemonade API `127.0.0.1:13305/api/v1`, CPU llama-server `127.0.0.1:8001`, Qwen XL, context 8192, threads/batch threads 24, GPU layers 0, parallel 1, reasoning off, draft-MTP. Exact argv is recorded in `original-runtime.json`. Manager stayed running; formal model was temporarily unloaded for sequential isolated tests at port 18082. Saved model settings/configuration were not changed.

## Controlled measurements

Fixed native completion prompt: 64 processed prompt tokens, exactly 32 requested/actual output tokens, temperature 0, seed 42, ignore EOS, prompt-cache reuse disabled. One four-token smoke precedes three measured repetitions per successful configuration. TTFT is measured from HTTP start to first nonempty streamed content. End-to-end means one inference HTTP request; model load is separately logged. Reported PP/TG are the server timings, not an inferred hardware peak. Medians are exploratory (n=3), not confidence intervals.

Only one main parameter changes relative to each anchor. CPU generation-thread changes retain batch threads 24. GPU-layer changes retain other settings. Vulkan anchor was the original full-offload 16K engineering configuration; ROCm anchor was full-offload 8K. The repeated 16K Vulkan context case is an unchanged control, not a tuning gain. No unmeasured combination of winning parameters is advertised. The formal baseline also has one diagnostic request, excluded from the three-repetition comparisons.

| Configuration | Result | PP tok/s | TG tok/s | TTFT s | Request s | Peak RSS MiB | Swap growth MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| cpu-24-mtp | PASS | 16.660 | 3.926 | 3.843 | 11.845 | 20828.0 | 0.00 |
| cpu-12-mtp | PASS | 16.784 | 3.923 | 3.817 | 11.718 | 20831.4 | 0.00 |
| cpu-18-mtp | PASS | 16.480 | 3.926 | 3.886 | 11.821 | 20829.6 | 0.00 |
| cpu-24-no-mtp | PASS | 16.787 | 3.376 | 3.815 | 12.931 | 19890.6 | 0.00 |
| vulkan-99 | PASS | 38.234 | 4.700 | 1.677 | 8.273 | 380.8 | 0.00 |
| vulkan-32 | PASS | 23.331 | 3.635 | 2.746 | 11.274 | 717.3 | 21.45 |
| hip-99 | PASS | 72.080 | 4.533 | 0.889 | 7.729 | 1287.4 | 0.00 |
| hip-32 | PASS | 40.158 | 3.453 | 1.596 | 10.574 | 9072.3 | 0.00 |
| engineering-vulkan-16384 | PASS | 38.311 | 4.700 | 1.673 | 8.269 | 380.4 | 0.00 |
| engineering-vulkan-16384-threads-12 | PASS | 38.110 | 4.698 | 1.683 | 8.281 | 380.9 | 0.00 |
| engineering-vulkan-16384-threads-18 | PASS | 37.912 | 4.700 | 1.691 | 8.286 | 381.0 | 0.00 |
| engineering-vulkan-16384-context-4096 | PASS | 37.648 | 4.622 | 1.702 | 8.409 | 380.2 | 0.00 |
| engineering-vulkan-16384-context-16384 | PASS | 38.092 | 4.702 | 1.682 | 8.271 | 381.5 | 0.00 |
| engineering-vulkan-16384-fa-on | PASS | 38.145 | 4.703 | 1.680 | 8.269 | 381.0 | 0.00 |
| engineering-vulkan-16384-fa-off | PASS | 37.708 | 4.574 | 1.699 | 8.479 | 391.2 | 0.00 |
| engineering-vulkan-16384-kv-k-q8 | PASS | 38.283 | 4.699 | 1.674 | 8.272 | 388.2 | 0.00 |
| engineering-vulkan-16384-kv-v-q8 | PASS | 37.943 | 4.699 | 1.690 | 8.283 | 388.0 | 0.00 |
| engineering-vulkan-16384-batch-1024 | PASS | 38.113 | 4.703 | 1.681 | 8.273 | 380.6 | 0.00 |
| engineering-vulkan-16384-ubatch-256 | PASS | 38.275 | 4.689 | 1.674 | 8.285 | 380.5 | 0.00 |
| hip-99-threads-12 | PASS | 72.133 | 4.566 | 0.889 | 7.680 | 1292.3 | 0.00 |
| hip-99-threads-18 | FAIL | — | — | — | — | 1088.2 | 70.92 |

Fastest measured CPU: `cpu-12-mtp`, 11.718 s. Its advantage over 24-thread MTP is only 1.07%; this is insufficient to claim a robust thread-count win. SAFE retains 24 threads. MTP materially helped this short request relative to CPU without MTP, but its effect depends on output/draft acceptance.
Fastest measured Vulkan: `engineering-vulkan-16384-fa-on`, 8.269 s. Most changes were within measurement noise; FA off was slower. FAST retains auto FA and full offload, rather than claiming marginal parameter differences as optimization.
Fastest measured ROCm: `hip-99-threads-12`, 7.680 s. This is the fastest **measured short inference**, not an established engineering or residency winner.

Context 4K/8K/16K tests measured allocation plus the same short input; they do not prove performance or stability at full context occupancy. A 64-token prompt does not exercise batch limits 1024/2048 or micro-batch limits 256/512, so no large-prompt batch-speed conclusion follows. Q8 K or V cache actually reduced the 16K attention KV allocation from 1024 MiB to 784 MiB, but quality/task success with quantized KV is NOT_TESTED; recommended profiles retain f16. These tests were supported by the installed build; no unavailable configuration was fabricated.

## Safety / failure evidence

Whole-host swap was already about 6.6–6.7 GiB occupied before tests. Existing occupancy was not reset or used as a speed claim. Resource samples include RSS, host available RAM, swap occupancy and pswpin/pswpout; GPU DRM allocation and sampled GPU busy are separate. GPU process RSS excludes VRAM/GTT and must not be called total model memory.

ROCm 18-thread load was stopped before measured repetitions: available memory remained 24.97 GiB, but swap growth was **70.92 MiB** and host swapout **69.84 MiB**, exceeding the conservative 64 MiB guard. Status **FAIL_RESOURCE_GUARD**; no throughput is assigned. This temporal observation does not prove the thread count itself caused eviction. No retry or further ROCm load was attempted.

ROCm context, FA, KV, batch/micro-batch tuning after that gate: **NOT_TESTED / safety-deferred**. No driver/device-lost/OOM/kernel fault was observed during this run; this is bounded smoke evidence, not high-load or long-duration stability PASS. All package versions and original formal argv compare identical after the run. No FPGA programming, protected-stack edits, model downloads, formal-profile promotion or GitHub push.

A verifier false negative initially labelled four successful GPU measurements FAIL because a truncated display excerpt omitted earlier offload lines. The original classifications/raw logs are preserved in `initial-stage-result.json` and per-configuration ledgers. Corrected master rows retain `initial_verifier_status` and `classification_correction`: full logs prove offloaded layers, Vulkan DRM compute counters increase, HIP has allocated GTT and nonzero GPU activity. KFD compute-counter exposure is unavailable here; no zero-counter CPU-fallback claim is made. Metrics were not rerun or rewritten. The guarded ROCm failure remains a real excluded trial.

## Recommendations — not applied

| Profile | Backend / device | Threads / batch threads | GPU layers | Context | Batch / micro-batch | FA / KV | Short request median | Evidence / risk |
|---|---|---|---|---:|---|---|---:|---|
| FAST | Vulkan / Vulkan0 | 24 / 24 | 99 requested; 66/66 logged | 8192 | 2048 / 512 | auto / f16 K+V | 8.273 s; PP 38.23, TG 4.70 | 3/3 inference; about 30.2% lower request time vs CPU24 MTP; no long-duration claim |
| ENGINEERING | Vulkan / Vulkan0 | 24 / 24 | 99 requested; 66/66 logged | 16384 | 2048 / 512 | auto / f16 K+V | 8.269 s; PP 38.31, TG 4.70 | Prior same configuration 18/18 T1/T2/T3; no new whole cohort |
| SAFE | CPU | 24 / 24 | 0 | 8192 | 2048 / 512 | auto / f16 K+V; draft-MTP | 11.845 s; PP 16.66, TG 3.93 | Original formal profile; 3/3 inference and restored Agent read-file PASS |

ROCm is kept as a measured faster candidate, **not a recommended default** while its repeated-load swap gate is unresolved. FAST and ENGINEERING prioritize the established Vulkan engineering evidence; SAFE remains the live configuration. Profiles are proposed parameter sets, not newly installed services.

Profile resources (sampled RSS is not GPU allocation):
- FAST: RSS peak 380.8 MiB; available RAM minimum 39.91 GiB; swap peak 6.64 GiB (pre-existing), growth 0.00 MiB, swapout 0.00 MiB; mean sampled GPU busy 81.5%. DRM at end: VRAM 15723456 KiB, GTT 1965532 KiB.
- ENGINEERING: RSS peak 380.4 MiB; available RAM minimum 39.46 GiB; swap peak 6.65 GiB (pre-existing), growth 0.00 MiB, swapout 0.00 MiB; mean sampled GPU busy 80.3%. DRM at end: VRAM 15731652 KiB, GTT 2498012 KiB.
- SAFE: RSS peak 20828.0 MiB; available RAM minimum 37.91 GiB; swap peak 6.64 GiB (pre-existing), growth 0.00 MiB, swapout 0.00 MiB; mean sampled GPU busy 0.0%. DRM at end: CPU only.

## Engineering validation / recovery

Reuse is explicit: frozen prior Qwen T1/T2/T3 tasks, same XL model/hash, Vulkan full offload, 24 threads, 16K context, default batch/micro-batch 2048/512, f16 caches and auto FA. Current Local Agent/task-runner source hashes match the archived executed harness. Each A/B arm has three trials; testbench and task acceptance were not changed. T1/T2 passed XSim plus independent synthesis; T3 passed C simulation plus HLS synthesis. Ross Skill reads and real local KB MCP calls are retained in the prior traces; no Codex-authored answer was substituted.

| Qwen task | Non-Ross PASS / mean seconds | Ross PASS / mean seconds |
|---|---|---|
| T1 | 3/3 / 172.70 | 3/3 / 274.66 |
| T2 | 3/3 / 551.46 | 3/3 / 508.38 |
| T3 | 3/3 / 169.28 | 3/3 / 217.64 |

These are **reused prior engineering measurements**, not fresh CPU-versus-GPU task trials. No engineering success claim is made for new ROCm, quantized KV or reduced-thread settings. No new task benchmark was required for the selected unchanged ENGINEERING candidate.

Recovery: owned temporary model processes stopped; saved formal Lemonade CPU load parameters restored without `--save-options`; actual argv equality PASS and API model enumeration PASS. A fresh Local Agent used the restored loopback Qwen provider, actually called `read_file` on an isolated file and returned `AI370_QWEN_RESTORE_OK` (**PASS**). No Codex runtime/cloud API was involved. [Readiness trace](evidence/qwen-performance-2026-10-14/formal-agent-readiness/trace.jsonl).

## Open items / reproducibility

- ROCm tuning after its safety gate remains deferred; causes of whole-host swap eviction were not diagnosed by changing system policy.
- Long-input batch tuning, full-context occupancy, long-duration stability and quantized-KV engineering accuracy remain NOT_TESTED; no extrapolated global optimum.
- Three repetitions and fixed sequential order provide bounded exploratory results, not a statistical guarantee.
- Full raw server transcripts remain in output; committed excerpts plus SSE/results/resources/commands are checksum-covered. Initial harness snapshot and current source are saved; the intermediate continuation harness was not separately frozen per process. This provenance limit does not erase raw commands/results.
- Original formal profile is unchanged; user review is required before adopting any recommendation.

Re-run command: `python3 scripts/optimize_qwen_performance.py` (temporarily unloads/restores this exact recorded formal profile). Uses existing binaries and only loopback inference. Resource guards refuse low memory, material swapout/growth and unreadable/faulting kernel audit. Read commands/config before use on a different workstation; it is not a universal new-machine profile.

Tests: Python syntax, 20 Local Agent tests, 7 Model Lab tests, 2 practical lifecycle/restoration tests, 4 performance/SSE/offload tests; actual measurement/restoration/readiness evidence above. `git diff --check` and evidence checksum verification recorded separately at commit time.
