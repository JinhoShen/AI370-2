# Build progress

日期：2026-09-30。

| 階段 | 狀態 | 證據 |
|---|---|---|
| M0歷史盤點 | COMPLETE | M0_BASELINE.md；未重跑audit |
| Git / Golden M0 | PASS | main；ai370-2-m0-golden；M0全部SHA重新比對成功；resources未tracked |
| M0.1 recovery foundation | PENDING REVIEW | 本機CP0已建立；SHA與selected-file restore通過；tar stderr待檢查，full boot restore未測 |
| Mesa/Vulkan baseline | PRECHECK ONLY | Radeon890M/RADV GFX1150枚舉成功；compute未測，見M4_VULKAN_PRECHECK.md |
| ROCm/NPU/FPGA | NOT RUN | 未安裝、更新、修改kernel/driver/permissions |

Git identity僅repo-local自動化名稱，沒有global Git設定修改或remote/push。
Golden tag只代表M0證據，不代表recovery或完整workstation完成。

使用者改選本機checkpoint，不使用T7。已提供僅限checkpoint verifier的sudo權限；其他系統管理權限未開放。
