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
| M7 Qwen3.6-35B-A3B Q8_0 model smoke | DOWNLOAD / SHA256 / GGUF metadata / CPU inference VERIFIED; Vulkan FAILED; ROCm inference DEFERRED | docs/M7/QWEN36_Q8_SMOKE.md；低負載 smoke 專項，不代表高負載/穩定性 PASS；Vulkan RADV command submission error 後停止 GPU 測試 |
| M8 NPU Local AI evaluation | DEFERRED (local ONNX PASS) | docs/M8/RESULT.md；VitisAI-only CNN 正確性/硬體 counter 通過；NPU LLM 權重不在本機；tiny unsupported graphs 未冒充 PASS |
| M9 native route | INSTALLED; SOFTWARE TOOLCHAIN PASS | docs/M9/LICENSE_UNLOCKED_VALIDATION.md；Vivado/Vitis/Vitis Embedded/HLS 2026.1 installed natively; active Enterprise license; OS support is not claimed |
| M9 Vivado/Vitis/HLS validation | PASS | docs/M9/LICENSE_UNLOCKED_VALIDATION.md；SP701 board/device recognition, Vivado RTL synthesis/utilization and Vitis HLS synthesis all passed |
| M9 protected-stack regression | PASS | docs/M9/LICENSE_UNLOCKED_VALIDATION.md；HIP/Vulkan 1024-result checks and VitisAI-only NPU CNN passed; XRT/NPU/firmware versions preserved |
| M9 Acceleration components | INSTALLED / VERIFIED / DEFERRED | docs/M9/ACCELERATION_INSTALL_RESULT.md；Vitis acceleration CLI and 8 embedded platforms verified; FPGA card runtime/XRT host API remain deferred |
| M9 board definitions | VERIFIED | docs/M9/LICENSE_UNLOCKED_VALIDATION.md；Vivado recognizes Xilinx SP701 and Digilent Arty A7-35; Spartan-7 device support added and used in synthesis |
| M11 FPGA hardware validation | DEFERRED | Hardware Manager found no connected JTAG target; no bitstream programming or live hardware result claimed |

Git identity僅repo-local自動化名稱，沒有global Git設定修改或remote/push。
Golden tag只代表M0證據，不代表recovery或完整workstation完成。

使用者改選本機checkpoint，不使用T7。已提供完整sudo施工權限；Kernel/DKMS/driver/XRT/FPGA OS等重大變更gate仍保留。
