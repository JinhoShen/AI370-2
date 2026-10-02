# Qwen3.8 GGUF candidates — inventory only

Recorded: 2026-10-02 (Asia/Taipei). These models are candidates for a later Local AI evaluation; no model test was run as part of this inventory.

## ACTUAL local file observations

All observed files were under:
`/home/shen/AI370-2/resources/Agent_Tools_Docs/04_Local_AI/GGUF/`

| Model | Observed file size | File mtime at inventory | Status |
|---|---:|---|---|
| `Qwen3.8-27B-UD-Q4_K_M.gguf` | 16,464,440,224 bytes | 2026-10-02 10:51:04 +08:00 | File present; download completeness/integrity not verified |
| `Qwen3.8-27B-UD-Q4_K_XL.gguf` | 17,559,178,144 bytes | 2026-10-02 11:57:42 +08:00 | File present; download completeness/integrity not verified |
| `Qwen3.8-27B-Uncensored-Q4_K_M.gguf` | 4,600,570,891 bytes | 2026-10-02 13:57:57 +08:00 | User reports download is still in progress; observed size is a partial-download snapshot and must not be used as complete-model evidence |

## NOT TESTED / PLANNED

- SHA-256 and final download integrity: NOT TESTED.
- GGUF parser compatibility and metadata (architecture, parameter/tensor counts, quantization): NOT TESTED.
- CPU inference: NOT TESTED.
- Vulkan or ROCm inference: NOT TESTED. These require separate resource guards and staged validation; no Qwen3.8 GPU run is authorized or implied here.
- NPU support: UNKNOWN. These are GGUF files and no claim is made that they are usable on the XDNA2/VitisAI path.

After the third download completes, verify that its size and mtime are stable before hashing or parsing it. Evaluate each model independently, starting with bounded CPU smoke and recording actual backend/device. Preserve the existing M7 conservative-only scope and M7.1 Qwen3.6 Q8 Vulkan issue as OPEN until its own evidence supports a status change.
