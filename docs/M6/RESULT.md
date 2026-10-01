# M6 Local LLM Foundation — RESULT

日期：2026-10-01。狀態：PASS。M5 Golden State 保持不變。

## Build provenance

- llama.cpp 來源為本機 archive `resources/Downloads/LocalAI/llama.cpp/llama.cpp-v0.5.0-7fe450e19305.tar.gz`，SHA-256 `a6861d549427f814dc591c439e08206f67ffaba0248344d421589abf18199e67`，commit `7fe450e19305b828c199d602c23a8337aaa1f03b`。
- 使用 `scripts/build_llama_cpp_m6.sh {cpu,vulkan,hip}` 分別建立三個獨立 build，artifact 位於 ignored `output/M6/build-*`。HIP target 明確指定 `gfx1150`。build 禁止 model/UI fetch 與 test targets。
- Vulkan configure 需要 `spirv-headers`，安裝與 loader 相符的 Ubuntu Noble package `1.6.1+1.3.275.0+git20240228-1`；這是 llama.cpp 唯一 build dependency 的系統安裝。
- 額外安裝本地 Lemonade 2026.39.1 deb 與其 Noble dependencies。沒有升級/移除既有套件；沒有變更 Kernel、ROCm、Mesa、amdxdna、XRT 或 NPU firmware。套件安裝曾觸發一次 llama.cpp UI asset fetch；後續 build 已關閉 UI/prebuilt UI，Lemonade 設定為 offline、no-fetch、停用 broadcast 與自動更新。
- Lemonade 使用 user service，僅綁定 localhost，另設 `MemoryMax=24G`、`MemorySwapMax=0`、`CPUQuota=800%`。三個本機 binary 路徑明確固定於 `/home/shen/AI370-2/output/M6`，CPU 為預設 provider；模型掃描目錄為本機 GGUF 資料夾。使用者設定檔權限 0600。

## Verified workload and results

固定模型：`Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf`，SHA-256 `ba3a1d47a604f17ef74d913f9a9d9a2b456acc6925e7b168bfa2e6527246011c`，Qwen35MoE 35B/A3B IQ2_M，檔案 11.65 GB。這是當時找到的本地文字 GGUF；本機沒有原規劃提到的小型文字 GGUF。

CPU、Vulkan、HIP 各自通過 llama-cli 與 llama-server localhost API 短回覆測試，回覆字串完全等於各 backend 的專屬 marker。每次限定 context 128、batch 16、ubatch 8、8 threads、短輸出；CPU 固定 `--device none --gpu-layers 0`。Vulkan 固定 `Vulkan0` (AMD Radeon 890M Graphics, RADV GFX1150)，HIP 固定 `ROCm0` (AMD Radeon 890M Graphics, gfx1150)，兩者 `--gpu-layers 1`。server log / command line 確認分別執行 Vulkan 與 HIP binary、device 選擇與 1-layer offload；非 CPU fallback 假定。

Lemonade CPU、Vulkan、ROCm 也依序載入同一模型並通過嚴格 API marker 驗證。`lemonade status` 顯示 CPU 或 GPU device；journal 記錄選定 provider/backend 和實際啟動 binary。Vulkan log/argv 使用 Vulkan0，ROCm log/argv 使用 ROCm0。每個 backend 卸載後才測下一個，避免同時保留多份模型。

每次 GPU 測試後的 kernel log 沒有新增 amdgpu page fault/reset/timeout、TTM corruption 或 soft lockup。所有 llama-server 都已清理，Lemonade 僅保留 user service。

## Rebuild / reverify

```bash
scripts/build_llama_cpp_m6.sh cpu
scripts/build_llama_cpp_m6.sh vulkan
scripts/build_llama_cpp_m6.sh hip
scripts/run_llama_server_smoke_m6.sh cpu
scripts/run_llama_server_smoke_m6.sh vulkan
scripts/run_llama_server_smoke_m6.sh hip
```

每個 build 與 smoke 的輸出、server trace、API response、kernel journal 位於 ignored `output/M6/`；本機 GGUF model 由 resource inventory 的 SHA-256 固定。Lemonade system package/config 和受限 user unit 為本機部署狀態，摘要與重建路徑記於本文件，不放入 Git 的機器私有設定。

M6 不代表 M7 benchmark 完成，也不代表 M8 NPU LLM model 已取得或驗證。
