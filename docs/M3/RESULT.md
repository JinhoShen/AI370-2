# M3 AMD GPU Compute — PASS

2026-09-30。使用者選擇保留graphics baseline的方案1。

PRECHECK：官方Ubuntu Snapshot 20260215T000000Z提供libdrm-dev~24.04.1、libpciaccess-dev0.17-3ubuntu0.24.04.2與libncurses-dev6.4+20240113-1ubuntu2。Ubuntu archive keyring驗證InRelease，核對Packages.xz及DEB SHA；只有缺少的三件DEB補下載，沒有重下載既有ROCm。
來源與SHA見matched-header-manifest.json、scripts/prepare_matched_headers.py。[Ubuntu Snapshot service](https://snapshot.ubuntu.com/)

ACTION：ROCm7.2.1 userspace最小HIP/BLAS closure18件+匹配headers3件；transaction21新增、0upgrade、0remove。HIP編譯發現缺rocm-device-libs（原本僅Recommended），另預檢並加入同版1件，0upgrade/0remove。最終22新增，所有既有installed package版本保持不變，見package-diff.json。
沒有amdgpu-install/DKMS、Kernel替換、firmware更新、XRT或Mesa升級；APT來源未變、未apt update/full-upgrade、未reboot。

VERIFY：

- rocminfo辨識Radeon890M gfx1150；hipconfig7.2.53211。
- hipcc --offload-arch=gfx1150編譯verify/hip_compute.cpp；sg render session執行，1024 GPU數值逐一正確。
- 同Vulkan shader回歸1024結果PASS；測試期間Kernel journal无新增條目，dpkg --audit正常。
- amdgpu/amdxdna module仍來自6.17.0-14內建module路徑；libdrm2~24.04.1、Mesa25.2.8保持M0版本。

PASS CRITERIA：GPU枚舉、真實HIP compile/run、數值正確、Vulkan回歸、無既有package升級均達成。此非PyTorch／LLM／長時間stability PASS。rocminfo另枚舉NPU agent也不代表NPU推論已驗證。

ROLLBACK：CP0本機archive可用；CP2 graphics-files.tar/etc.tar與SHA、前版本清單存output/M3/CP2。先模擬移除本次22件新包，禁止autoremove或單件libdrm降版；必要的rootrestore須另approval。
DOCUMENT/COMMIT：此文件、package-diff、官方signed來源manifest、完整transaction/verify輸出與rebuild scripts。ROCm預設/opt/rocm→7.2.1，未加入全域LD_LIBRARY_PATH或GPU架構偽裝。
