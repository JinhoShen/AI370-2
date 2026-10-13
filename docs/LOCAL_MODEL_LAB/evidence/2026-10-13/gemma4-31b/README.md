# Gemma 4 31B CPU engineering cohort (exploratory)

- Local run ID: `20261013T091609+0800` (Asia/Taipei).
- Model: `gemma-4-31b-jang-crack-Q4_K_M.gguf`, 18,687,057,344 bytes.
- SHA256: `b1fc8ee10f916da019dbb1d177854fa3b6421fbea1e93839a2061861308e1de7`.
- Backend: existing Lemonade/llama.cpp CPU; context 8192, 24 threads, 24 batch threads, zero GPU layers, one parallel slot.
- Task order: T1, T2, T3; each used A1 → B1 → B2 → A2 → A3 → B3 (three Non-Ross and three Ross trials).
- Ross endpoint calls were local Skill/Knowledge Base requests, recorded in B traces.
- No FPGA programming or protected GPU/NPU stack changes.

## Results

| Task | Non-Ross | Ross-assisted | Notes |
|---|---:|---:|---|
| T1 Basic RTL Repair | 0/3 PASS | 0/3 PASS | No model patch applied; all six failed. |
| T2 Multi-file RTL Engineering | 0/3 PASS | 0/3 PASS | No model patch applied; all six failed. |
| T3 Vitis HLS CSim/CSynth | 3/3 PASS | 3/3 PASS | Both C simulation and C synthesis markers verified in all trials. |

T3 mean end-to-end time: Non-Ross 413.613 s; Ross 555.163 s. Exploratory Ross delta: 34.2% slower. Only three samples per arm; do not generalize. Failed T1/T2 latency is not used as a successful completion-time comparison.

## Protocol deviation

The benchmark controller temporarily loaded Gemma into Lemonade even though the fixed protocol prohibited automatic active-model switching. It did not save the production configuration and did not load two large models concurrently. After the cohort, it restored the formal Qwen3.8 model and reported `RESTORE_QWEN=PASS`. This deviation makes the Gemma cohort exploratory rather than acceptance-grade controlled evidence. The raw controller output is not part of the repository; the structured run result, per-task ledgers, Local Agent traces and HLS validation logs are preserved here. Future cross-model runs must separately authorize and explicitly gate model residency and restoration.

## Evidence files

- `result.json`: aggregate preflight, per-task summaries and scoreboard.
- `T1/trials.json`, `T2/trials.json`, `T3/trials.json`: raw trial ledgers.
- `T1/*-trace.jsonl`, `T2/*-trace.jsonl`, `T3/*-trace.jsonl`: model/tool/Ross traces for all 18 attempts.
- `T3/A1` through `T3/B3`: fixed task/spec/config, source/testbench, and actual HLS C-simulation/C-synthesis logs for each passing trial.

The source and testbench hashes are in the raw ledgers. Build/cache products were excluded. The production Qwen3.8 setting was restored after the run; this is an execution record, not a new Qwen benchmark.
