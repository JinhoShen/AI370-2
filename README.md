# AI370 2 Engineering Workstation

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

目前 Roadmap 與狀態：[docs/ROADMAP.md](docs/ROADMAP.md)。
實際執行時間／預估（分開記錄）：[docs/EXECUTION_TIMELINE.md](docs/EXECUTION_TIMELINE.md)。
原規劃 review：[docs/MASTER_PLAN_REVIEW.md](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[docs/M0_BASELINE.md](docs/M0_BASELINE.md)。

**目前狀態：** M0–M10 仍只在正式結果文件定義的範圍內有效；M0.1/M1/M8 為部分完成，M7.1 Qwen Q8 Vulkan failure 維持 OPEN。M11 已 PASS 於有界 SP701 實體驗證範圍（JTAG、MIG DDR3 bitstream/programming、16 MiB physical write/read/compare，以及已啟動的 post-program regression）；不代表全容量 DDR coverage。M12 已實際驗證 workstation→SP701 JTAG-to-AXI→FPGA logic→workstation 的資料往返；標準 XRT application path 仍 DEFERRED，M12 未整體 PASS。M13 Ross/Local KB 協助此一工程流程，但 Vivado MCP 硬體操作、Vitis/HLS workflow 與 air-gapped agent 仍未驗證。M14 持續施工；M15 Final Golden 尚未開始。詳見 [Roadmap](docs/ROADMAP.md)、[M12 整合報告](docs/M12/SP701_HOST_FPGA_INTEGRATION_REPORT.md) 與 [M13 結果](docs/M13/RESULT.md)。

每階段：precheck → action → verify → document → commit；PASS 僅代表該 milestone 文件列出的 scope。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求依 Roadmap gate 管理。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。Ubuntu 24.04.4 native Xilinx success 不等於 AMD/Xilinx official OS support；M11 bounded DDR3 hardware PASS 僅代表其報告列出的範圍，不等於全容量 DDR coverage；M12 的實體 JTAG-to-AXI round-trip 是另外的控制/資料路徑證據，仍不等於 production XRT application integration。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
