# Build progress

**狀態來源：** [`ROADMAP.md`](ROADMAP.md) 為 M0–M15 唯一詳細狀態表；[`EXECUTION_TIMELINE.md`](EXECUTION_TIMELINE.md) 是唯一詳細時間表。下表只作目前狀態摘要，避免另行維護不同估時或 PASS 定義。

| 階段 | 狀態 | PASS / 已知範圍 | 待辦／阻塞 | 詳細記錄 |
|---|---|---|---|---|
| M0 Baseline | COMPLETE | 原始系統/資源 inventory 已保存；M0 Golden tag 存在 | 不覆寫歷史基線 | [M0_BASELINE](M0_BASELINE.md) |
| M0.1 Recovery / Git | PARTIAL | Git/evidence 流程、同碟 file-level CP0 與 selected-file restore | Off-device backup、full boot/system recovery 未驗證 | [CP0_RESULT](CP0_RESULT.md) |
| M1 OS / Compatibility | PARTIAL / 無獨立 PASS | 兼容性 decision 與 protected-stack gates 載入後續工作流程 | 無 standalone M1 result；Ubuntu 24.04.4 native Xilinx success 不等於官方支援 | [MASTER_PLAN_REVIEW](MASTER_PLAN_REVIEW.md) |
| M2 Core Development Toolchain | PASS（記錄範圍） | C/C++、CMake/Ninja、Python venv、VS Code CLI/extensions | GUI debugger 和完整離線IDE重建未驗證 | [M2 Python/IDE](M2_PYTHON_IDE_RESULT.md), [M2/M4](M2_CORE_M4_RESULT.md) |
| M3 ROCm / HIP | PASS | HIP gfx1150 實際執行與數值驗證；Mesa/Kernel未替換 | 不含長時間穩定性或更廣 framework 測試 | [M3](M3/RESULT.md) |
| M4 Mesa / Vulkan | PASS | RADV Radeon 890M compute 1,024 結果正確、拒絕 CPU fallback | 不代表長時穩定性 | [M2_CORE_M4_RESULT](M2_CORE_M4_RESULT.md) |
| M5 XDNA2 / XRT / Ryzen AI | PASS / NPU Golden State | post-reboot VitisAI-only CNN、無CPU fallback、輸出比對及HIP/Vulkan回歸 | 保護已驗證 Mesa/ROCm/XRT/amdxdna/firmware stack | [M5 status](M5/reboot/STATUS) |
| M6 Local LLM | PASS | CPU/Vulkan/ROCm llama.cpp 短測，backend/device 可確認；Lemonade 短測 | 不含 Qwen Q8 問題或高負載穩定性 | [M6](M6/RESULT.md) |
| M7 Conservative Benchmark | PASS（僅保守範圍） | context 64、三次量測、CPU/Vulkan/ROCm效能與資源記錄 | 不是 high-load/long-duration PASS | [M7](M7/RESULT.md) |
| M7.1 Qwen Q8 Vulkan failure | OPEN | 檔案/SHA/metadata/CPU smoke verified；Vulkan smoke失敗，ROCm inference未執行 | RADV command submission/device-loss investigation未解決 | [Qwen smoke](M7/QWEN36_Q8_SMOKE.md) |
| M8 NPU Local AI | PARTIAL | ONNX CNN workload PASS | NPU LLM evaluation DEFERRED（模型未在本機） | [M8](M8/RESULT.md) |
| M9 Vivado / FPGA Toolchain | PASS（software scope） | Vivado 2026.1、SP701/Arty辨識、SP701 RTL synthesis/utilization、HLS與stack regression | 不是physical FPGA PASS；24.04.4 official support未確立 | [M9](M9/LICENSE_UNLOCKED_VALIDATION.md) |
| M10 Vitis / HLS / Platforms | PASS（software scope） | `v++`, SP701 HLS、8 embedded platforms個別解析 | 不代表platform programming或硬體執行 | [M10](M10/RESULT.md) |
| Platform / Xilinx Records | COMPLETE（文件） | 最新只讀平台狀態與2026.1安裝差異已記錄 | 文件不是新增測試結果 | [Platform record](platform/AI370_2_PLATFORM_RECORD.md), [Xilinx record](platform/XILINX_2026_1_INSTALLATION_RECORD.md) |
| M11 SP701 Physical FPGA | DEFERRED / WAITING FOR HARDWARE TARGET | 尚無JTAG target evidence | JTAG detection→implementation→bitstream→program→observable execution→regression | [ROADMAP](ROADMAP.md) |
| M12 AI + FPGA Integration | IN PROGRESS / host↔FPGA DEFERRED | GPU/NPU sequential coexistence smoke VERIFIED；protected stack未變更 | 現有 `.xpfm` 無 SP701 platform；XRT C++ headers、FPGA runtime/API、JTAG與hardware execution仍未驗證 | [M12 RESULT](M12/RESULT.md), [ROADMAP](ROADMAP.md) |
| M13 AMD Ross Agentic AI | PLANNED / NOT INSTALLED | 只有AMD官方資料研究規劃，無本機安裝或驗證 | Codex/MCP/Vivado/Vitis/Skills/KB及offline能力待驗證 | [ROADMAP](ROADMAP.md) |
| M14 Automation / Reproducible Rebuild | PLANNED | 無 end-to-end rebuild PASS | 將已驗證流程護欄化並實際rebuild/recovery演練 | [ROADMAP](ROADMAP.md) |
| M15 Final Golden Workstation | PLANNED | 尚無Final Golden State | integrated regression、recovery、docs/security audit、temporary privilege cleanup、final checkpoint | [ROADMAP](ROADMAP.md) |

## Project controls

- M5 NPU Golden State 與已驗證 GPU/NPU/FPGA stack 保持受保護狀態；未經單獨決策不得將 Mesa、ROCm、XRT、amdxdna、NPU firmware 或 Kernel 變更混入 roadmap 工作。
- M9/M10 的 PASS 僅涵蓋軟體工具、SP701 software synthesis/HLS 與已列明的平台檢查；SP701 JTAG、programming、hardware execution 尚未驗證。
- M7.1 保持 OPEN；一般 Vulkan regression PASS 不會關閉 Qwen Q8 的獨立失敗。
- M0.1 不是完整 recovery PASS；M9 手工安裝成功不是自動化重建能力；Ross 尚未安裝或驗證。
- 詳細實際時間與未來 ESTIMATE 集中維護於 [`EXECUTION_TIMELINE.md`](EXECUTION_TIMELINE.md)。ACTUAL project date window 不代表投入工時。
