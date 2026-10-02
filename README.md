# AI370 2 Engineering Workstation

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

目前 Roadmap 與狀態：[docs/ROADMAP.md](docs/ROADMAP.md)。
實際執行時間／預估（分開記錄）：[docs/EXECUTION_TIMELINE.md](docs/EXECUTION_TIMELINE.md)。
原規劃 review：[docs/MASTER_PLAN_REVIEW.md](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[docs/M0_BASELINE.md](docs/M0_BASELINE.md)。

**目前狀態：** M0–M10 依正式結果文件定義範圍；M7 只代表 conservative benchmark，不代表 high-load/long-duration stability。M0.1/M1/M8 部分完成，M8 NPU LLM DEFERRED；M7.1 Qwen Q8 Vulkan failure 維持 OPEN。M11 已 PASS 於有界 SP701 實體驗證範圍（JTAG、MIG DDR3 bitstream/programming、16 MiB physical write/read/compare），不代表全容量 DDR coverage。M9/M10 為 FPGA software toolchain / Vitis-HLS-platform 驗證 PASS，不是 SP701 physical PASS。M12 已驗證 workstation→SP701 JTAG-to-AXI 資料往返；標準 XRT application path 仍 DEFERRED。M13 Ross/Local KB 已協助實際工作流，並有 bounded HLS C-sim/synthesis/report VERIFIED；end-to-end air-gap 與部分 IDE/cosimulation 尚未驗證。M14 guarded verifiers、APT guard 及 M12 clean out-of-tree software rebuild 均有證據；完整 rebuild/recovery 尚未完成。M15 unified software regression 已 PASS_WITH_DEFERRED。依 2026-10-02 架構決策，不製作包含已安裝 Xilinx tree 的 current-state archive；CP0 保留為 Vivado/Vitis 前 historical recovery evidence，selected-file restore PASS，但 full boot restore NOT TESTED。T7 定位為 Deployment / Migration Media，已掛載；Vivado/Vitis installer 與系統副本大小及 SHA256 完全相同，但整體 deployment kit 尚未完成驗證。規格與盤點見 [T7 Deployment Kit](docs/deployment/T7_MANIFEST.md)。T7 上的 Git bundle 已 clone-verified；部署資源 closure 與 clean rebuild 尚未完成。M15 收尾仍待資源清冊閉合及 sudoers syntax audit。Ubuntu 24.04.4 上的 Xilinx native installation success 不代表 AMD/Xilinx 官方 OS support。詳見 [Roadmap](docs/ROADMAP.md)、[M15 結果](docs/M15/RESULT.md) 及 [execution timeline](docs/EXECUTION_TIMELINE.md)。

每階段：precheck → action → verify → document → commit；PASS 僅代表該 milestone 文件列出的 scope。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求依 Roadmap gate 管理。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。Ubuntu 24.04.4 native Xilinx success 不等於 AMD/Xilinx official OS support；M11 bounded DDR3 hardware PASS 僅代表其報告列出的範圍，不等於全容量 DDR coverage；M12 的實體 JTAG-to-AXI round-trip 是另外的控制/資料路徑證據，仍不等於 production XRT application integration。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
