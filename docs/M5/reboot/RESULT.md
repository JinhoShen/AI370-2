# M5 post-reboot result — FAIL / CP5 RECOVERED

2026-09-30。開機服務已執行既定驗證並自動回復；沒有在本次人工核對重新安裝或變更版本。

重開機驗證的 DKMS module 來源為 updates/dkms，版本 2.21.260102.53.release_20260309；XRT 2.21.75 辨識 RyzenAI-npu4（XDNA2），實際 firmware 1.1.2.64。
CNN 10 次 inference PASS：停用 CPU fallback、profile 的執行節點全為 VitisAIExecutionProvider、NPU hardware time 增加 14,719,188 ns，與獨立 CPU reference 最大絕對誤差 0。原始 profile 已保存至 ort-profile.json。CPU EP 註冊不代表實際 fallback。
HIP 與 Vulkan 在回復前、回復後，以及本次重新執行皆 PASS，各驗證 1024 筆結果。

最終 kernel gate 匹配到 `amdxdna: module verification failed: signature and/or required key missing - tainting kernel`，觸發既定 FAIL 與 CP5 recovery。這行是 module signature / trust 警告；不能由此聲稱 NPU compute 失敗。未修改既定 gate 或將回復後狀態改標 M5 PASS。

CP5 腳本已移除指定 plugin/DKMS，恢復 inbox module、原 firmware、SHIM 與 initramfs；archive、module、firmware SHA 核對成功。現況 modinfo 來源為 kernel/drivers/accel/amdxdna，XRT firmware 1.0.0.63，無 pending reboot verification。詳細見 rollback.txt 與 recovery-current-*。
本次回復後尚未再次 reboot，因此回復 initramfs 的下一次開機驗證仍未完成；不宣稱完整 boot recovery 已驗證。M5 保持 FAIL / CP5 recovered，未進 M6。
