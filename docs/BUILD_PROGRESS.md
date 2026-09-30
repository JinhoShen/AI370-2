# Build progress

日期：2026-09-30。

| 階段 | 狀態 | 證據 |
|---|---|---|
| M0歷史盤點 | COMPLETE | M0_BASELINE.md；未重跑audit |
| Git / Golden M0 | PASS | main；ai370-2-m0-golden；M0全部SHA重新比對成功；resources未tracked |
| M0.1 recovery foundation | BLOCKED | RECOVERY_CHECKPOINT_PLAN.md；sudo需要人工授權、外接backup目的地未連接 |
| Mesa/Vulkan baseline | NOT RUN | 待recovery checkpoint；不把已載入Mesa當workload PASS |
| ROCm/NPU/FPGA | NOT RUN | 未安裝、更新、修改kernel/driver/permissions |

Git identity僅repo-local自動化名稱，沒有global Git設定修改或remote/push。
Golden tag只代表M0證據，不代表recovery或完整workstation完成。
