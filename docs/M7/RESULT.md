# M7 Local LLM benchmark — RESULT

日期：2026-10-01。狀態：PASS（保守短測範圍）。未執行高壓長測或 4096/8192 context。

## Reproducible benchmark

- Model: local `Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf`, SHA-256 `ba3a1d47a604f17ef74d913f9a9d9a2b456acc6925e7b168bfa2e6527246011c`, 11,648,246,272 bytes; Qwen35MoE, 35B total / 3B active, IQ2_M.
- Binary source commit: llama.cpp `7fe450e19305b828c199d602c23a8337aaa1f03b` (M6 independent CPU/Vulkan/HIP binaries).
- Comparable run: `llama-bench -p 64 -n 64 -r 3 -b 16 -ub 8 -t 8`, fixed KV K/V `f16`; each prefill and decode test allocates context 64 (`llama-bench` sets `n_ctx=n_prompt+n_gen+n_depth`). CPU: `-ngl 0 -dev none`; Vulkan: `-ngl 1 -dev Vulkan0`; ROCm: `-ngl 1 -dev ROCm0`. This version's `-p 64` and `-n 64` are distinct prefill/decode measurements, each at context 64, rather than one combined 128-token conversation.
- Every benchmark ran in a user systemd scope capped at 24 GiB RAM, zero swap, 800% CPU. Three repetitions include the tool's warmup. No additional model was loaded concurrently.

## Results

| Backend/device | Offload | Prefill 64 (tok/s, mean ± sd) | Decode 64 (tok/s, mean ± sd) | Max RSS (KiB) | Sampled peak GTT / VRAM |
|---|---:|---:|---:|---:|---:|
| CPU / none | 0 layers | 59.72 ± 0.36 | 22.09 ± 0.63 | 11,852,820 | N/A / N/A |
| Vulkan / RADV GFX1150 | 1 layer | 49.86 ± 0.32 | 19.58 ± 0.75 | 280,612 | 10.65 / 1.08 GiB |
| ROCm / gfx1150 | 1 layer | 54.27 ± 0.18 | 21.03 ± 0.25 | 11,481,088 | 0.62 / 0.72 GiB |

Memory figures were sampled from `/proc` and `/sys/class/drm/card1/device/mem_info_{gtt, vram}_used` during short runs, so the sysfs measurements describe this UMA device's kernel-accounted allocations, not exclusive per-process physical VRAM. During the higher Vulkan step, minimum `MemAvailable` was 32.49 GiB; swap remained 0. The system returned to 43 GiB available RAM after each run. HIP run minimum available RAM was 31.71 GiB. No test exceeded the resource scope limits.

Progression was CPU/Vulkan/ROCm at prompt 32/decode 16 first (three reps; contexts 32 each), then only after clean kernel logs Vulkan at prompt 64/decode 64, followed by CPU and ROCm at the exact same parameters. GPU offload stayed at one layer. Journal checks after each stage found no new amdgpu fault/page fault/reset/timeout, TTM corruption or soft lockup. No swap-in/out occurred. This establishes only a conservative benchmark baseline; it is not an extended-load or high-context stability certification.

Raw llama-bench JSON, timing/RSS, memory samples and before/after kernel snapshots are retained in ignored `output/M7/`. The selected local model and binary provenance hashes are recorded above and in M6. No fixed local RTL/Tcl quality-test corpus was available, so this milestone makes no engineering-answer quality claim.
