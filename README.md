# AI370 2 Engineering Workstation

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

目前 Roadmap 與狀態：[docs/ROADMAP.md](docs/ROADMAP.md)。
實際執行時間／預估（分開記錄）：[docs/EXECUTION_TIMELINE.md](docs/EXECUTION_TIMELINE.md)。
原規劃 review：[docs/MASTER_PLAN_REVIEW.md](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[docs/M0_BASELINE.md](docs/M0_BASELINE.md)。

**目前狀態：** M0–M10 依正式結果文件定義範圍；M7 只代表 conservative benchmark，不代表 high-load/long-duration stability。M0.1/M1/M8 部分完成，M8 NPU LLM DEFERRED；M7.1 Qwen Q8 Vulkan failure 維持 OPEN。M11 已 PASS 於有界 SP701 實體驗證範圍（JTAG、MIG DDR3 bitstream/programming、16 MiB physical write/read/compare），不代表全容量 DDR coverage。M9/M10 為 FPGA software toolchain / Vitis-HLS-platform 驗證 PASS，不是 SP701 physical PASS。M12 已驗證 workstation→SP701 JTAG-to-AXI 資料往返；標準 XRT application path 仍 DEFERRED。M13 的 standalone Qwen3.8 Local Agent 已直接透過 Lemonade 使用受限本機工具，完成一次 RTL→XSim 失敗回饋→模型修正→XSim PASS；Telegram controller source 也直接啟動 Local Agent，不依賴 Codex。多步驟泛化、Vitis IDE、Telegram live E2E 與完整 host air-gap 尚未驗證。M14 guarded verifiers、APT guard、M12 clean out-of-tree software rebuild 及最新 evidence audit 均有證據；整機 clean rebuild/recovery 尚未完成。M15 unified software regression 為 PASS_WITH_DEFERRED，sudoers syntax/security audit 已 PASS。依 2026-10-02 架構決策，不製作包含已安裝 Xilinx tree 的 current-state archive；CP0 保留為 Vivado/Vitis 前 historical recovery evidence，selected-file restore PASS，但 full boot restore NOT TESTED。T7 已安全卸載並關閉電源，目前未掛載；最後驗證的部署快照在 commit `25125e7`，後續文件更新尚待 T7 重接後同步。正式部署目錄為 `/media/shen/T7/AMD_AI_Workstation/`；deployment kit 仍 PARTIAL，尚未建立完整離線 dependency closure 或在乾淨新機重建。規格見 [T7 Deployment Kit](docs/deployment/T7_MANIFEST.md)。Ubuntu 24.04.4 上的 Xilinx native installation success 不代表 AMD/Xilinx 官方 OS support。詳見 [Roadmap](docs/ROADMAP.md)、[M15 結果](docs/M15/RESULT.md) 及 [execution timeline](docs/EXECUTION_TIMELINE.md)。

每階段：precheck → action → verify → document → commit；PASS 僅代表該 milestone 文件列出的 scope。

**2026-10-12 readiness update：** Lemonade 在實際設定的 `127.0.0.1:13305` 健康檢查與 bounded Qwen3.8 CPU inference 通過；新的 standalone 本機 Qwen→Local Agent RTL/XSim 修正閉環及 Vivado/Vitis/HLS 版本啟動通過；工具 sandbox 外網阻斷 smoke 通過。M13/M14 仍 IN PROGRESS，M15 仍 PRE-FINAL；Telegram 等待 BotFather token，沒有宣稱 FINAL_GOLDEN_PASS。詳見 [M15 readiness follow-up](docs/M15/RESULT.md) 與 [M13 evidence](docs/M13/evidence/2026-10-12/local-qwen-standalone-agent-rtl/)。

**2026-10-13 Ross A/B update：** 本地 Qwen3.8 + Local Agent 已實際呼叫 Ross Skill 與本機 Knowledge Base MCP。T1 A=3/3、B=0/3；修正後 T2 A=3/3、B=1/3（另兩次 B 因 8192-token context overflow 失敗）；T3 兩組 3/3，但 Ross 平均慢 2.69%。正式 T2 3×3 cohort 已完成，先前 v5/v6/v7 為分開保留的診斷歷史。M13 維持 IN PROGRESS/PARTIAL，沒有宣稱 Ross 普遍提升成功率或速度。細節與失敗樣本見 [M13 Ross benchmark report](docs/M13/M13_ROSS_AB_BENCHMARK_REPORT.md)。

**2026-10-13 Local Model Lab update：** 已盤點五個候選槽位並建立只會使用「已在 loopback server 載入模型」的 guarded runner。Qwen3.8 Q4_K_XL current CPU smoke PASS，正式 T1/T2/T3 A/B 數據沿用 M13；Gemma 4 有既有 bounded smoke evidence，但目前未載入。GPT-OSS 20B、Devstral Small 2 尚未安裝，RESERVED 尚未指定，因此沒有跨模型排名，Lab 維持 PARTIAL。沒有下載或切換正式模型。詳見 [Local Model Lab](docs/LOCAL_MODEL_LAB/RESULT.md) 與 [重跑流程](docs/LOCAL_MODEL_LAB/PROTOCOL.md)。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求依 Roadmap gate 管理。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。Ubuntu 24.04.4 native Xilinx success 不等於 AMD/Xilinx official OS support；M11 bounded DDR3 hardware PASS 僅代表其報告列出的範圍，不等於全容量 DDR coverage；M12 的實體 JTAG-to-AXI round-trip 是另外的控制/資料路徑證據，仍不等於 production XRT application integration。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
