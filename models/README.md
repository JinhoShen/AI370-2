# AI370-2 Local Models

`/home/shen/AI370-2/models/` is the flat, canonical location for local inference weights and auxiliary model payloads. GGUF, ONNX, TFLite, Whisper, Kokoro, Stable Diffusion, and wake-word assets are listed in `MODEL_INVENTORY.tsv`. The `GGUF -> .` symlink preserves existing Lemonade, UI, and runner paths.

## Preserved compatibility paths

- `Legacy_Cache/Qwen_Cache/` retains the original cache metadata and directory structure. Repeated SER9 model payloads were SHA256-verified and converted to hard links to one canonical root file; no model bytes were deleted. The original `SER9-Qwen-Models.tar` archive remains in `Legacy_Cache/Qwen_Cache/`.
- `Ross_Offline_Resources/` retains Ross embedding archives. The extracted embedding GGUF is in the flat model root, with a compatibility symlink at its former path.
- Former `resources/Agent_Tools_Docs/04_Local_AI/GGUF`, Lemonade cache, and Ross paths remain compatibility links.

## T7 import (2026-10-20)

Twenty-one previously absent model payloads were copied from T7 into this directory. Each copy was verified by exact byte size and SHA256. The local checksum log is `output/model-import/t7-model-import-2026-10-20.tsv` (ignored by Git). T7 source files were retained. The T7 Qwen3.6-35B-A3B-Q8 file was subsequently confirmed truncated. Replacement failed due to insufficient T7 capacity, and the incomplete T7 file was deleted. The local copy passes tensor-range validation; publisher checksum verification remains outstanding. Copy verification does not establish backend compatibility or inference readiness.

## Disk organization

Nineteen primary GGUF payloads were physically moved into this root; `GGUF/<filename>` continues to resolve through the compatibility symlink. Four legacy Qwen payloads have canonical root copies. Six verified-identical legacy cache instances now share hard-linked payloads, preserving all old cache paths while reclaiming approximately 48.2 GB of duplicate blocks. The desktop Trash was observed empty during the latest disk check.

## Browse models

See [CATALOG.md](CATALOG.md) for a categorized list of the canonical model files and backup notes.
