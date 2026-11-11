# 階段驗收紀錄：Local Model Lab 測試、可靠性與 harness 修正（2026-11-11）

**結論：通過。** 驗收時 commit 為 `a85cc10`，與 `origin/main` 一致，無未提交變更。

## 機器狀況（2026-11-11 14:34 CST）

| 項目 | 狀態 |
|---|---|
| 開機 | 2026-11-09 17:11 起未重開（約 1 天 21 小時） |
| CPU | AMD Ryzen AI 9 HX 370，24 核心，load 1.6，37°C |
| 記憶體 | 46 GiB，可用 37 GiB；swap 使用 0；memory PSI 0 |
| GPU | Radeon 890M，使用率 10%，VRAM 0.8／16 GiB |
| 磁碟 | `/` 使用 78%，可用 199 GiB；`output/` 8.4 GiB |
| Kernel | 開機以來 amdgpu fault／reset 0 次，OOM 0 次 |
| 桌面 | 2026-11-11 重新登入後無新當機；`/var/crash` 保留 2026-11-09 的 gnome-shell、VS Code、node crash report |

| 服務 | 狀態 |
|---|---|
| `ai370-local-model-controller`（user service） | active，2026-11-11 13:39 起載入最新程式；重啟後 114 筆 telemetry，0 筆 `health_error` |
| Local Agent UI（127.0.0.1:13306） | HTTP 200 |
| Lemonade（127.0.0.1:13305） | 正常，未載入 LLM |
| Embedding llama-server | 2026-11-09 起運作 |
| systemd | 無失敗的 system／user 服務 |

controller 狀態 `MONITORING`；quality 狀態 `SAFETY_STOP`（2026-11-06）；凍結計畫僅有 `20261103T065105Z`。

## 驗收項目

| 項目 | 結果 |
|---|---|
| 離線測試 | 16 個測試檔、321 個測試全部通過；同日以 fresh clone 模擬（無 `output/`、無權重）亦全部通過 |
| 實際工具驗證 | Vivado 2026.1／Vitis HLS 2026.1 執行 `validate_quality_corpus.py --task all`：corpus v1（`5e3fe5c`）與 v2（`7aa8057`）皆 24／24 PASS |
| controller | SIGTERM 後 0.1 秒內正常結束（實測，舊版 27.1 秒）；健康資料不可讀時 fail-closed |
| harness | guard 優先序、來源改動判 FAIL、protocol／HEAD／ignored 檔案檢查、工具逾時判 FAIL、可編輯檔以 protocol 為準；皆有回歸測試，並確認在舊版失敗 |
| 題庫 | corpus v2 修正 T8 介面規格；v1 的 T8 樣本重新分類為 `HARNESS_INVALID`，原始證據未改（見 `T8_SPEC_DEFECT.md`） |
| 文件 | `QUALITY_VALIDATION_PLAN.md` 第 13 節 |

## 未結事項

1. 開始下一批評測：需先封存目前 `SAFETY_STOP` 的 quality 狀態（不得覆寫證據），再以 controller `arm-pilot` 用新 harness 與 corpus v2 啟動新的 V1 pilot（72 個樣本）。
2. T6 非逾時的 C simulation 失敗仍使用同一句 vector mismatch 診斷。
3. AnyDesk 在 `0.0.0.0:7070` 接受直接連線；不需要區網直連時可在 AnyDesk 設定關閉。
4. 以 AnyDesk 遠端操作時不要切走 KVM：2026-11-09 23:42 GNOME Shell 因此當機（mutter `logical_monitor` assertion）。
5. `/var/crash` 的三份 2026-11-09 crash report 可回報 Ubuntu 或刪除。
