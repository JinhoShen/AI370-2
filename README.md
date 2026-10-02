# AI370 2 Engineering Workstation

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

目前 Roadmap 與狀態：[docs/ROADMAP.md](docs/ROADMAP.md)。
實際執行時間／預估（分開記錄）：[docs/EXECUTION_TIMELINE.md](docs/EXECUTION_TIMELINE.md)。
原規劃 review：[docs/MASTER_PLAN_REVIEW.md](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[docs/M0_BASELINE.md](docs/M0_BASELINE.md)。

**目前狀態：** M0–M10 各自只在正式結果文件定義的範圍內標記完成；M0.1/M1/M8 為部分完成。M7.1 Qwen Q8 Vulkan failure 維持 OPEN。M11 等待 SP701/JTAG target；M12 預硬體整合持續施工；M13 Ross 2026.9.1 Vivado MCP 與本機文件搜尋已驗證、其餘能力仍在施工；M14 自動化持續施工；M15 尚未開始 Final Golden 驗收。詳見 [Roadmap](docs/ROADMAP.md) 與 [M13 結果](docs/M13/RESULT.md)。

每階段：precheck → action → verify → document → commit；PASS 僅代表該 milestone 文件列出的 scope。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求依 Roadmap gate 管理。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。Ubuntu 24.04.4 native Xilinx success 不等於 AMD/Xilinx official OS support；SP701 synthesis PASS 不等於 physical FPGA PASS。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
