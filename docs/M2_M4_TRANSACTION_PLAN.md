# M2/M4 minimal toolchain transaction — PRECHECK PASS / ACTION PENDING

2026-09-30。CP0本機檔案層级checkpoint已驗證，限制見CP0_RESULT.md。

精確allowlist：cmake3.28.3-1build7、cmake-data同版、ninja-build1.11.1-2、vulkan-tools1.3.275.0+dfsg1-1、libvulkan-dev1.3.275.0-1build1、glslc2023.8-1build1、libshaderc1同版、libjsoncpp251.9.5-6build1、librhash01.4.3-3build1。
已存在本機下載；APT模擬為0升級、9新增、0移除，424pending不處理。不修改Kernel、DKMS、GPU/NPU driver或Mesa；不預期reboot。

ACTION尚未執行：目前sudo僅授權checkpoint-verifier，不含套件安裝。需本機人工管理權限執行具體transaction。
VERIFY：CMake/Ninja compile/run、vulkaninfo Radeon/RADV、shader compile及最小compute dispatch數值驗證，Kernel log regression。
PASS須上述功能驗證通過；枚舉成功不能代替compute PASS。
ROLLBACK：按本transaction新安裝包清單移除（先模擬），不無條件autoremove；必要時CP0檔案恢復，破壞性root restore另approval。
DOCUMENT/COMMIT：保存精確transaction和原始APT結果、各子phase測試與版本。原始模擬保留output/precheck/toolchain-apt-simulation.txt。
