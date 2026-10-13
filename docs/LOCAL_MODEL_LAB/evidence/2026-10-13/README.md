# Local Model Lab evidence — 2026-10-13

- `phase0-inventory.tsv`: five requested model slots plus the two extra Qwen3.8 variants. SHA256 values for all four non-retired GGUF files were recomputed this turn and match the existing M15 manifest.
- `phase0-backend-snapshot.txt`: OS-visible CPU/RAM/swap, llama.cpp version, backend device enumeration, and the active Lemonade/llama.cpp CPU model configuration.
- `qwen38-xl-lemonade-smoke.json`: current 2-token smoke via the same Lemonade loopback API used by the Local Agent.
- `qwen38-xl-cpu-smoke.json`: direct llama.cpp loopback smoke of the same already-loaded model; no second model was loaded.
- `qwen38xl-m13-baseline.json`: normalized T1/T2/T3 formal A/B trial metadata imported from the cited M13 ledgers. It is explicitly reused evidence; no engineering cohort was rerun in the Model Lab phase.

`SHA256SUMS` covers all evidence files except itself. Verify from the repository root using `sha256sum -c docs/LOCAL_MODEL_LAB/evidence/2026-10-13/SHA256SUMS`.
