# Local model evaluation — 2026-10-02

Status: **IN PROGRESS**. This is bounded availability testing, not a long benchmark or a claim of sustained stability. Each inference used the CPU-only llama.cpp binary, context 64, a two-token output limit, four CPU threads, `--device none`, `--gpu-layers 0`, and a systemd cgroup with swap disabled. Tests ran sequentially.

## CPU smoke results

| Model | Actual file / source | Parsed metadata | CPU smoke | Evidence |
|---|---|---|---|---|
| Qwen3.5-9B UD Q4_K_XL | `resources/Agent_Tools_Docs/04_Local_AI/Lemonade/Qwen_Cache/SER9-Qwen-Models (2)/models--unsloth--Qwen3.5-9B-GGUF/snapshots/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-UD-Q4_K_XL.gguf`; 5,966,095,584 bytes; SHA256 `6f5d30666c2d8ae16a306e616d95341dcf3cc46810df84d7e6f5a7d1e4c1b293` | `qwen35`, 8.95B parameters; parser reports Q4_K Medium | **PASS**, exit 0; 2 tokens; 8.9 tok/s; peak RSS 7,624,192 KiB; 0 swaps | `evidence/model-evaluation-2026-10-02/qwen35-9b-*` |
| Qwen3-14B Q4_0 | `Lemonade/Qwen_Cache/SER9-Qwen-Models.tar`, member `models--unsloth--Qwen3-14B-GGUF/snapshots/a04a82c4739b3ef5fa6da7d10261db2c67dd1985/Qwen3-14B-Q4_0.gguf`; extracted temporarily to `/tmp`; 8,543,001,984 bytes; model SHA256 `009f54ffc8d8082e7921139924229d4deea61c9174a0a357d91384bd299ff78e` | `qwen3`, 14.77B parameters, Q4_0 | **PASS**, exit 0; 2 tokens; 7.0 tok/s; peak RSS 15,426,464 KiB; 0 swaps | `evidence/model-evaluation-2026-10-02/qwen3-14b-*`; archive SHA256 verified from its sidecar |
| Qwen3.8-27B UD Q4_K_M | `04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_M.gguf`; 16,464,440,224 bytes; SHA256 `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482` | `qwen35`, 27.32B parameters, Q4_K Medium | **PASS**, exit 0; 2 tokens; 3.1 tok/s; peak RSS 18,589,188 KiB; 0 swaps | `evidence/model-evaluation-2026-10-02/qwen38-q4km-*` |
| Qwen3.8-27B UD Q4_K_XL | `04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf`; 17,559,178,144 bytes; SHA256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` | `qwen35`, 27.32B parameters; parser reports Q4_K Medium | **PASS**, exit 0; 2 tokens; 3.0 tok/s; peak RSS 18,930,832 KiB; 0 swaps | `evidence/model-evaluation-2026-10-02/qwen38-q4kxl-*` |
| Qwen3.8-27B Uncensored Q4_K_M | `04_Local_AI/GGUF/Qwen3.8-27B-Uncensored-Q4_K_M.gguf`; 16,810,714,528 bytes; SHA256 `4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675` | `qwen35`, 27.32B parameters, Q4_K Medium | **PASS**, exit 0; 2 tokens; 2.9 tok/s; peak RSS 25,708,928 KiB; 0 swaps | `evidence/model-evaluation-2026-10-02/qwen38-uncensored-*` |

The Qwen3-14B archive checksum matched `SER9-Qwen-Models.tar.sha256`. Its extracted test copy is temporary; this does not modify the archive. The repeated Lemonade cache directories contain copies of the same Qwen3.5-9B file, so only one representative copy was tested.

## Existing evidence and remaining tests

- Qwen3.6-35B-A3B Q8_0: earlier bounded CPU smoke is PASS with SHA256 `d8d7842cc657d720f39546878e431937c84473aa130c36371669ac17c80c7361`; not rerun here.
- Qwen3.6 Q8 Vulkan failure: **not rerun**; M7.1 remains **OPEN**.
- Gemma 4 31B Q4_K_M and Qwen3.6 uncensored IQ2_M: CPU smoke **PENDING**.
- Qwen3.5-9B, Qwen3-14B, Qwen3.8 models: Vulkan/ROCm inference **NOT RUN** yet. Backend readiness is separate from model inference.
- NPU evaluation of these GGUF models: **NOT TESTED**.

No kernel, GPU, ROCm, Mesa, XRT, NPU driver, firmware, or llama.cpp build configuration was changed. No M7 high-load or long-duration stability result is claimed.
