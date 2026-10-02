# Local model evaluation — 2026-10-02

Status: **BOUNDED SMOKE PASS FOR TESTED MODELS; NOT A LONG BENCHMARK OR STABILITY CLAIM.** Runs were sequential. CPU tests used context 64, at most 2 generated tokens, four CPU threads, CPU-only llama.cpp, and systemd cgroups with swap disabled. GPU tests used context 32, at most 4 generated tokens (most generated 2), four CPU threads, exactly one layer offloaded, explicit backend/device selection, cgroup swap disabled, a 25 GiB available-memory precondition, and a kernel-fault audit after every run.

## Model inventory and CPU smoke

| Model | Source and integrity | Parsed metadata | CPU smoke |
|---|---|---|---|
| Qwen3.5-9B UD Q4_K_XL | Lemonade cache copy `(2)`; 5,966,095,584 bytes; SHA256 `6f5d30666c2d8ae16a306e616d95341dcf3cc46810df84d7e6f5a7d1e4c1b293` | `qwen35`, 8.95B parameters; llama.cpp reports Q4_K Medium | **PASS**, exit 0; 2 tokens; 8.9 tok/s; peak RSS 7,624,192 KiB; 0 swaps |
| Qwen3-14B Q4_0 | Member in `Lemonade/Qwen_Cache/SER9-Qwen-Models.tar`; archive SHA256 sidecar verified; extracted test copy 8,543,001,984 bytes; model SHA256 `009f54ffc8d8082e7921139924229d4deea61c9174a0a357d91384bd299ff78e` | `qwen3`, 14.77B parameters, Q4_0 | **PASS**, exit 0; 2 tokens; 7.0 tok/s; peak RSS 15,426,464 KiB; 0 swaps |
| Qwen3.8-27B UD Q4_K_M | 16,464,440,224 bytes; SHA256 `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482` | `qwen35`, 27.32B parameters, Q4_K Medium | **PASS**, exit 0; 2 tokens; 3.1 tok/s; peak RSS 18,589,188 KiB; 0 swaps |
| Qwen3.8-27B UD Q4_K_XL | 17,559,178,144 bytes; SHA256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` | `qwen35`, 27.32B parameters; llama.cpp reports Q4_K Medium | **PASS**, exit 0; 2 tokens; 3.0 tok/s; peak RSS 18,930,832 KiB; 0 swaps |
| Qwen3.8-27B Uncensored Q4_K_M | 16,810,714,528 bytes; SHA256 `4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675` | `qwen35`, 27.32B parameters, Q4_K Medium | **PASS**, exit 0; 2 tokens; 2.9 tok/s; peak RSS 25,708,928 KiB; 0 swaps |
| Gemma 4 31B Q4_K_M | 18,687,057,344 bytes; SHA256 `b1fc8ee10f916da019dbf4c9a9d9a2b456acc6925e7b168bfa2e6527246011c` | `gemma4`, 30.70B parameters, Q4_K Medium | **PASS**, exit 0; 2 tokens; 2.5 tok/s; peak RSS 31,348,244 KiB; 0 swaps |
| Qwen3.6-35B-A3B Q8_0 | Existing M7 evidence; SHA256 `d8d7842cc657d720f39546878e431937c84473aa130c36371669ac17c80c7361` | `qwen35moe`, 34.66B parameters, Q8_0 | Earlier bounded CPU smoke **PASS**; not repeated |
| Qwen3.6-35B-A3B Uncensored IQ2_M | Existing M15 evidence | `qwen35moe`, 34.66B parameters, IQ2_M | Existing bounded CPU inference **PASS**; not repeated |

The archive-contained Qwen3-14B model was extracted to `/tmp` for the GPU smokes as well; its archive was not modified. The Lemonade cache contains repeated Qwen3.5-9B copies; this run tested one copy only. SHA and metadata inventory for the GGUF files in the main `GGUF/` directory is retained in [M15 model summary](../M15/evidence/2026-10-02/unified-final-validation/models/model-summary.tsv).

## Bounded Vulkan and ROCm inference

Every run below returned exit 0, generated the requested short response, logged the named device and one GPU layer with a nonzero backend buffer, used zero cgroup swap, and had zero matching kernel faults. Vulkan resolved to Radeon 890M / RADV GFX1150; ROCm resolved to Radeon 890M (`0000:c5:00.0`). These are partial-offload smoke results, not full GPU offload.

| Model | Vulkan | ROCm | Evidence prefix |
|---|---|---|---|
| Qwen3.5-9B | **PASS**, 1/33 layers, 9.4 tok/s | **PASS**, 1/33 layers, 9.7 tok/s | `qwen35-9b-` |
| Qwen3-14B | **PASS**, 1/41 layers, 5.5 tok/s | **PASS**, 1/41 layers, 5.5 tok/s | `qwen3-14b-` |
| Qwen3.8-27B UD Q4_K_M | **PASS**, 1/66 layers, 3.0 tok/s | **PASS**, 1/66 layers, 3.4 tok/s | `qwen38-q4km-` |
| Qwen3.8-27B UD Q4_K_XL | **PASS**, 1/66 layers, 2.7 tok/s | **PASS**, 1/66 layers, 3.2 tok/s | `qwen38-q4kxl-` |
| Qwen3.8-27B Uncensored Q4_K_M | **PASS**, 1/66 layers, 3.1 tok/s | **PASS**, 1/66 layers, 3.3 tok/s | `qwen38-uncensored-` |
| Gemma 4 31B Q4_K_M | **PASS**, 1/61 layers, 2.6 tok/s | **PASS**, 1/61 layers, 2.9 tok/s | `gemma4-31b-` |
| Qwen3.6-35B-A3B Uncensored IQ2_M | Existing M15 bounded CPU/Vulkan/ROCm inference **PASS**, context 32 and one GPU layer | Existing M15 bounded CPU/Vulkan/ROCm inference **PASS**, context 32 and one GPU layer | `docs/M15/evidence/2026-10-02/unified-final-validation/models/m7-iq2-*` |

## Explicit exclusions and limits

- Qwen3.6-35B-A3B Q8 Vulkan: **not rerun**. The known device-loss/kernel-error investigation remains **M7.1 OPEN**. Qwen3.6 Q8 ROCm remains **NOT TESTED** under the existing safety gate.
- The Qwen3.6 IQ2 result is reused from M15 rather than repeated.
- The `mmproj` file is a companion projector, not a standalone text model; multimodal inference was **NOT TESTED**.
- NPU inference for these GGUF models was **NOT TESTED**.
- No long-duration run, benchmark comparison, full GPU offload, or high-load stability claim is made. M7 remains limited to its previously accepted conservative scope; this report does not close M7.1.
- The final targeted kernel audit found zero matching fault signatures. Vulkan and ROCm still enumerate Radeon 890M after testing. Kernel, Mesa, libdrm, ROCm/HIP, system XRT, amdxdna module, NPU firmware, and llama.cpp build configuration were not changed; protected package/module versions match the M15 baseline. Exact final inventory is in `evidence/model-evaluation-2026-10-02/platform-after.txt`.

All new run logs, exit codes, resource snapshots, backend device enumeration and per-run kernel audits are in [`evidence/model-evaluation-2026-10-02/`](evidence/model-evaluation-2026-10-02/).
