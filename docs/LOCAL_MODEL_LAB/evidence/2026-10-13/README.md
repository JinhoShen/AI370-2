# Local Model Lab evidence — 2026-10-13

- `phase0-inventory.tsv`: five requested roster slots plus the two additional Qwen3.8 variants. SHA256 values for four non-retired GGUF files match existing M15 inventory.
- `phase0-backend-snapshot.txt`: OS-visible CPU/RAM/swap, llama.cpp version, backend device enumeration, and the original Qwen CPU configuration.
- `qwen38-xl-cpu-smoke.json` and `qwen38-xl-lemonade-smoke.json`: bounded Qwen3.8 CPU smokes.
- `qwen38xl-m13-baseline.json`: normalized Qwen3.8 XL T1/T2/T3 A/B results reused from M13; these were not rerun here.
- `qwen38-restored-preflight.json`: a fresh read-only preflight after the Gemma cohort; confirms the formal Qwen3.8 XL is active again.
- `gemma4-31b/`: exploratory CPU T1/T2/T3 A/B cohort, including per-trial ledgers, tool/model/Ross traces, and HLS validation logs. The temporary model switch violated the original no-switch protocol, so this cohort is not acceptance-grade.

Top-level `SHA256SUMS` covers the files directly in this directory. The Gemma subdirectory has its own `SHA256SUMS`. Verify both manifests from the repository root.
