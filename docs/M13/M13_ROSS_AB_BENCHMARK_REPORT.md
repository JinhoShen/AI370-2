# M13 AMD Ross / Local Qwen A/B benchmark

**Overall: PARTIAL — no general Ross advantage proven.** The Local Agent made real Ross Skill and local Knowledge Base MCP calls. Results vary by task: Ross completed 0/3 T1 repairs, 1/3 corrected T2 multi-file repairs, and 3/3 T3 HLS source checks. T2 Non-Ross completed 3/3; the sole successful B trial is too small for a reliable latency comparison. The valid T3 equal-success comparison was 2.69% slower by Ross mean end-to-end time.

## Common setup and controls

- Model: existing `Qwen3.8-27B-UD-Q4_K_XL` through the existing Lemonade-compatible loopback endpoint. The running server uses the CPU backend, `--n-gpu-layers 0`, context 8192, and 24 inference/24 batch threads; CPU was not restricted to four cores.
- A uses the same `scripts/local_agent.py`, task, fresh seeded workspace, fixed validators and bounds without any Ross tool schema or endpoint. B has explicit calls to the installed AMD `vivado-simulate-rtl` Skill and actual local AMD Doc Search MCP `vivado_doc_search`. No Codex execution or cloud model was used.
- Trials ran sequentially; every repetition used a fresh workspace. Task/specification, fixed testbench and validator remained unchanged within each cohort. Validation is software-only; no FPGA programming or Golden-project edits.
- Resource guard stops below `max(6 GiB, 12.5% of detected RAM)` MemAvailable or on >2 GiB swap growth during a trial. No formal T1/T2/T3 trial was stopped by this guard. Swap was already occupied at baseline.
- End-to-end duration includes Local Agent/model request wall time and validation. Local Agent `model_request_seconds` is retained when the agent emits a final ledger; failure runs without one have no exact aggregate wall-time split, although server timing payloads are retained separately. T2 monotonic traces support approximate post-response tool durations; older T1/T3 trace formats lack tool timestamps, so their per-tool execution time is NOT_INSTRUMENTED. MCP server call latency is separately reported. Three-sample P90 is exploratory and shown as the maximum observed. Failed trial duration is time-to-failure, never completion time. No latency gain is claimed without adequate successful samples.

## T1 — Basic one-file RTL repair

Each fresh run starts from the same AXI-Lite XOR-mode fault. The unchanged self-checking test expects `0x1336597c`; baseline returns `0x1336557c`. Success requires a model-authored RTL modification and the fixed XSim terminal PASS marker.

Formal ledger: `output/M13/ross-ab-benchmark-2026-10-12/T1-timeout600/trials.json`.

| Trial | Result | Time (s) | Prompt/completion tokens | Ross calls | XSim invocations / PASS | Patches |
|---|---|---:|---:|---:|---:|---:|
| A1 | PASS | 1058.246 | 27374 / 498 | 0 | 2 / 1 | 1 |
| A2 | PASS | 991.236 | 27374 / 498 | 0 | 2 / 1 | 1 |
| A3 | PASS | 904.954 | 27119 / 360 | 0 | 2 / 1 | 1 |
| B1 | FAIL | 1184.976 | 26221 / 430 | 2 | 2 / 0 | 0 |
| B2 | FAIL | 1112.461 | 26216 / 431 | 2 | 2 / 0 | 0 |
| B3 | FAIL | 1180.544 | 26219 / 432 | 2 | 2 / 0 | 0 |

A passed 3/3; B passed 0/3. All B samples made the real Ross Skill and MCP calls, but Qwen returned malformed/truncated multi-file tool-call JSON (provider HTTP 500); no patch was applied. The first counted XSim invocation was blocked by the Ross-prerequisite policy, so only the unchanged baseline actually ran. A mean/median completion time was 984.812/991.236 s; its n=3 P90 (maximum observed) was 1058.246 s. B has no completion-time sample. MCP lookup calls took 0.085–0.086 s each.

## T2 — Multi-file RTL engineering

Fixed task: add readable/writable `REG_OPERAND_B` at byte address `0x10`; when control bit 2 is set, return wrapping 32-bit `value + operand_b`; preserve the existing complement default and control-bit-1 XOR-with-offset behavior. A fixed unchanged testbench checks all cases. Fixed testbench SHA256: `b73d5d68ef19be5723c2e7ee43441e61001fb4a3426596ff3608a9f093834280`.

### Initial T2-v5 3×3 cohort

Ledger: `output/M13/ross-ab-benchmark-2026-10-12/T2-multifile-hunkfix-v5-final/trials.json`.

| Arm | PASS | Trial durations (s) | Interpretation |
|---|---:|---|---|
| A | 2/3 | 1800.473 FAIL; 1335.673 PASS; 780.274 PASS | One total timeout; two model-authored patches passed XSim |
| B | 0/3 | 697.204; 446.865; 517.186 FAIL | Real Skill/MCP calls; original Ross context composition exceeded the 8192-token model window / yielded malformed tool calls |

The defect identified in the B flow was Local Agent context/tool-call assembly. This cohort is retained as-is and does not measure the corrected implementation.

### T2-v6 and T2-v7 diagnostic follow-ups

These cohorts changed context compaction / prompt/runner policy between rounds. They are **diagnostic, not pooled** with either controlled T2 cohort.

| Diagnostic cohort | A | B | What it establishes |
|---|---:|---:|---|
| T2-v6 bounded context | 2/3 PASS | 1/3 PASS | A and B each had a timeout or malformed tool output; one Ross/Qwen patch passed XSim |
| T2-v7 compaction | 2/3 PASS | 1/3 PASS | B1 Ross-assisted model patch passed; B2/B3 and A1/A3 retained failures while fixing patch normalization/context behavior |

Full v5/v6/v7 trial ledgers, model traces and selected simulator logs are separated by cohort under `evidence/2026-10-12/ross-ab-benchmark/T2/`.

### Corrected controlled T2 cohort (A1 → B1 → B2 → A2 → A3 → B3)

This cohort used one fixed prompt, runner, source seed, context limit, tool policy and validation cap for all six repetitions. It is the formal corrected comparison. Raw live output is under ignored `output/M13/ross-ab-benchmark-2026-10-13/T2-corrected-controlled/`; curated evidence is under `evidence/2026-10-12/ross-ab-benchmark/T2/corrected-controlled/`.

| Trial | Result | Time (s) | Prompt/completion tokens | Ross calls (MCP seconds) | XSim runs / PASS | Accepted patches |
|---|---|---:|---:|---:|---:|---:|
| A1 | PASS | 1262.359 | 28460 / 2209 | 0 (0) | 2 / 1 | 1 |
| B1 | PASS | 1420.973 | 29967 / 2713 | 2 (0.184) | 2 / 1 | 1 |
| B2 | FAIL | 653.026 | 23950 / 591 | 4 (0.423) | 1 / 0 | 0 |
| A2 | PASS | 1117.061 | 21870 / 2037 | 0 (0) | 2 / 1 | 1 |
| A3 | PASS | 913.976 | 22551 / 2668 | 0 (0) | 2 / 1 | 1 |
| B3 | FAIL | 863.347 | 23950 / 582 | 4 (0.329) | 1 / 0 | 0 |

A passed 3/3 (mean 1097.799 s, median 1117.061 s; exploratory P90 1262.359 s). B passed 1/3. B1 is a genuine Ross-assisted result: after the unchanged baseline failure, Qwen-authored patch formatting was rejected twice without modifying RTL; the model then emitted a valid bounded two-file patch and the unchanged XSim test passed. B2 and B3 each ended with an explicit provider `context_length_exceeded` error at 8886 and 8919 prompt tokens against the 8192 context; no source patch was applied. Because B has only one successful trial, completion-time comparisons between arms are **NOT statistically meaningful**. Successful-only B latency is a single observation (1420.973 s), not an estimated treatment mean. The failure times are not called completion times.

### T2 resource observations

| Arm | Mean prompt/completion tokens | Mean peak process RSS (MiB) | Minimum MemAvailable (MiB) | Maximum swap used (MiB) | Mean machine-equivalent CPU |
|---|---:|---:|---:|---:|---:|
| A | 24294 / 2305 | 28105.3 | 28311.8 | 5629.3 | 96.7% |
| B | 25956 / 1295 | 27768.9 | 28457.1 | 5629.2 | 96.3% |

The host already had about 5.6 GiB swap occupied. No trial exceeded the swap-growth or MemAvailable guard. Ross MCP mean measured time across B trials was 0.312 s; Skill read time was not separately instrumented. The model spent substantially more wall time than MCP calls.

## T3 — Vitis HLS source engineering

Each isolated run starts from the same `invert32` defect (`~input ^ 1u`). The unchanged four-vector C testbench is validated by fixed Vitis HLS C simulation and C synthesis checks for `xc7s100fgga676-2`. This is source-level CSim/CSynth, not full implementation, timing closure, or physical FPGA execution.

Ledger: `output/M13/ross-ab-benchmark-2026-10-12/T3-HLS-timeout600-final/trials.json`.

| Trial | Result | Time (s) | Prompt/completion tokens | Ross calls | HLS runs; CSim/CSynth PASS |
|---|---|---:|---:|---:|---:|
| A1 | PASS | 580.364 | 12590 / 314 | 0 | 2; 1 / 1 |
| A2 | PASS | 473.563 | 16371 / 383 | 0 | 2; 1 / 1 |
| A3 | PASS | 469.895 | 16371 / 383 | 0 | 2; 1 / 1 |
| B1 | PASS | 437.001 | 19339 / 545 | 2 | 2; 1 / 1 |
| B2 | PASS | 415.032 | 19297 / 503 | 2 | 2; 1 / 1 |
| B3 | PASS | 712.807 | 25088 / 568 | 2 | 2; 1 / 1 |

Both arms passed 3/3. A mean/median was 507.941/473.563 s; B was 521.613/437.001 s. Mean time improvement `(A−B)/A` is **−2.69%** (Ross slower); median-based improvement is +7.72%. At n=3 the difference is exploratory and timing variability is high. The maximum observed sample P90 is 580.364 s (A), 712.807 s (B). Mean tokens per trial were 15111/360 (A) and 21241/539 (B); B used more prompt and completion tokens. Ross Doc Search MCP latency was sub-second per trial. CPU was not captured by the T3 runner and is not inferred here.

## Resource and timing measurement coverage

| Formal cohort | Arm | Mean peak process RSS (MiB) | Minimum MemAvailable (MiB) | Maximum swap used (MiB) | Mean machine-equivalent CPU |
|---|---|---:|---:|---:|---:|
| T1 | A | 28454.1 | 28563.9 | 5717.7 | 95.7% |
| T1 | B | 28041.2 | 28853.2 | 5716.1 | 96.2% |
| Corrected T2 | A | 28105.3 | 28311.8 | 5629.3 | 96.7% |
| Corrected T2 | B | 27768.9 | 28457.1 | 5629.2 | 96.3% |
| T3 | A | 28723.2 | 29072.6 | 5731.5 | NOT_CAPTURED |
| T3 | B | 28855.0 | 27869.3 | 5725.3 | NOT_CAPTURED |

T1/T2 CPU values are the runner's process CPU over the full trial, normalized to total machine capacity; RSS includes the local model process. The host started with about 5.6–5.7 GiB swap occupied. No formal sample crossed the available-memory or swap-growth guard.

Timing detail is in [`timing_breakdown.json`](evidence/2026-10-12/ross-ab-benchmark/timing_breakdown.json). The corrected T2 tool-event timing is derived from monotonic timestamps: two XSim runs totalled about 8.05–8.10 s for successful trials and one baseline run about 4.06–4.08 s for failed B trials; this includes executor dispatch/serialization and is approximate. Exact MCP call durations were 0.085–0.086 s per T1 Ross sample, 0.184/0.423/0.329 s for corrected T2 B1/B2/B3, and 0.494/0.088/0.149 s for T3. The old T1/T3 traces lack monotonic tool timestamps, so XSim/HLS per-tool wall time and Skill-read wall time are **NOT_INSTRUMENTED** there. Missing measurements are not imputed. Per-request `model_request_seconds` and end-to-end elapsed remain reported separately; the local server's token timing fields are retained as a distinct, non-equivalent measurement.

## Combined interpretation

- Task-level formal success: T1 A 3/3 vs B 0/3; corrected T2 A 3/3 vs B 1/3; T3 A 3/3 vs B 3/3. The cross-task descriptive totals are A 9/9 and B 4/9, but tasks differ and this is not a generalized success-rate estimate.
- Real Ross use is verified in all formal B samples: selected installed Skill content and the actual local `AMD Doc Search 0.11.0` MCP `vivado_doc_search` calls are present in traces. This is Skills + local Knowledge Base assistance; it is **not** Qwen access to unrestricted Vivado Tcl through Vivado MCP. No dedicated Vitis/HLS MCP was found.
- Only T3 has balanced 3/3 success for a completion-time comparison, and Ross was slower by mean. T1 B had zero completions. Corrected T2 B had one success, too few to compare completion times reliably. No overall time-saving claim is supported.
- Qwen ran on the existing Lemonade CPU backend with 24 configured inference/batch threads. No Codex CLI/OpenAI API/cloud model execution took part. The local KB MCP used an internal container network; physical host-network disconnection and air-gapped Telegram/Ross operation remain NOT TESTED.
- The B arms used more prompt tokens because Ross instructions/retrieval were included. In measured samples the model/Agent loop dominated elapsed time; MCP calls were sub-second. T2 has approximate event-timed XSim tool durations; T1/T3 per-tool duration and all Skill-read duration were not consistently instrumented.
- Failure modes remain visible: T1 truncated/invalid JSON; initial T2 context/JSON failures; corrected T2 malformed model patch attempts and two 8192-context overflows. The guarded patch executor rejected invalid patches without changing source. No testbench or Golden project was altered.

**M13 Ross benchmark verdict: PARTIAL / MIXED RESULTS / NO GENERAL BENEFIT PROVEN.** The requested formal T1/T2/T3 sample set is complete, but Ross did not improve aggregate task success in these samples and the only valid balanced timing comparison showed a small mean regression. Remaining M13 scope includes Vivado Tcl/MCP integration (not exposed intentionally), direct Vitis Unified/Embedded integration, full host-disconnected operation, air-gapped Telegram, and M13 overall acceptance. None is marked PASS by this benchmark.
