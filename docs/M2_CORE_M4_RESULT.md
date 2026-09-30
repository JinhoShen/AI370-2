# M2 core toolchain / M4 Vulkan — PASS

2026-09-30。CP0已有本機檔案層級checkpoint；完整boot recovery未測。

PRECHECK：精確9件DEB SHA通過，APT模擬0upgrade/9new/0remove。
ACTION：本機DEB先放APT cache，再使用no-download/no-upgrade/no-remove transaction；沒有apt update/upgrade。補CMake3.28.3、Ninja1.11.1、glslc2023.8、Vulkan診斷與headers；Mesa/Kernel/driver未變。
VERIFY：GCC13.3透過CMake/Ninja編譯Vulkan C程式與shader；Radeon890M RADV GFX1150實際dispatch，1024結果逐一驗證成功；拒絕CPUfallback。測試期間Kernel journal無新增條目。原始log在output/M4，安裝log在M2_M4_INSTALL.log。
PASS CRITERIA：最小compile/run、真正GPU compute數值正確、Vulkan provider符合基線、無新增Kernelfault，全部達成。不是長時間stability或LLM PASS。
ROLLBACK：按9件新增清單先模擬移除，不autoremove；必要時使用CP0，破壞性restore另approval。
DOCUMENT/COMMIT：本文件、verify/CMakeLists.txt與compute source可重建。

M2 Python/IDE另外驗證，整個M2尚未宣告全部完成。M4完成且在任何ROCm安裝之前。

M1必要權限：shen加入render/video群組，未使用chmod666或更換udev driver規則；目前既有session群組不會自動刷新，後續用sg render做compute，下一次登入才全面生效。回復先保存原群組，僅撤回本次新增成員資格。
