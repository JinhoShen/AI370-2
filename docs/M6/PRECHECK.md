# M6 Local LLM Foundation — PRECHECK

日期：2026-10-01。目標：在不改系統 GPU/NPU stack 下，使用已保存的 llama.cpp v0.5.0 source 建立 CPU、Vulkan、HIP 三個獨立 build，並分別驗證實際 backend/device。

## Baseline

- M5 Golden tag `ai370-2-npu-golden` 存在；起始 Git working tree clean。
- Host 為 Ubuntu 24.04.4、Kernel `6.17.0-14-generic`、Ryzen AI 9 HX 370 / Radeon 890M `gfx1150`。
- ROCm/HIP 7.2.1、Mesa/RADV 25.2.8、Vulkan loader 1.3.275、CMake/Ninja/GCC 已安裝；`/dev/kfd`、`renderD128`、`accel0` 權限為 `root:render 0660`。
- 起始記憶體約 46 GiB，available 約 43 GiB；swap 8 GiB 空閒。GTT 約 23.3 GiB、VRAM/UMA aperture 16 GiB。根檔案系統約 622 GiB 可用。
- 起始 kernel log 無新增 GPU reset、VM/page fault、ring timeout、TTM corruption 或 soft lockup。保留既有開機訊息，不將它們當作新錯誤。
- 未安裝 Lemonade 或 llama.cpp 套件；此 M6a-c 只用本機 source，build artifact 放 Git ignored `output/M6`。

## Local model inventory and constraint

目前本機只有 Qwen3.6 35B MoE IQ2_M (11.66 GB)、Gemma 4 31B Q4_K_M (18.69 GB) 和 Qwen image projector，沒有 review 提到的小型 text GGUF。GGUF metadata 顯示 text architecture 為 `qwen35moe` / `gemma4`；先確認鎖定 source 支援及模型 SHA，再以 Qwen candidate 做小 context、短輸出 smoke。未證實 parser/backend/model execution 前不宣告 PASS。若架構不支援，記錄模型 gate BLOCKED；不假裝成功或暗中換外部模型。

## Change boundary

僅本機 tarball extract、三個獨立 CMake build、非持久 shell/launcher 設定和 ignored output。禁止 apt transaction、ROCm/Mesa/Kernel/amdxdna/XRT/firmware 變更、GPU/NPU 全域環境變更。先 CPU、再 RADV Vulkan、最後 HIP/gfx1150；每次 GPU smoke 使用有限 offload、短 generation 和小 context，前後比對 kernel journal，出現新 fault 即停止後續 GPU 壓力。
