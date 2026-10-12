# M13 Ross / Local Qwen A/B evidence

This directory contains curated, reviewable artifacts for the formal T1/T2/T3 trials plus T2 diagnostic history. `SHA256SUMS` covers every file in this evidence directory except the checksum file itself.

## Cohort map

- `T1/official-cohort/`: complete T1 A1→B1→B2→A2→A3→B3 ledger, Local Agent tool traces, fixed seed inputs, stdout/stderr and selected XSim logs. T1 Ross failures are retained.
- `T2/seed/`: exact fixed task, original RTL modules and unchanged testbench used by all multi-file cohorts.
- `T2/initial-v5/`, `bounded-context-v6/`, `compaction-v7-diagnostic/`: separate unpooled iteration histories. Their trial ledgers and traces are retained to show the context/tool-call/parser failure path and exploratory Ross repair results.
- `T2/corrected-controlled/`: complete fixed-policy A1→B1→B2→A2→A3→B3 formal 3×3 cohort, including per-trial final status, traces, source snapshots and selected XSim output. A/B workspace seeds and the testbench are unchanged.
- `T3/official-cohort/`: complete HLS A1→B1→B2→A2→A3→B3 ledger, source snapshots, Local Agent traces and selected C simulation/C synthesis logs and reports.
- `resource-backend-snapshot.txt`: host CPU/RAM/swap and existing model backend/configuration observed during this benchmark. The GGUF model itself is not copied.

The raw, ignored run directories remain under `output/M13/ross-ab-benchmark-2026-10-12/` and `output/M13/ross-ab-benchmark-2026-10-13/`. This repository evidence excludes simulator caches, HLS intermediate objects/binaries, model files, installed Xilinx trees, and credentials/license files. The full machine-readable sample data are in each `trials.json`; token usage, elapsed time, Ross calls, attempt counts, resource measurements and final source hashes are retained per trial. `timing_breakdown.json` identifies which model/tool timing values are exact, approximate from T2 monotonic traces, or not instrumented in older T1/T3 traces; it does not impute missing values.

## Verdict

T1: A 3/3, B 0/3. Corrected T2: A 3/3, B 1/3 (two B context overflows). T3: A 3/3, B 3/3, Ross 2.69% slower by mean. These bounded samples show that Ross Skills/local KB can be used by the standalone Local Agent, but do not prove a general success-rate or speed benefit. M13 remains PARTIAL; see `../../../M13_ROSS_AB_BENCHMARK_REPORT.md`.
