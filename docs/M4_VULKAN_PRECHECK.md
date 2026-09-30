# M4 Vulkan precheck — ENUMERATION PASS / COMPUTE NOT RUN

日期：2026-09-30。既有vulkan-tools DEB解包至Git忽略的output/diagnostics/vulkan-tools，直接執行vulkaninfo --summary；沒有dpkg/apt安裝或系統library替換。

結果：instance 1.3.275；Radeon 890M vendor 1002/device150e，RADV GFX1150，Mesa25.2.8-0ubuntu0.24.04.1，GPU API1.4.318。
同時枚舉llvmpipe CPU device；後續compute sample必須明確選RADV Radeon，不能以fallback為GPU PASS。
stderr空白。原始stdout/stderr保留output/diagnostics；現有Kernel/amdgpu/Mesa未變更。

僅枚舉成功，不是M4完整PASS；最小compute dispatch/數值驗證與前後Kernel日誌尚未完成。
回復：刪除解包工具即可，系統套件沒有變動。
