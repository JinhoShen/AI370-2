# M5 — SER9 reference / compatibility decision gate

日期：2026-09-30。狀態：**APPROVED TO EXECUTE；M5 尚未 PASS**。

## 結論與證據界線

首選重建組合：保持 Ubuntu 24.04.4、Kernel 6.17.0-14、Mesa/RADV、ROCm 7.2.1；NPU 使用 XRT 2.21.75 + xrt-amdxdna DKMS 2.21.260102.53.release + 套件附帶的 17f0_10 firmware 1.1.2.64 + Ryzen AI 1.7.1。目前 ONNX Runtime 實際版本以 python-freeze.txt 為準（1.23.3 開發版本），不得用舊機版本覆寫本機證據。

使用者提供的 SER9 記錄是相同 HX370/XDNA2 在 Ubuntu 24.04.4 / Kernel 6.17.x 曾安裝及辨識此組合的 reference，未提供可在本機繼承的 workload correctness / no-fallback PASS。

[AMD Ryzen AI 1.7.1 Linux installation](https://ryzenai.docs.amd.com/en/1.7.1/linux.html) 明列目前本機四個 XRT/plugin 檔名，要求 Ubuntu 24.04 LTS、Kernel >=6.10、Python 3.12，並以 CNN quicktest 驗證。這確認指定 driver 套件配套，不能推論每個 6.17 Ubuntu patch kernel 已完成官方測試。

本機 plugin 的 version.json 記錄 XRT build 2.21.75、XRT commit 4eb1f4392a012b4e6eca759762389c612537f7c7、driver commit 6f881ad230142b707ca8ce5b33fca426a926c551。dkms.conf 記錄 PACKAGE_NAME=xrt-amdxdna、PACKAGE_VERSION=2.21.260102.53.release；DEB 本身 Package=xrt_plugin-amdxdna、Version=2.21，不要把這三種 version 混為一談。

套件 payload usr/lib/firmware/amdnpu/17f0_10/npu.dev.sbin 含 Release 1.1.2.64；npu4_regs.c 指定載入此路徑。它確實是同一套件附帶的 firmware，不必另找或下載。字串是 payload 證據；切換後還須用 XRT/driver 確認實際載入版本。

## PRECHECK：既有資源

四個 DEB 全部與 docs/SHA256SUMS.local 逐件重算匹配，見 research/resource-verification.json。現有 ryzen_ai-1.7.1.tgz 與已建立 .venvs/npu21 沿用先前 SHA/環境驗證，沒有重新下载 SDK。xrt-base / xrt-npu 已是 2.21.75；base-dev 雖在資源中，但 runtime 驗證不需要，仍不安裝其會升級 util-linux 的依賴閉包。

DKMS 工具目前未安裝；APT simulation 是 dkms 3.0.11-1ubuntu13，1 new / 0 upgrades / 0 removals。對應 kernel headers 已存在；Secure Boot disabled。已在 output/M5/plugin-inspect 隔離編譯原套件 driver：configure feature probes + make 成功，modinfo vermagic=6.17.0-14-generic，driver version 符合指定 release。沒有 make install / DKMS register / modprobe / firmware copy；編譯成功不等於實際載入及穩定性 PASS。BTF 因未提供 vmlinux 而略過，編譯並未失敗。

資源中另有 Lemonade 的 XRT 2.25 與不同 amdxdna-dkms；此路線不使用、不混装。

調查時曾從官方 VTD 2.21.75 tag 取得 36 MB archive，隨後確認同一 archive 已在既有 plugin DEB 內，SHA256 完全相同。這次重複取得已記錄；後續重建直接用既有 plugin payload，不再下載它。

## ABI / execution 差異

|項目|Linux v6.17 upstream / 本機行為|既有 AMD plugin 原始碼|
|---|---|---|
|Command BO|XDNA_MAX_CMD_BO_SIZE=SZ_32K；本機 0x116b80 請求被 create_cmd_bo 拒絕|amdxdna_gem.c CREATE_BO 將 CMD/SHARE 都交 create_share_bo，沒有同一 32 KiB command-only 檢查|
|ERT execution|ctx.h / message dispatcher 支援 START_CU=0、CMD_CHAIN=19、START_NPU=20|另外支援 START_NPU_PREEMPT=21、START_NPU_PREEMPT_ELF=22，執行時另檢查 firmware preemption feature|
|HWCTX / memory ABI|實測 GEMM CONFIG_HWCTX 返回 -95；legacy CNN copy exec_buf 不支持|較新的 HWCTX/BO/import/debug 等介面；詳細差異由 package source 保留，不能只放寬一個大小就宣稱相容|
|Firmware 路徑|目前 npu.sbin.zst -> 1.0.0.63|npu.dev.sbin，套件 payload 1.1.2.64|

[Linux v6.17 GEM implementation](https://raw.githubusercontent.com/torvalds/linux/v6.17/drivers/accel/amdxdna/amdxdna_gem.c) 與 [command definitions](https://raw.githubusercontent.com/torvalds/linux/v6.17/drivers/accel/amdxdna/amdxdna_ctx.h) 作比較參考；Ubuntu 可能有 backport，因此本機錯誤、module SHA 與套件內實際 source 更重要。上述差異充分解釋目前 SDK 預設路線失敗，並支持改用官方完整配套；不證明所有自製小型 workload 在 upstream 上均不可能運行。

## ACTION / VERIFY：已完成的安全方案

|方案|實際結果|判定|
|---|---|---|
|XRT 2.21 userspace + plugin SHIM，inbox driver|XRT 辨識 XDNA2|枚舉 PASS，compute 未證明|
|SDK CNN 預設 ELF/preempt|command BO 約 1.09 MiB 超限|-22 FAIL|
|小 MatMul / QDQ Conv|算子無法全放 VitisAI；disable_cpu_ep_fallback 阻止執行|FAIL，沒有拿 CPU 當成功|
|SDK private config 關閉 ELF/preempt，X2 / X1|session/runner 前進，但 bank 0 vs 65537 copy 路徑失敗；exec_buf unsupported，No host side buffer|FAIL，不變更 SDK 全域設定|
|VAIML small model private config|CPU placement 被禁止 fallback 阻止|FAIL|
|官方 VTD 2.21.75 GEMM|已取得正確 archive；CONFIG_HWCTX -95|FAIL，不再誤判成缺 archive|
|官方 VTD latency / NOP|Average latency 49.0 us，test PASSED|部分 NPU 命令執行成功；沒有運算輸出 correctness，**不是 M5 PASS**|
|隔離編譯指定 DKMS|build / vermagic 正確|build precheck PASS，未安裝/載入|
|HIP / Vulkan regression|各 1024 數值正確|PASS|
|inbox module / firmware SHA|與 M5 前一致|PASS；未修改 Kernel / driver / firmware|

不再把 SDK1.7.1 的完整配套拆成僅 SHIM 就視為官方支持。對此 SDK 的完整 CNN/no-fallback 驗證，建議下一步是已確認配套的 driver/firmware 切換；繼續猜測 undocumented buffer flags 或抑制必要 ioctl 無法提供可靠 correctness 證據。

## Recovery checkpoint

- CP0：output/recovery/CP0-20260930T084329Z，全 root/EFI live file-level archives；已驗 SHA、selected restore，全文件開機還原未測。
- CP4：output/M5/CP4/npu-config.tar，NPU 前置 config、firmware、inbox module；SHA 已有。
- 新 CP5：output/recovery/CP5-NPU-GATE-20260930T095450Z。保存 /etc、/boot kernel/initramfs、EFI、dpkg status、inbox amdxdna module、目前 amdnpu firmware、XRT 與隔離 SHIM。platform.tar / efi.tar SHA PASS；已抽取至獨立 scratch，逐位元比較 kernel、initramfs、module、firmware、dpkg status，EFI 結構可讀。見 research/CP5-verification.txt。scratch 已清除，原 archive 保留 root-only。

限制：同一 NVMe 的 live file-level checkpoint，不是原子 filesystem snapshot，不提供 NVMe 故障保護；沒有實機完整 boot restore PASS。使用者已指定本機備份且不備 T7。Git 不能替代系統 checkpoint。

## Proposed change / STOP / APPROVAL GATE

**使用者已明確批准指定 DKMS / firmware 切換、reboot 後驗證及失敗自動 CP5 rollback。不混用 2.25。**

1. 重新核對 CP5 SHA、無正在用 NPU 的程序、精確 APT simulation 0 upgrade / 0 removal；取得缺少的 dkms DEB 後檢查來源/hash，記錄新增套件。保留同一 kernel/headers。
2. 安裝 dkms 工具與既有 xrt_plugin-amdxdna 2.21 DEB。此 DEB postinst 會 DKMS install --force、rmmod/modprobe amdxdna，並將 accel udev 改成 MODE=0666；不能當普通 userspace 安裝，也不能先偷偷執行。
3. 完整記錄 package payload、四個 npu.dev.sbin firmware 路徑、/usr/src/xrt-amdxdna-2.21.260102.53.release、DKMS registry、updates/dkms module、module precedence、udev 及 initramfs 變更。driver 實際安裝路徑由 DKMS 確認，不只依 DEST_MODULE_LOCATION 字串猜測。
4. 將 package 的 world-writable udev 規則收斂成 render group / 0660，验证使用者 render group 存取；不得讓後续套件更新悄悄放寬。
5. 檢查 module dependency、modinfo 與 firmware 路徑、DKMS status、必要 initramfs；規劃乾淨 reboot。重開機會中斷桌面/作業，需要協調使用者的人工操作。禁止以 live reload 成功就省略重開機後驗證。

|操作|本方案|
|---|---|
|Kernel 更換/降級|否|
|DKMS 安裝|**是**|
|NPU driver 替換|**是**|
|Firmware 修改/新增並載入|**是**，1.1.2.64 npu.dev.sbin|
|GPU driver / Mesa 更換|否|
|XRT 2.25|否|
|Reboot|**需要**|

### Proposed verification gates after approval

重開機後逐層：Kernel 仍6.17.0-14 → module 來源 updates/dkms 與指定 build → firmware 實際1.1.2.64 → XRT detects XDNA2 → VitisAI EP / runner → SDK CNN 實際多次 inference → accelerator live descriptors/counters/kernel activity → CPU reference 輸出 correctness → session.disable_cpu_ep_fallback=1、profile 全 VitisAI、禁止 emulation → HIP/Vulkan regression及重複穩定性 → DOCUMENT/COMMIT → M5 PASS才進M6。

verify/npu_cnn.py 在 private config 試驗時保持禁用 fallback。CPU EP 可能被 ORT 註冊，不能只以 provider list 宣判 CPU 執行；必須看實際 node profile。單獨 NOP/latency、device enumeration、編譯成功、Test Finished 文字或舊 SER9 記錄均不夠。

### Proposed rollback

遇安裝/載入/compute/regression失敗先停止 NPU workloads、保存log與package/module/fw狀態。先模擬移除本次 plugin，審核不動 GPU/XRT base。透過套件 prerm + DKMS remove 對指定 release 清除 out-of-tree module與套件擁有的新增 npu.dev.sbin；不要刪除 in-tree module或 Ubuntu 的 npu.sbin.zst。確認無 updates/dkms 殘留、必要 depmod，恢復 CP5 的相關 udev/config與原 isolated SHIM symlink/prefix；重建/恢复一致 initramfs並reboot，modinfo 確認回 inbox來源、XRT firmware回1.0.0.63，再跑HIP/Vulkan。必要時用本機 recovery材料/live介質還原指定檔案。

不能只覆蓋解開 CP5 就當完整 rollback：overlay restore 不會移除新 DKMS module / 新firmware / registry。必須先清除精確新增項目、同步package registry。不能用整份舊 dpkg status 覆寫充當套件移除。原盤 root/EFI/disk destructive restore 仍需獨立 gate；目前未執行任何 restore。

## DOCUMENT / COMMIT

此文件、read-only resource hashes、失敗/部分成功測試、隔離 build、CP5驗證、regression與可重建 checkpoint script 保存 Git。大型 payload、SDK/venv、archive、編譯模組均留 output/resources、不得入 Git。此 commit 是決策與 recovery readiness，**不是 M5 PASS**。
