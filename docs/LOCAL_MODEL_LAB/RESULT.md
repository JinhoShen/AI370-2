# AI370-2 Local Model Lab — current result

**Status: PARTIAL.** Phase 0 inventory and Phase 1 guarded cross-model runner are complete. The active Qwen3.8-27B UD Q4_K_XL passed a new bounded CPU smoke. Its complete formal T1/T2/T3 A/B engineering results are reused from M13. A current cross-model comparison is blocked because GPT-OSS 20B and Devstral Small 2 24B are not installed, the reserved model is unspecified, and switching the active production Qwen server is expressly forbidden. Gemma and other Qwen3.8 artifacts are present and have historical smoke evidence, but are not currently loaded.

## Model inventory

| Roster model | Local artifact | Current status | Integrity / metadata |
|---|---|---|---|
| Qwen3.8-27B | `Qwen3.8-27B-UD-Q4_K_XL.gguf` (17,559,178,144 bytes) | ACTIVE; current CPU smoke PASS | SHA256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`, matches current full hash and M15 metadata inventory; architecture `qwen35`, 27.32B parameters, Q4_K_M metadata label |
| GPT-OSS 20B | Not found in the Local AI resource tree | NOT_INSTALLED; no download attempted | No file/hash/metadata |
| Devstral Small 2 24B | Not found in the Local AI resource tree | NOT_INSTALLED; no download attempted | No file/hash/metadata |
| Gemma 4 31B | `gemma-4-31b-jang-crack-Q4_K_M.gguf` (18,687,057,344 bytes) | PRESENT; not active | SHA256 `b1fc8ee10f916da019dbb1d177854fa3b6421fbea1e93839a2061861308e1de7`, matches current full hash and M15 record; architecture `gemma4`, 30.697B parameter elements, Q4_K_M |
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

Qwen3.8 Q4_K_M, Qwen3.8 Uncensored Q4_K_M, and Gemma 4 have historical bounded CPU smoke PASS evidence under M7 with matching present-file SHA256. Those historical outcomes are not new Phase 2 executions. Current inference was not attempted for them because the active production model may not be switched and two large models must not be resident together.

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
| 1 (reference only) | Qwen3.8-27B UD Q4_K_XL | Current CPU smoke and complete reused M13 T1/T2/T3 A/B cohorts | Reference baseline, not a winner; Ross benefit is task-dependent |
| Not ranked | Gemma 4 31B Q4_K_M | Historical bounded smoke only; not active and no engineering cohort | Insufficient comparison evidence |
| Not ranked | GPT-OSS 20B | Artifact absent | NOT_INSTALLED |
| Not ranked | Devstral Small 2 24B | Artifact absent | NOT_INSTALLED |
| Not ranked | RESERVED | Model unspecified | WAITING_FOR_MODEL_SELECTION |

There is no multi-model winner yet. Success rate takes priority; cross-task times are not combined. Existing M13 results show task-dependent Ross behavior and do not establish a general Ross advantage.

## Integrity and accidental harness probe

The four candidate artifacts directly used for inventory (three Qwen3.8 variants and Gemma) were fully hashed this turn and all match the M15 SHA256 inventory. Existing M15 parsed metadata was reused because the parser's NumPy dependency is not present in system Python. No model files were modified.

During interface discovery, an old runner was mistakenly invoked with `--help`; it has no help-only mode and began one run in the ignored historical raw T2 output tree. That process was terminated before completion. The partial trial is invalid, excluded from statistics and committed evidence, and did not alter curated M13 evidence or project source. Future discovery uses the new standard argparse interface and has unit coverage to prevent this mistake.

## Remaining blockers

- GPT-OSS 20B and Devstral Small 2 24B require user-provided local model files; this Lab did not download anything.
- RESERVED needs a model choice.
- Gemma and the other Qwen3.8 variants require a safely selected active provider; this runner deliberately does not stop or switch the formal Qwen server.
- Current model-load duration and standalone per-tool success-rate denominator are not available from the existing M13 traces and remain NOT_INSTRUMENTED.
- Cross-model rankings and Ross effects remain UNKNOWN until each artifact is locally available and run through the same configured cohorts.
