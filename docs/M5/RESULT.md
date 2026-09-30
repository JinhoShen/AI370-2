# M5 XDNA2 NPU — FAIL / COMPATIBILITY BLOCKED

2026-09-30。**未達實際NPU workload成功、無CPUfallback的PASS條件；不得進下一階段。**

## PRECHECK

使用者核准XRT2.21 userspace，明確禁止DKMS、替換內建amdxdna、混用XRT2.25。保留6.17.0-14 Kernel、NPU firmware1.0.0.63。CP4保存NPU module/firmware/udev/limits與package前清單，位於output/M5/CP4。
審查全部XRT DEB控制腳本；base/npu無driver maintainer scripts；plugin會DKMS/rmmod/modprobe/0666，所以不安裝該DEB。
base-dev會引入uuid-dev並連带13個util-linux套件升級，沒有執行；runtime僅需base/npu與三件現有下載的library，模擬0upgrade/5new/0remove。

## ACTION

安裝xrt-base/xrt-npu2.21.75、libboost-filesystem/program-options1.83.0、ocl-icd-libopencl1。package-diff證明只有5新增，所有既有package版本不變。
從已驗SHA的plugin DEB僅取libxrt_driver_xdna.so userspace payload，放/opt/ai370/npu/xrt21-shim/lib，XRT lib目錄加指向该library的symlink；無複製driver source、firmware或執行plugin scripts。
這是明確分拆的本機驗證路線，非官方whole-package安裝支持聲明。XRT同commit source證明plugin loader掃描libxrt_core所在目錄；只設定LD_LIBRARY_PATH不會註冊plugin。
[XRT 2.21 module loader source](https://raw.githubusercontent.com/Xilinx/XRT/4eb1f4392a012b4e6eca759762389c612537f7c7/src/runtime_src/core/common/module_loader.cpp)

RyzenAI1.7.1已解包本機SDK，使用獨立.venvs/npu21、uv解析並安裝官方本機wheels，torch明確為2.5.1+cpu（SDK編譯/參考用途），未與ROCm PyTorch混環境。一般缺少的Python依賴取自索引，實際版本保存python-freeze.txt。未直接執行install_ryzen_ai.sh；參照其必要環境/voe-min payload，未全域改LD_LIBRARY_PATH。新增SDK Python約25GiB；完整offline wheelhouse尚未建立。

## VERIFY

| 測試 | 結果 | 界線 |
|---|---|---|
| NPU access | PASS | sg render session可讀寫accel0；0660保持 |
| XRT examine | PASS | 2.21.75辨識0000:c6:00.1 RyzenAI-npu4、inboxamdxdna、firmware1.0.0.63 |
| xrt-smi gemm | FAIL / workload not executed | No archive provided；不是硬體compute PASS |
| SDK CNN | FAIL | runner建立遇DRM_IOCTL_AMDXDNA_CREATE_BO -22；Kernel報commandBO0x116b80 too large；沒有成功NPU inference輸出 |
| 小MatMul | FAIL | disabled CPU fallback，runtime拒絕CPU節點 |
| 小QDQ Conv | FAIL | 同樣因CPU節點而被禁止fallback設定拒絕 |
| driver/firmware SHA | PASS | 所有檔案與M5前一致 |
| HIP/Vulkan regression | PASS | 各1024數值正確，見回歸輸出 |

SDK CNN graph曾顯示3個fused node全分配VitisAI EP，但其runner建立失敗，因此不能由placement或session initialized訊息推論NPU真正執行。初版測試另外嚴格拒絕CPU EP被註冊；已修正：CPU EP註冊不等於實際fallback，應以disable_cpu_ep_fallback、實際node profile與device descriptor判斷。原CNN測試的driver錯誤獨立存在，不因這項測試修正消失。

verify/npu_cnn.py已停用ORT CPU fallback、禁止emulation，要求profile所有執行node來自VitisAI與live accel descriptor，並與明確獨立的CPU reference比對。兩個較小測試在session initialization就被阻止，沒有將CPU執行當成功。結果沒有產生cnn-result.json PASS。

## 相容性診斷

本機log的command BO請求0x116b80（約1.09MiB）被driver拒絕。Linux v6.17 upstream source的XDNA_MAX_CMD_BO_SIZE是32KiB，超限回EINVAL，與本機錯誤吻合；這是目前CNN路線的強相容性證據，不證明所有更小/更舊NPU workload都不可能執行。
[Linux 6.17 amdxdna GEM source](https://raw.githubusercontent.com/torvalds/linux/v6.17/drivers/accel/amdxdna/amdxdna_gem.c)
完整examine另出現不支持的GET_INFO parameter4，符合新userspace/舊inbox API缺口；不能把枚舉成功当完整ABI相容。

## PASS CRITERIA / STOP

M5只在真實NPU compute完成、結果正確、無CPUfallback證據充分且regression無新增不可接受問題時PASS。目前**FAIL**，因runtime/inboxdriver配套限制**BLOCKED**；未安裝DKMS、未換Kernel/driver/firmware、未裝2.25、未reboot。沒有跨越重大變更gate，也沒有開始M6。
後續可先研究與inboxdriver相符的2.21 userspace/測試artifact；不得在未有具體證據時聲稱此路線一定可行。若需換driver/Kernel，必須另提相容性/rollback方案並取得獨立批准，現有禁令仍有效。

## ROLLBACK

工作中的GPU stack保留，無回退理由。NPU路線可停相關程序、移除新增SHIM symlink/prefix，先模擬移除5件新userspace套件，保留SDKvenv與log供診斷，或經確認移除venv。不要執行原plugin prerm（本來就未安裝），不rmmod/inboxdriver。CP4 archive與CP0可供需要時恢復；原root破壞性restore另approval。

## DOCUMENT / COMMIT

保存實際來源SHA、package diff、maintainer scripts、Python freeze、模型SHA/小型測試模型、workload完整log、Kernel錯誤、driver/firmware integrity與GPUregression結果。此commit是失敗診斷紀錄，不是PASS milestone。

## 2026-09-30 autonomous follow-up / SER9 reference

已完成安全替代路線、精確套件/firmware比對、隔離 driver build與新CP5；見 [REBUILD_GATE.md](REBUILD_GATE.md)。官方 latency/NOP部分執行PASS，但CNN/GEMM驗證仍失敗、無correctness/no-fallback compute PASS。首選改為RyzenAI1.7.1官方完整2.21配套，停在DKMS/driver/firmware approval gate；M5狀態仍未PASS。

## Approved switch executed

見 [PRE_REBOOT_RESULT.md](PRE_REBOOT_RESULT.md)。Live CNN嚴格compute驗證已PASS；M5整階段狀態為PENDING REBOOT，尚未進M6。
