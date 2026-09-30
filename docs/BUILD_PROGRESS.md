# Build progress

日期：2026-09-30。

| 階段 | 狀態 | 證據 |
|---|---|---|
| M0歷史盤點 | COMPLETE | M0_BASELINE.md；未重跑audit |
| Git / Golden M0 | PASS | main；ai370-2-m0-golden；M0全部SHA重新比對成功；resources未tracked |
| M0.1 recovery foundation | PASS (file-level scope) | CP0_RESULT.md；本機live archive與selected-file restore通過，full boot/disk recovery未測 |
| Mesa/Vulkan baseline | PASS | M2_CORE_M4_RESULT.md；1024 GPU shader數值正確；Mesa/driver未替換 |
| M2 developer foundation | PASS (CLI/venv/IDE CLI) | M2_PYTHON_IDE_RESULT.md；GUIdebug未測 |
| M3 ROCm | PASS | docs/M3/RESULT.md；HIP數值與Vulkan回歸PASS；既有package未升級 |
| M5 NPU | FAIL / COMPATIBILITY BLOCKED | docs/M5/RESULT.md；XRT2.21枚舉成功，CNN commandBO被inboxdriver拒絕；無成功compute或CPUfallback PASS |
| FPGA | NOT RUN | 2026.1 OS compatibility gate保留 |

Git identity僅repo-local自動化名稱，沒有global Git設定修改或remote/push。
Golden tag只代表M0證據，不代表recovery或完整workstation完成。

使用者改選本機checkpoint，不使用T7。已提供完整sudo施工權限；Kernel/DKMS/driver/XRT/FPGA OS等重大變更gate仍保留。
