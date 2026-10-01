# Build progress

日期：2026-10-01。

| 階段 | 狀態 | 證據 |
|---|---|---|
| M0歷史盤點 | COMPLETE | M0_BASELINE.md；未重跑audit |
| Git / Golden M0 | PASS | main；ai370-2-m0-golden；M0全部SHA重新比對成功；resources未tracked |
| M0.1 recovery foundation | PARTIAL (same-disk file-level checkpoint) | CP0_RESULT.md；2026-10-01 root/EFI SHA與selected-file restore通過；off-device/full boot restore未測 |
| Mesa/Vulkan baseline | PASS | M2_CORE_M4_RESULT.md；1024 GPU shader數值正確；Mesa/driver未替換 |
| M2 developer foundation | PASS (CLI/venv/IDE CLI) | M2_PYTHON_IDE_RESULT.md；GUIdebug未測 |
| M3 ROCm | PASS | docs/M3/RESULT.md；HIP數值與Vulkan回歸PASS；既有package未升級 |
| M5 NPU | PASS | docs/M5/reboot/STATUS；重開機後DKMS/firmware、CNN正確性、硬體usage、no-fallback及HIP/Vulkan通過 |
| M6 Local LLM foundation | PASS | docs/M6/RESULT.md；本地 llama.cpp CPU/Vulkan/ROCm 獨立 build 與 CLI/server/Lemonade 實際 backend 短測通過；M5 stack 未改 |
| M7 Local LLM benchmark | PASS (conservative baseline) | docs/M7/RESULT.md；本地 GGUF/context64 CPU/Vulkan/ROCm 三次 prefill/decode、RSS/GTT/VRAM/swap/kernel log；未做高壓長測 |
| M8 NPU Local AI evaluation | DEFERRED (local ONNX PASS) | docs/M8/RESULT.md；VitisAI-only CNN 正確性/硬體 counter 通過；NPU LLM 權重不在本機；tiny unsupported graphs 未冒充 PASS |
| M9 native route | USER-DECIDED; PRE-INSTALL CHECKPOINT VERIFIED; APT GATE BLOCKED | docs/M9/NATIVE_INSTALL_DECISION.md；Ubuntu 24.04.4 host; solver proposes Mesa/RADV upgrades; no package installed and installer not launched |
| M9 Vivado/Vitis/HLS validation | NOT STARTED — GATED | 先解決受保護 Mesa stack transaction；VM route history preserved；M9 not PASS |
| FPGA | NOT RUN | 尚未開始 Vivado synthesis 或硬體驗證 |

Git identity僅repo-local自動化名稱，沒有global Git設定修改或remote/push。
Golden tag只代表M0證據，不代表recovery或完整workstation完成。

使用者改選本機checkpoint，不使用T7。已提供完整sudo施工權限；Kernel/DKMS/driver/XRT/FPGA OS等重大變更gate仍保留。
