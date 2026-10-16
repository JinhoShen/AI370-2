# Build progress

## Latest acceptance — 2026-10-16

**WAN_OFFLINE_ENGINEERING_PASS**: existing local Qwen + Ross + model-authored RTL repair + fixed XSim PASS while host IPv4/IPv6 default routes were absent and external TCP failed with ENETUNREACH. 295.053 seconds, one accepted patch, two XSim runs. Network restored and formal ENGINEERING profile rechecked PASS. [Actual evidence](M15/evidence/2026-10-16/wan-offline-engineering/). This resolves bounded WAN-offline engineering verification, not physical air-gap or clean-host rebuild. M13/M14 broader scope remains PARTIAL; M15 remains PRE-FINAL / SOFTWARE_PASS_WITH_DEFERRED, not FINAL_GOLDEN_PASS. T7 remains BLOCKED on user hold; Telegram E2E WAITING_USER for token. No protected stack change, FPGA programming, push or new workload. Earlier dated limitations remain history.


**Latest operational checkpoint — 2026-10-15 18:52:** READY_FOR_FINAL_REVIEW / SOFTWARE_PASS_WITH_DEFERRED. Formal Qwen XL now runs saved ENGINEERING Vulkan16K/24-thread settings; actual Local Qwen + Ross + XSim repair and current software regression PASS. Graphics baseline gate resolved. Full M15 remains PRE-FINAL; external/deferred items are listed in the [handoff](LOCAL_ENGINEERING_HANDOFF.md).

**Current resolution — 2026-10-15:** Mesa/libdrm `.2` baseline accepted after bounded HIP/Vulkan/XRT/strict NPU PASS; version guards updated and read-only audit now PASS_WITH_DEFERRED (27 PASS / 0 FAIL). The earlier baseline gate below is resolved. M15 remains PRE-FINAL for independent deployment/offline/rebuild scope. [Decision/evidence](M15/GRAPHICS_BASELINE_ACCEPTANCE_2026-10-15.md).

**2026-10-15:** Current closeout evidence is in [FINAL_READINESS_REVIEW.md](FINAL_READINESS_REVIEW.md). The protected version guard fails on Mesa/libdrm Ubuntu `.2` vs accepted `.1`; no baseline or package was changed. Local model engineering evidence passed its separate semantic audit.

**狀態來源：** [`ROADMAP.md`](ROADMAP.md) 為 M0–M15 唯一詳細狀態表；[`EXECUTION_TIMELINE.md`](EXECUTION_TIMELINE.md) 是唯一詳細時間表。下表只作目前狀態摘要，避免另行維護不同估時或 PASS 定義。

| 階段 | 狀態 | PASS / 已知範圍 | 待辦／阻塞 | 詳細記錄 |
|---|---|---|---|---|
| M0 Baseline | COMPLETE | 原始系統/資源 inventory 已保存；M0 Golden tag 存在 | 不覆寫歷史基線 | [M0_BASELINE](M0_BASELINE.md) |
| M0.1 Recovery / Git | PARTIAL | Git/evidence 流程；CP0 為 Vivado/Vitis 前歷史 archive，checksum 與 selected-file restore PASS；T7 commit 71f8248 bundle 已 clone-verified，完整 1,027 項 SHA256 全數通過 | T7 kit 的 OS/dependency closure 與 clean rebuild 尚未驗證；full boot restore NOT TESTED；current-machine image NOT REQUIRED | [CP0_RESULT](CP0_RESULT.md), [T7 Manifest](deployment/T7_MANIFEST.md) |
| M1 OS / Compatibility | PARTIAL / 無獨立 PASS | 兼容性 decision 與 protected-stack gates 載入後續工作流程 | 無 standalone M1 result；Ubuntu 24.04.4 native Xilinx success 不等於官方支援 | [MASTER_PLAN_REVIEW](MASTER_PLAN_REVIEW.md) |
| M2 Core Development Toolchain | PASS（記錄範圍） | C/C++、CMake/Ninja、Python venv、VS Code CLI/extensions | GUI debugger 和完整離線IDE重建未驗證 | [M2 Python/IDE](M2_PYTHON_IDE_RESULT.md), [M2/M4](M2_CORE_M4_RESULT.md) |
| M3 ROCm / HIP | PASS | HIP gfx1150 實際執行與數值驗證；Mesa/Kernel未替換 | 不含長時間穩定性或更廣 framework 測試 | [M3](M3/RESULT.md) |
| M4 Mesa / Vulkan | PASS | RADV Radeon 890M compute 1,024 結果正確、拒絕 CPU fallback | 不代表長時穩定性 | [M2_CORE_M4_RESULT](M2_CORE_M4_RESULT.md) |
| M5 XDNA2 / XRT / Ryzen AI | PASS / NPU Golden State | post-reboot VitisAI-only CNN、無CPU fallback、輸出比對及HIP/Vulkan回歸 | 保護已驗證 Mesa/ROCm/XRT/amdxdna/firmware stack | [M5 status](M5/reboot/STATUS) |
| M6 Local LLM | PASS | CPU/Vulkan/ROCm llama.cpp 短測，backend/device 可確認；Lemonade 短測 | 不含 Qwen Q8 問題或高負載穩定性 | [M6](M6/RESULT.md) |
| M7 Conservative Benchmark | PASS（僅保守範圍） | context 64、三次量測、CPU/Vulkan/ROCm效能與資源記錄；後續 Qwen3.8/Gemma bounded smokes 見 M7/M15 evidence | 不是 high-load/long-duration PASS；Qwen3.6 Q8 Vulkan failure 仍由 M7.1 OPEN 管理 | [M7](M7/RESULT.md), [Qwen3.8 candidates](M7/QWEN38_CANDIDATE_MODELS.md) |
| M7.1 Qwen Q8 Vulkan failure | OPEN | 檔案/SHA/metadata/CPU smoke verified；Vulkan smoke失敗，ROCm inference未執行 | RADV command submission/device-loss investigation未解決 | [Qwen smoke](M7/QWEN36_Q8_SMOKE.md) |
| M8 NPU Local AI | PARTIAL | ONNX CNN workload PASS | NPU LLM evaluation DEFERRED（模型未在本機） | [M8](M8/RESULT.md) |
| M9 Vivado / FPGA Toolchain | PASS（software scope） | Vivado 2026.1、SP701/Arty辨識、SP701 RTL synthesis/utilization、HLS與stack regression | 不是physical FPGA PASS；24.04.4 official support未確立 | [M9](M9/LICENSE_UNLOCKED_VALIDATION.md) |
| M10 Vitis / HLS / Platforms | PASS（software scope） | `v++`, SP701 HLS、8 embedded platforms個別解析 | 不代表platform programming或硬體執行 | [M10](M10/RESULT.md) |
| Platform / Xilinx Records | COMPLETE（文件） | 最新只讀平台狀態與2026.1安裝差異已記錄 | 文件不是新增測試結果 | [Platform record](platform/AI370_2_PLATFORM_RECORD.md), [Xilinx record](platform/XILINX_2026_1_INSTALLATION_RECORD.md) |
| M11 SP701 Physical FPGA | PASS（bounded physical validation scope） | SP701 MIG synthesis/implementation/bitstream/programming passed; blocking DRC 0; WNS +0.994 ns/TNS 0; 30 s physical test on 16 MiB window showed calibration complete, 14,210,117 write and 6,558,522 read status events, sticky compare/error 0; post-test JTAG and already-started post-program regression passed | Full 512 MiB MIG / 1 GiB module coverage, exhaustive range and long-duration behavior are NOT TESTED | [M11 RESULT](M11/RESULT.md), [DDR3 test report](M11/SP701_DDR3_Memory_Test_Report.md), [DDR evidence](M11/evidence/ddr3-hardware-test-2026-10-02/), [post-program evidence](M11/evidence/post-program-regression-2026-10-02/), [ROADMAP](ROADMAP.md) |
| M12 AI + FPGA Integration | IN PROGRESS — physical JTAG-to-AXI Host↔FPGA path VERIFIED | Earlier GPU/NPU coexistence evidence plus a new SP701 JTAG-to-AXI design: four physical host writes were transformed in FPGA fabric and read back correctly; bitstream/DRC/timing/JTAG evidence retained | Production application transport, XRT host API/`xclbin`, GPU/NPU AI workload handoff and throughput remain DEFERRED/NOT TESTED; no SP701 `.xpfm` or XRT headers | [M12 RESULT](M12/RESULT.md), [integration report](M12/SP701_HOST_FPGA_INTEGRATION_REPORT.md), [M12 evidence](M12/evidence/host-fpga-jtag-axi-20261002/), [ROADMAP](ROADMAP.md) |
| M13 AMD Ross Agentic AI | PARTIAL — bounded Vulkan16K Qwen engineering VERIFIED | T1/T2/T3 each 3/3 per Ross and Non-Ross arm; 18/18 total; model provenance and local KB calls audited 2026-10-15 | Full disconnected operation, direct Qwen Vivado Tcl MCP, Vitis IDE/Embedded agent and live Telegram remain NOT_TESTED/DEFERRED | [M13](M13/RESULT.md), [current review](FINAL_READINESS_REVIEW.md) |
| M14 Automation / Rebuild | IN PROGRESS — accepted-baseline audit PASS_WITH_DEFERRED | New semantic audit PASS: 36 historical repairs, 664 checksums, 20 successful configurations and preserved guard failure | Read-only audit PASS_WITH_DEFERRED: 27 PASS, zero failures; full clean rebuild unverified | [M14](M14/RESULT.md), [audit](M14/evidence/2026-10-15/accepted-baseline-audit/summary.json) |
| M15 Final Golden Workstation | PRE-FINAL — current software PASS_WITH_DEFERRED | Fresh 2026-10-15 bounded software regression PASS; formal Qwen/Ross/XSim integration PASS; hardware evidence retained | T7 user hold, offline/rebuild closure, disconnected workflow and final scope acceptance | [M15](M15/RESULT.md), [current review](FINAL_READINESS_REVIEW.md) |
| Local Model Lab | PARTIAL — available-model practical cohort completed; five-model roster incomplete | Qwen3.8 and Gemma each 18/18 T1/T2/T3 PASS; 12 RTL syntheses per model; HLS csim/csynth; Vulkan/24 threads/16K; formal Qwen CPU restoration PASS | GPT-OSS and Devstral NOT_INSTALLED; fifth slot unspecified; historical CPU and harness-invalid pilot retained separately; no universal winner | [Model Lab result](LOCAL_MODEL_LAB/RESULT.md), [protocol](LOCAL_MODEL_LAB/PROTOCOL.md) |
| Qwen performance optimization | PARTIAL_SAFE_PROFILES_READY — recommendations not applied | 20 safe configurations × 3 short repetitions; reused Vulkan 16K engineering 18/18; original formal argv/API/Local Agent restored PASS; package versions unchanged | ROCm18 load FAIL_RESOURCE_GUARD; further ROCm tuning NOT_TESTED; no global/long-duration optimum claim | [Performance report](LOCAL_MODEL_LAB/QWEN_PERFORMANCE_OPTIMIZATION.md) |

## Project controls

- M5 NPU Golden State 與已驗證 GPU/NPU/FPGA stack 保持受保護狀態；未經單獨決策不得將 Mesa、ROCm、XRT、amdxdna、NPU firmware 或 Kernel 變更混入 roadmap 工作。
- M9/M10 的 PASS 僅涵蓋軟體工具、SP701 software synthesis/HLS 與已列明的平台檢查；後續 M11 已另行驗證有界實體 FPGA/DDR 範圍，不擴張 M9/M10 的 PASS。
- M7.1 保持 OPEN；一般 Vulkan regression PASS 不會關閉 Qwen Q8 的獨立失敗。
- M0.1 不是完整 recovery PASS；M9 手工安裝成功不是自動化重建能力；M13 Ross 僅有明確記錄的軟體/本機搜尋驗證，尚未整體 PASS。
- 詳細實際時間與未來 ESTIMATE 集中維護於 [`EXECUTION_TIMELINE.md`](EXECUTION_TIMELINE.md)。ACTUAL project date window 不代表投入工時。
