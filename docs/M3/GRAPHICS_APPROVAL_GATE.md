# M3 ROCm graphics dependency gate — STOP BEFORE INSTALL

2026-09-30。M4真实Radeon Vulkan compute已PASS；ROCm尚未安裝。

PRECHECK：最小HIP/BLAS closure為18個ROCm7.2.1本機DEB，詳rocm-allowlist.json。APT完整模擬見rocm-simulation.txt。
模擬要求21新增、12升級、0移除；Kernel/DKMS未列入，但libdrm2/amdgpu/common/intel/nouveau/radeon從2.4.125-1ubuntu0.1~24.04.1升至~24.04.2，另有ncurses與libpciaccess依賴升級。

原因：hsa-rocr-dev引入libdrm-dev；目前下載/索引的libdrm-dev精確依賴新版所有libdrm libraries。既有材料沒有~24.04.1的libdrm-dev；base archive的2.4.120不能用來降級工作中的2.4.125。
APT --no-upgrade在此模擬仍會為新增套件依賴升級其他元件，因此不能只依賴flag，必須審查完整Inst列表。禁止直接執行此交易。

ACTION：未執行。符合使用者「ROCm可能破壞目前graphics stack」STOP gate。
可選路線：
1. 優先保留graphics基線，另查可信官方歷史包是否可提供同版libdrm-dev/libpciaccess-dev並重新解析；若找到，SHA/來源/依賴/ABI先驗證，未找到不可強行安裝。
2. 使用者批准Ubuntu同源libdrm patch升級：先建立含現狀的CP2回復包與明確version closure；graphics transaction獨立執行，重新通過M4後才安裝ROCm，不把兩筆交易混在一起。

VERIFY：任何批准後路線需驗desktop/RADV/Vulkancompute、HIP編譯數值、Kernel日誌與package差異。
PASS CRITERIA：gate決策明確且實際驗證成功；預檢成功不等於ROCm PASS。
ROLLBACK：保留舊libdrm版本及config的可恢復材料；回退需完整ABI版本組，不只單件libdrm-amdgpu1；破壞性rootrestore另approval。
DOCUMENT/COMMIT：此gate與simulation已保存。完整sudo權限不代表撤銷重大graphics變更gate。
