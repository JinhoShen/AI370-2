# AI370 2 本機安裝資源

來源：`/media/shen/T7/Agent_Tools_Docs`。
本機：`/home/shen/AI370-2/resources/Agent_Tools_Docs`。

本次僅複製資源與驗證 SHA256，未執行安裝包、更新系統或更改驅動。

保留 Ubuntu 復原 ISO、Vivado/Vitis 2026.1 TAR、Ryzen AI 1.7.1 TGZ、
XRT ZIP 與四個 DEB、Qwen 模型快取 TAR、三個非空 GGUF、文件、
歷史專案 bundle、舊機盤點與故障紀錄、原始 checksum。

未複製 FPGA 與 Ryzen AI 已解開的重複副本、Gemma Q3 零位元組檔案、
Windows 啟動文字及空目錄。T7 原件不刪除、不修改。

## 完整性紀錄

`resource-manifest.json` 記錄來源相對路徑、大小與預期 SHA256。
`copy-verification.json` 記錄本機副本的實際 SHA256 與比對結果。
`SHA256SUMS.local` 是本機驗證完成後產生的清單，路徑相對於資源根目錄。
`copy-progress.log` 記錄複製及驗證過程。

Git bundle 的原始總清單 hash 與獨立 `.sha256` 有衝突；本次使用已與
來源實際 hash 一致的獨立 `.sha256`。保留原始矛盾紀錄，不修改來源。
Bundle 的 main 為 dc94da9，但故障紀錄引用 95effc6；尚不能認定備份
涵蓋舊機最新提交。零位元組 Gemma Q3 必須重新取得。

雜湊一致確認本機副本符合此次來源紀錄，不等於官方來源認證、
安裝成功或模型推論成功。壓縮包解開副本未逐檔驗證，因此採用原始包。

## 尚待準備

2026-09-30 已補下載通用安裝資源，最新狀態見
`DOWNLOAD_PREPARATION.md` 與 `download-verification.json`。
下列清單保留為 T7 初次盤點時的缺項紀錄。

ROCm/HIP 安裝套件與配套 GPU Python 套件、llama.cpp 固定版本原始碼、
Vulkan 開發及診斷工具、CMake/Ninja/Python venv/pip/uv、VS Code、
Lemonade 主程式、Ryzen AI 配套 NPU LLM 模型、FPGA 板卡 platform/BSP
及適用授權、舊機最新 Git 備份與官方 checksum 文件。

Ryzen AI 安裝脚本會取用網路依賴；現有資源不代表完整離線安裝環境。
舊機資料只能作歷史參考，新工作站需重新驗證 GPU/NPU/FPGA 與穩定性。
