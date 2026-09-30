# AI370 2 — 補充安裝資源下載完成

日期：2026-09-30。目錄：`/home/shen/AI370-2/resources/Downloads`。
這輪只下載、保存文件與驗證檔案，未安裝套件、更新系統、
修改套件來源、Kernel、BIOS、驅動或裝置權限。

## 結果

整合去重後共 489 個檔案、9.112 GiB。所有本機檔案重新讀取
SHA256 一致；有發布 SHA256 的套件也已比對通過。
Wheel/VSIX 通過 ZIP CRC，原始碼 TAR/GZIP 通過串流讀取檢查，
DEB 通過格式標頭檢查。無失敗下載、`.part` 或分段殘留檔。
軟體庫 Packages 索引另存於各資源的 metadata 目錄。

## 已準備

- AMD ROCm 7.2.1：86 個 ROCm 套件與 amdgpu-install 下載入口。
- GPU Python：官方 ROCm 7.2.1 / Python 3.12 的 PyTorch 2.9.1、
  torchvision 0.24.0、torchaudio 2.9.0、Triton 3.5.1 wheel。
- Ubuntu 24.04：CMake、Ninja、Python pip/venv、Git LFS、Vulkan
  開發與診斷工具、OpenCL 診斷、C/C++ 相依套件及 ROCm/Lemonade
  所需的依賴套件。本機現有 APT 索引只供解析，未 apt update。
- VS Code 1.139.1 AMD64 DEB；穩定版 Python 2026.6.0、Pylance
  2026.4.1、debugpy 2026.6.0、C/C++ 1.34.4、CMake Tools 1.24.42 VSIX。
- uv 0.12.21 Linux x86_64 發行壓縮包與官方 checksum。
- llama.cpp v0.5.0 固定 commit 原始碼壓縮包與該 commit 建置文件。
- Lemonade：官方 stable PPA 的 Ubuntu 24.04 套件與庫中相關套件，
  主程式版本 2026.39.1~24.04；未使用 Debian 13 DEB。
- FPGA：XilinxBoardStore、Digilent vivado-boards、Vitis Embedded
  Platform Source 固定 commit 原始碼。具體版本見下載 manifest。
- 官方 Ryzen AI、ROCm、Lemonade、VS Code 文件離線副本；
  Ubuntu 24.04.1 官方 SHA256SUMS 與簽章檔。ISO 與發布 SHA256 一致，
  簽章已保存但本輪未做 GPG 簽章驗證。

初次 Marketplace API 的 latest 候選檔案移至
`DevTools/VSCode/Extensions/Prerelease-Archive` 作查詢紀錄，
不作預設安裝來源；正式準備的五個 VSIX 在 Extensions 直接目錄。

## 驗證與追溯

- `download-verification.json`：整合檔案大小、來源 URL、版本、SHA256、
  發布雜湊與檔案格式檢查結果。
- `SHA256SUMS.downloads`：路徑相對於 Downloads 的本機清單。
- `download-plan.json`、各 `download-*-results.json`：原始下載紀錄。
- `download-resume.log`：主要清單最終 466/466 完成紀錄。
- `ubuntu-published-sha256.json`：Ubuntu 來源索引的 SHA256。
- `rocm-dependency-review.json`：預定套件版本加上現有已安裝系統
  的宣告依賴靜態比對，未發現未滿足項目。這不是安裝或執行驗證。

初次下载腳本途中切換到分段續傳；`download-progress.log` 因此不是
最終完成紀錄。分段回應檢查 HTTP 206、Content-Range 與精確長度，
組裝後仍核對 SHA256，最後重新讀取檔案並檢查格式。

## 尚待準備與安裝前確認

1. Ryzen AI NPU LLM：官方參考模型
   `amd/Phi-3.5-mini-instruct_rai_1.7.1_npu_4K` 的 Hugging Face
   連線多次被重設，本輪未取得模型。現有 GGUF 不等於這項 NPU 模型。
2. 舊機最新專案備份：本機既有 bundle 與較新故障紀錄的 commit
   不一致，需要從舊機补齊，不能靠公開下載取得。
3. FPGA 不限定型號，已準備通用工具與板卡資料來源；特定板卡的
   BSP、預建平台/映像與商用授權在選板後配套準備。原始碼的固定
   commit 不代表已與 Vivado/Vitis 2026.1 或所有板卡驗證相容。
4. SDK/PyTorch 的完整 Python wheelhouse 尚未解析齊全；正式安裝
   仍可能需取用 PyPI 等網路來源。本機資源不依賴 T7，不代表已能
   完全離線重建全部開發環境。
5. 正式安裝前逐階段做依賴模擬與版本檢查，特別核對 ROCm 文件中
   OEM Kernel 路線與目前 6.17 HWE、內建 amdgpu/amdxdna 的搭配。
   本轮未變更 Kernel，也未驗證 GPU/NPU 運算或 FPGA 工具執行。

## 官方來源

- https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2.1/
- https://ryzenai.docs.amd.com/en/1.7.1/linux.html
- https://lemonade-server.ai/docs/guide/install/ubuntu/
- https://code.visualstudio.com/docs/setup/linux
- https://github.com/ggml-org/llama.cpp
- https://github.com/astral-sh/uv
- https://github.com/Xilinx/XilinxBoardStore
- https://github.com/Digilent/vivado-boards
- https://github.com/Xilinx/Vitis_Embedded_Platform_Source
