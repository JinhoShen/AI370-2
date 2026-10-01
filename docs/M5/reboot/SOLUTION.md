# M5 post-reboot false negative：處理紀錄

## 問題

第一次 post-reboot 驗證中，NPU workload 已成功，但 verifier 把 kernel 的 module signature 訊息當成致命錯誤並啟動 CP5 rollback。當時 Secure Boot 為 disabled；指定的 DKMS `amdxdna` module 已載入。這是 verification-policy false negative，不是 NPU compute 或 M5 workload failure。

## 恢復與修正

1. 先完成 CP5 recovery，恢復原 inbox module、firmware、XRT shim 和 initramfs，並核對 checkpoint、module、firmware 的 SHA。確認裝置回到 CP5 後才重新套用已批准的組合；沒有重做相容性研究。
2. 修正 `verify/m5_kernel_policy.py`：只有在 Secure Boot disabled 且 `/sys/module/amdxdna/version` 顯示指定 `2.21.260102.53.release` 時，對 `module verification failed: signature and/or required key missing` 記錄 `WARNING`。其他情況仍視為失敗。driver ERROR、timeout、fault、failed，以及 GPU reset/VM fault/ring timeout 仍列為功能性失敗。
3. 修正 `scripts/verify_m5_after_reboot.sh`，先驗證新 boot ID、Kernel、DKMS module 來源與版本，再檢查 XRT/NPU/firmware、CNN 真正的 VitisAI node 與 NPU hardware time、停用 CPU fallback、CPU reference 輸出一致性，以及 HIP/Vulkan regression。任何功能 gate 失敗仍執行 CP5 rollback。
4. 重新安裝指定 XRT 2.21/DKMS `2.21.260102.53.release` 與 firmware `1.1.2.64`，重開機並執行完整驗證。結果全部通過後才寫入 M5 PASS 並建立 Golden State。

## 最終驗證

- Secure Boot：disabled；module signature 訊息列為 WARNING。
- XRT 2.21 偵測 NPU `0000:c6:00.1`，firmware `1.1.2.64`。
- CNN：10 次 inference 均由 VitisAI 執行、CPU fallback disabled、NPU hardware time 增加、CPU reference 最大絕對誤差為 0。
- HIP 與 Vulkan：均 PASS。
- M5 PASS commit：`849377c8f2da4c8cc230fc97c1c12fb800899d48`；tag：`ai370-2-npu-golden`。

原始誤判與 CP5 recovery 證據在 [`../retry/previous-policy-false-negative/`](../retry/previous-policy-false-negative/)；最終逐項輸出見本目錄的 `verification.txt`、`kernel-policy.txt`、`xrt-examine.txt`、`cnn-result.json`、`hip.txt` 和 `vulkan.txt`。
