# AI370-2 Local Model Lab — current result

## Current 2026-10-19 run — workstation performance

**RUNNING / incomplete.** The user reprioritized throughput/capacity, replacing the pure repeated-engineering execution order. See [performance protocol, actual state and evidence](WORKSTATION_PERFORMANCE.md). Older complete Qwen/Gemma cohorts and the later partial four-variant engineering loop remain distinct historical records; no completed four-model performance ranking is claimed yet.


## 2026-10-19 continuous evaluation — RUNNING

User-authorized repeating four-model T1/T2/T3 Ross/Non-Ross cohorts until stopped. Evidence/progress is under `output/model-endurance/`; the UI shows the active model and supports stop. Current initial case: Qwen3.8 UD Q4_K_M, Vulkan 66/66 offload, T1 Non-Ross A1. Full integrity/readiness passed; no completed engineering result is claimed by this startup record. The previous Gemma UI Vulkan gate remains; this run tests a separately declared CPU profile. [Protocol, evidence format and stop/recovery policy](CONTINUOUS_EVALUATION.md). Older completed benchmark results below remain historical and unchanged.


## Completed practical cohort — actual 2026-10-13

Execution completed `2026-10-13T21:48:31+08:00`; formal Qwen service restoration **PASS**. Both available models completed **18/18** task trials. T1/T2 also passed 12 independent syntheses per model; T3 passed real HLS C simulation and synthesis. Missing GPT-OSS/Devstral and the unspecified fifth slot keep the overall five-model inventory **PARTIAL**.

| Model | Task | Non-Ross PASS | Non-Ross mean seconds | Ross PASS | Ross mean seconds | Ross time improvement |
|---|---|---|---:|---|---:|---:|
| gemma4_31b | T1 | 3/3 | 159.28 | 3/3 | 230.83 | -44.92% |
| gemma4_31b | T2 | 3/3 | 503.11 | 3/3 | 706.40 | -40.41% |
| gemma4_31b | T3 | 3/3 | 144.73 | 3/3 | 183.12 | -26.52% |
| qwen38 | T1 | 3/3 | 172.70 | 3/3 | 274.66 | -59.04% |
| qwen38 | T2 | 3/3 | 551.46 | 3/3 | 508.38 | +7.81% |
| qwen38 | T3 | 3/3 | 169.28 | 3/3 | 217.64 | -28.56% |

Both used measured Vulkan full layer offload, 24 threads, context 16,384, the same frozen harness/task corpus and three repetitions per arm. Gemma was faster on T1/T3; Qwen was faster for Ross-assisted T2. Equal success rates and only three observations per arm do not establish a universal model winner. Ross adds retrieval/prompt work and did not improve every task. Raw/normalized failures and the earlier harness-invalid pilot remain separate historical evidence.

Evidence: [practical cohort](evidence/practical-2026-10-13/result.json). Complete raw workspaces: `output/LOCAL_MODEL_LAB_PRACTICAL/20261013T182657+0800`. Measured GPU allocations/compute counters are in the result. Microbench selection is a short-workload heuristic, not exhaustive tuning.

Qwen performance optimization is a separate follow-up; no formal configuration has been promoted.


The preparation pilot `20261013T173115+0800` completed Gemma T1 with six XSim PASS and six independent Vivado synthesis PASS. Its T2 exposed an executor compatibility defect: ordinary unified-diff file labels (`--- rtl/...`, `+++ rtl/...`) were rejected because the parser required Git `a/` and `b/` labels. That pilot was stopped and its formal Qwen model was restored (actual restoration PASS). Its interrupted T2 is **HARNESS_INVALID / NOT A MODEL FAILURE**. Pilot calibration remains valid and is explicitly reused after this harness-only correction; pilot engineering timings are excluded from the new ranking.

The corrected common executor normalizes only path labels and diff context/counts, matches model-authored old-text hunks against unique exact source regions, and applies the model's added/removed source text unchanged. It rejects ambiguous hunks, disallowed paths, new files, deletes and testbench edits. Both raw and applied patches are recorded. Unit tests verify this behavior; the final verdict still requires actual XSim/HLS and, for successful RTL trials, independent synthesis. This corrects a shared tool compatibility problem rather than supplying a model solution.

## Qwen optimization follow-up — actual 2026-10-14

**PARTIAL_SAFE_PROFILES_READY**: 20 configurations completed three short measurements each; one ROCm 18-thread load stopped at the swap guard (no throughput assigned). FAST Vulkan 8K, ENGINEERING Vulkan 16K (reused 18/18 engineering evidence), SAFE original CPU24 MTP are proposed and not applied. Formal argv/API/Local Agent restored and verified; no new kernel fault. [Full optimization report](QWEN_PERFORMANCE_OPTIMIZATION.md).

## Historical CPU reference results

**Status: PARTIAL.** Phase 0 inventory, Phase 1 guarded runner, the Qwen3.8 reference cohort (reused from M13), and a new Gemma 4 T1/T2/T3 CPU A/B cohort are complete. Gemma passed all six T3 HLS trials, but all T1 and T2 trials failed. GPT-OSS 20B and Devstral Small 2 are not installed and the fifth slot is unspecified, so the five-model comparison is incomplete. The original Qwen3.8 Lemonade configuration has been restored and health-checked.

## Model inventory

| Roster model | Local artifact | Current status | Integrity / metadata |
|---|---|---|---|
| Qwen3.8-27B | `Qwen3.8-27B-UD-Q4_K_XL.gguf` (17,559,178,144 bytes) | ACTIVE; current CPU smoke PASS | SHA256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`, matches current full hash and M15 metadata inventory; architecture `qwen35`, 27.32B parameters, Q4_K_M metadata label |
| GPT-OSS 20B | Not found in the Local AI resource tree | NOT_INSTALLED; no download attempted | No file/hash/metadata |
| Devstral Small 2 24B | Not found in the Local AI resource tree | NOT_INSTALLED; no download attempted | No file/hash/metadata |
| Gemma 4 31B | `gemma-4-31b-jang-crack-Q4_K_M.gguf` (18,687,057,344 bytes) | PRESENT; this turn's bounded CPU T1/T2/T3 A/B cohort complete; formal Qwen service restored afterward | SHA256 `b1fc8ee10f916da019dbb1d177854fa3b6421fbea1e93839a2061861308e1de7`, matches current full hash and M15 record; architecture `gemma4`, 30.697B parameter elements, Q4_K_M |
| RESERVED | No selection supplied | WAITING_FOR_MODEL_SELECTION | Unknown |

Two more Qwen3.8 files are present outside the five-slot roster: UD Q4_K_M, 16,464,440,224 bytes, SHA256 `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`; and Uncensored Q4_K_M, 16,810,714,528 bytes, SHA256 `4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675`. Both match the previous verified model inventory, but are not loaded for this run. The two Qwen3.6 models and their mmproj are present but retired from this roster; their known Q8 Vulkan issue remains M7.1 OPEN and they were not tested.

A Qwen3-14B GGUF also appears as a member of the existing 18.2 GB Lemonade cache tar, not as a direct GGUF file. It is outside this five-model roster and was not extracted or tested.

## Backend and resource precheck

- Hardware-visible CPU: AMD Ryzen AI 9 HX 370, 24 logical CPUs. Linux currently exposes 48,928,804 KiB (about 46.7 GiB) to processes; this read-only check does not establish the physical DIMM total. Swap is 8 GiB total with about 5.5 GiB already occupied. The active inference server uses 24 threads and 24 batch threads; this Lab does not impose a 4-core cap.
- Active backend: Lemonade loopback API `127.0.0.1:13305/api/v1` backed by llama.cpp `0.5.0-dev` commit `7fe450e19305b828c199d602c23a8337aaa1f03b`, Qwen3.8 Q4_K_XL, `--ctx-size 8192 --n-gpu-layers 0`, backend URL `127.0.0.1:8001`. Device is CPU; no GPU/NPU offload or fallback ambiguity.
- `llama-cli --list-devices` enumerated CPU build with no accelerator device, Vulkan build with `Vulkan0: AMD Radeon 890M Graphics (RADV GFX1150)`, and HIP build with `ROCm0: AMD Radeon 890M Graphics`. These are backend-readiness results, not model inference results for this Lab.
- Before the bounded smoke, `MemAvailable` was about 30.2 GiB. Afterward it was about 30.2 GiB and swap did not materially change. The current Qwen server already occupies about 25 GiB RSS; starting a second 27–31B model would violate the one-large-model rule and approach the resource guard.
- The generic GGUF metadata parser could not run under system Python because NumPy is absent. No package was installed. For files with prior M15 metadata evidence, that committed parse result was used; it explicitly says tensor payloads were not validated. GPT-OSS/Devstral remain unknown because their artifacts are absent.

Phase 1 also found a result-label bug: Local Agent's final gate did not count the `--multi-file-xsim` profile as a verification mode, so completed T2 tool loops could print `COMPLETED` even when the fixed XSim marker existed. The gate now includes that profile. Historical T2 rows are normalized from the saved model patch count and actual XSim pass marker; no old test result was changed. Local Agent policy tests now pass 17/17.

## Phase 2 smoke

New current smoke: `Qwen3.8-27B-UD-Q4_K_XL.gguf` returned exactly `READY` through the existing Lemonade API and active CPU llama.cpp backend, with a 17-token prompt and 2 generated tokens. HTTP 200; elapsed 0.957 s. This was a tiny smoke, not a benchmark or stress test. See [`qwen38-xl-lemonade-smoke.json`](evidence/2026-10-13/qwen38-xl-lemonade-smoke.json) and the direct backend check in [`qwen38-xl-cpu-smoke.json`](evidence/2026-10-13/qwen38-xl-cpu-smoke.json).

Qwen3.8 Q4_K_M and Qwen3.8 Uncensored Q4_K_M have historical bounded CPU smoke PASS evidence under M7 with matching present-file SHA256. Gemma 4 additionally completed the new CPU engineering cohort below. The Gemma server used context 8192, 24 threads, zero GPU layers, one parallel slot; the original Qwen production configuration was restored after the cohort.

## Engineering results reused from M13

These are the formal Qwen3.8 Q4_K_XL CPU-backend A/B cohorts, not reruns in this Lab:

| Task | Non-Ross | Ross-assisted | Interpretation |
|---|---:|---:|---|
| T1 Basic RTL Repair | 3/3 PASS | 0/3 PASS | Ross calls occurred; Qwen produced malformed/truncated tool-call JSON |
| T2 Multi-file RTL Engineering, corrected controlled cohort | 3/3 PASS | 1/3 PASS | Two Ross trials exceeded the 8192-token context; B timing is not estimable from one success |
| T3 Vitis HLS source CSim/CSynth | 3/3 PASS | 3/3 PASS | Ross mean end-to-end time was 2.69% slower; only this task has balanced success for latency comparison |

Full token, timing, tool-call, source-hash, and resource data are in [the M13 benchmark report](../M13/M13_ROSS_AB_BENCHMARK_REPORT.md) and its curated evidence. The HLS task was C simulation and C synthesis only, not HLS implementation, timing closure, or physical FPGA execution.

The normalized M13 ledgers show tool-call result success (successful `result.ok` divided by all Local Agent `tool_call` events) of T1 A 80.0% / B 75.0%, T2 A 84.2% / B 86.5%, and T3 A 69.2% / B 77.4%. This event-level measure is not task success: for example, all three T1 Ross tasks still failed despite most tool calls returning successfully. T2 B2 and B3 show context overflow in the actual model traces.

Available per-model resource comparison is limited to the corrected T2 cohort; it is not a cross-model comparison:

| Arm | Mean peak process RSS | Minimum host MemAvailable | Maximum swap used | Mean machine-equivalent CPU |
|---|---:|---:|---:|---:|
| Non-Ross | 28,105.3 MiB | 28,311.8 MiB | 5,629.3 MiB | 96.7% |
| Ross | 27,768.9 MiB | 28,457.1 MiB | 5,629.2 MiB | 96.3% |

The model was already resident before each recorded task, so model-load duration was not captured. The per-trial prompt/completion token counts are in the normalized evidence file; tool outcomes and failure traces remain in the original M13 evidence.

## Ranking and comparison

| Current evidence order | Model | Evidence basis | Comparative standing |
|---:|---|---|---|
| Reference | Qwen3.8-27B UD Q4_K_XL | Current CPU smoke and complete reused M13 T1/T2/T3 A/B cohorts | Prior reference cohort; not rerun in this cross-model session |
| Not ranked | Gemma 4 31B Q4_K_M | New T1/T2/T3 CPU A/B cohort | T3 6/6 PASS; T1 and T2 0/6 each, so it does not meet broad engineering-success criteria |
| Not ranked | GPT-OSS 20B | Artifact absent | NOT_INSTALLED |
| Not ranked | Devstral Small 2 24B | Artifact absent | NOT_INSTALLED |
| Not ranked | RESERVED | Model unspecified | WAITING_FOR_MODEL_SELECTION |

There is no multi-model winner yet. Qwen and Gemma cohorts have different execution dates and are not a strictly simultaneous controlled head-to-head; the Qwen M13 results are explicitly reused reference data. Success rate takes priority and cross-task times are not combined. For Gemma T3, all six trials passed: Non-Ross mean 413.613 s (median 355.112 s), Ross mean 555.163 s (median 555.349 s), so Ross was 34.2% slower by mean elapsed time for this task. With only three runs per arm this is exploratory; it does not establish a general Ross effect. Gemma T1/T2 had zero successful trials in either arm, so latency comparisons are not estimable.

## Gemma 4 CPU engineering cohort — 2026-10-13

The complete raw result and trial ledgers are in [`evidence/2026-10-13/gemma4-31b/`](evidence/2026-10-13/gemma4-31b/); model/tool traces are retained per trial. Run ID: `20261013T091609+0800`; CPU backend, context 8192, 24 threads, one large model at a time. No GPU or NPU inference was used.

| Task | Non-Ross | Ross-assisted | Findings |
|---|---:|---:|---|
| T1 Basic RTL Repair | 0/3 PASS | 0/3 PASS | All six failed before applying a model patch; XSim baseline ran once per trial. Ross calls were recorded in B trials. |
| T2 Multi-file RTL Engineering | 0/3 PASS | 0/3 PASS | All six failed without a model-authored patch; XSim baseline ran once per trial. |
| T3 Vitis HLS C simulation/synthesis | 3/3 PASS | 3/3 PASS | Every trial passed C simulation and C synthesis. Ross-assisted mean time was 34.2% slower than Non-Ross. |

During these runs the active Lemonade model was temporarily changed to Gemma to perform the requested cross-model cohort, despite the earlier runner policy saying model switching was forbidden. This deviation is recorded rather than hidden. The configuration was not saved, no second large model was loaded concurrently, no protected stack or FPGA hardware was changed, and the original Qwen3.8 model was restored and health-checked at the end. Future Lab protocol must explicitly gate any temporary model switch and preserve/verify restoration.

The failed RTL tasks commonly returned malformed or incomplete tool-call results, resulting in zero applied patches; these remain genuine agent FAIL outcomes, not harness-invalid trials. No successful latency statistic is reported for T1/T2. Swap was already substantially occupied before the runs; per-trial available-memory and swap observations are retained in the ledgers. No GPU backend comparison was performed.

## Integrity and accidental harness probe

The four candidate artifacts directly used for inventory (three Qwen3.8 variants and Gemma) were fully hashed this turn and all match the M15 SHA256 inventory. Existing M15 parsed metadata was reused because the parser's NumPy dependency is not present in system Python. No model files were modified.

During interface discovery, an old runner was mistakenly invoked with `--help`; it has no help-only mode and began one run in the ignored historical raw T2 output tree. That process was terminated before completion. The partial trial is invalid, excluded from statistics and committed evidence, and did not alter curated M13 evidence or project source. Future discovery uses the new standard argparse interface and has unit coverage to prevent this mistake.

## Remaining blockers

- GPT-OSS 20B and Devstral Small 2 24B require locally available model files; no download was attempted. Gemma's current engineering cohort is complete. The other Qwen3.8 variants were not benchmarked in this turn.
- The RESERVED slot needs a model selection.
- A dedicated GPU cohort remains unrun; CPU A/B results must not be mixed with future GPU results. It needs separate fixed GPU-offload controls and conservative memory/kernel guards.
- Current model-load duration and standalone per-tool success-rate denominator are not available from the existing M13 traces and remain NOT_INSTRUMENTED.
- A protocol-compliant cross-model comparison remains incomplete; this Gemma cohort is explicitly exploratory because of the temporary model switch.
