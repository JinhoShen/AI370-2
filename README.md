# AI370 2 Engineering Workstation

## 本機操作介面

在這台工作站開啟 **http://127.0.0.1:13306/**：模型選擇、Local Agent 對話／唯讀查詢、Ross 選項、隔離 RTL/XSim 工作、進度／結果與停止操作。[使用方式與驗證邊界](docs/LOCAL_AGENT_UI.md)。不下載模型，不依賴 Codex／雲端；M15 PRE-FINAL 狀態不變。


## Delivery review — 2026-10-16

**SOFTWARE_DELIVERY_COMPLETE_WITH_DEFERRED / READY_FOR_FINAL_REVIEW.** Fresh read-only evidence/protected-stack audit has zero failures; broad temporary sudo is already removed, so no new privilege modification was needed. WAN-offline local Ross/RTL/XSim acceptance passed. All executable closeout actions in this scope are finished. Overall M15 remains PRE-FINAL, not FINAL_GOLDEN_PASS: Telegram token, T7 user hold, clean-host rebuild/full restore and physical air-gap remain explicit external/unverified conditions. [Final scope, evidence and remaining prerequisites](docs/M15/FINAL_COMPLETION_REVIEW.md). No workload regression repeated or system stack changed.


## Latest acceptance — 2026-10-16

**WAN_OFFLINE_ENGINEERING_PASS**: existing local Qwen + Ross + model-authored RTL repair + fixed XSim PASS while host IPv4/IPv6 default routes were absent and external TCP failed with ENETUNREACH. 295.053 seconds, one accepted patch, two XSim runs. Network restored and formal ENGINEERING profile rechecked PASS. [Actual evidence](docs/M15/evidence/2026-10-16/wan-offline-engineering/). This resolves bounded WAN-offline engineering verification, not physical air-gap or clean-host rebuild. M13/M14 broader scope remains PARTIAL; M15 remains PRE-FINAL / SOFTWARE_PASS_WITH_DEFERRED, not FINAL_GOLDEN_PASS. T7 remains BLOCKED on user hold; Telegram E2E WAITING_USER for token. No protected stack change, FPGA programming, push or new workload. Earlier dated limitations remain history.


**Latest operational checkpoint — 2026-10-15 18:52:** READY_FOR_FINAL_REVIEW / SOFTWARE_PASS_WITH_DEFERRED. Formal Qwen XL now runs saved ENGINEERING Vulkan16K/24-thread settings; actual Local Qwen + Ross + XSim repair and current software regression PASS. Graphics baseline gate resolved. Full M15 remains PRE-FINAL; external/deferred items are listed in the [handoff](docs/LOCAL_ENGINEERING_HANDOFF.md).

**Current resolution — 2026-10-15:** Mesa/libdrm `.2` baseline accepted after bounded HIP/Vulkan/XRT/strict NPU PASS; version guards updated and read-only audit now PASS_WITH_DEFERRED (27 PASS / 0 FAIL). The earlier baseline gate below is resolved. M15 remains PRE-FINAL for independent deployment/offline/rebuild scope. [Decision/evidence](docs/M15/GRAPHICS_BASELINE_ACCEPTANCE_2026-10-15.md).

**2026-10-15 收尾狀態：PRE-FINAL／BLOCKED_BASELINE_REVIEW。** 本地 Qwen＋Ross 的 Vulkan16K T1/T2/T3 已有 18/18 PASS；最新唯讀 audit 驗證了工程 evidence，但發現 Mesa／libdrm 套件修訂版 `.2` 與原 Golden guard `.1` 不一致。未改套件、未接受新 baseline、未切換正式模型。詳見 [目前驗收與真正剩餘項目](docs/FINAL_READINESS_REVIEW.md)。

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

目前 Roadmap 與狀態：[docs/ROADMAP.md](docs/ROADMAP.md)。
實際執行時間／預估（分開記錄）：[docs/EXECUTION_TIMELINE.md](docs/EXECUTION_TIMELINE.md)。
原規劃 review：[docs/MASTER_PLAN_REVIEW.md](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[docs/M0_BASELINE.md](docs/M0_BASELINE.md)。

**目前狀態：** M0–M10 依正式結果文件定義範圍；M7 只代表 conservative benchmark，不代表 high-load/long-duration stability。M0.1/M1/M8 部分完成，M8 NPU LLM DEFERRED；M7.1 Qwen Q8 Vulkan failure 維持 OPEN。M11 已 PASS 於有界 SP701 實體驗證範圍（JTAG、MIG DDR3 bitstream/programming、16 MiB physical write/read/compare），不代表全容量 DDR coverage。M9/M10 為 FPGA software toolchain / Vitis-HLS-platform 驗證 PASS，不是 SP701 physical PASS。M12 已驗證 workstation→SP701 JTAG-to-AXI 資料往返；標準 XRT application path 仍 DEFERRED。M13 的 standalone Qwen3.8 Local Agent 已直接透過 Lemonade 使用受限本機工具，完成一次 RTL→XSim 失敗回饋→模型修正→XSim PASS；Telegram controller source 也直接啟動 Local Agent，不依賴 Codex。多步驟泛化、Vitis IDE、Telegram live E2E 與完整 host air-gap 尚未驗證。M14 guarded verifiers、APT guard、M12 clean out-of-tree software rebuild 及最新 evidence audit 均有證據；整機 clean rebuild/recovery 尚未完成。M15 unified software regression 為 PASS_WITH_DEFERRED，sudoers syntax/security audit 已 PASS。依 2026-10-02 架構決策，不製作包含已安裝 Xilinx tree 的 current-state archive；CP0 保留為 Vivado/Vitis 前 historical recovery evidence，selected-file restore PASS，但 full boot restore NOT TESTED。T7 已安全卸載並關閉電源，目前未掛載；最後驗證的部署快照在 commit `25125e7`，後續文件更新尚待 T7 重接後同步。正式部署目錄為 `/media/shen/T7/AMD_AI_Workstation/`；deployment kit 仍 PARTIAL，尚未建立完整離線 dependency closure 或在乾淨新機重建。規格見 [T7 Deployment Kit](docs/deployment/T7_MANIFEST.md)。Ubuntu 24.04.4 上的 Xilinx native installation success 不代表 AMD/Xilinx 官方 OS support。詳見 [Roadmap](docs/ROADMAP.md)、[M15 結果](docs/M15/RESULT.md) 及 [execution timeline](docs/EXECUTION_TIMELINE.md)。

每階段：precheck → action → verify → document → commit；PASS 僅代表該 milestone 文件列出的 scope。

**2026-10-12 readiness update：** Lemonade 在實際設定的 `127.0.0.1:13305` 健康檢查與 bounded Qwen3.8 CPU inference 通過；新的 standalone 本機 Qwen→Local Agent RTL/XSim 修正閉環及 Vivado/Vitis/HLS 版本啟動通過；工具 sandbox 外網阻斷 smoke 通過。M13/M14 仍 IN PROGRESS，M15 仍 PRE-FINAL；Telegram 等待 BotFather token，沒有宣稱 FINAL_GOLDEN_PASS。詳見 [M15 readiness follow-up](docs/M15/RESULT.md) 與 [M13 evidence](docs/M13/evidence/2026-10-12/local-qwen-standalone-agent-rtl/)。

**2026-10-13 Ross A/B update：** 本地 Qwen3.8 + Local Agent 已實際呼叫 Ross Skill 與本機 Knowledge Base MCP。T1 A=3/3、B=0/3；修正後 T2 A=3/3、B=1/3（另兩次 B 因 8192-token context overflow 失敗）；T3 兩組 3/3，但 Ross 平均慢 2.69%。正式 T2 3×3 cohort 已完成，先前 v5/v6/v7 為分開保留的診斷歷史。M13 維持 IN PROGRESS/PARTIAL，沒有宣稱 Ross 普遍提升成功率或速度。細節與失敗樣本見 [M13 Ross benchmark report](docs/M13/M13_ROSS_AB_BENCHMARK_REPORT.md)。

**2026-10-13 Local Model Lab completed cohort：** Qwen3.8 Q4_K_XL 與 Gemma 4 31B 各完成 T1/T2/T3 Ross／Non-Ross 共 18/18 PASS；T1/T2 並有獨立 Vivado synthesis，T3 有 HLS C simulation／synthesis。兩者使用已實測的 Vulkan backend，24 threads、16K context，正式 Qwen CPU 服務已還原。Gemma 的 T1/T3 較快；Ross-assisted T2 則 Qwen 較快，不能宣稱單一模型全面勝出。先前 CPU exploratory failures 與 harness-invalid pilot 保留為歷史，不當成本次排名。GPT-OSS／Devstral 未安裝、第五槽未指定，整體 Lab 仍 PARTIAL。詳見 [Local Model Lab](docs/LOCAL_MODEL_LAB/RESULT.md) 與 [流程](docs/LOCAL_MODEL_LAB/PROTOCOL.md)。

**2026-10-14 Qwen optimization：** 已完成安全配置比較，推薦 FAST Vulkan 8K／ENGINEERING Vulkan 16K／SAFE CPU24 MTP。ROCm 較快但後續載入觸發 swap guard，調校保持 PARTIAL；正式模型配置未更動，API／Local Agent 已恢復。詳見 [實測、限制與配置](docs/LOCAL_MODEL_LAB/QWEN_PERFORMANCE_OPTIMIZATION.md)。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求依 Roadmap gate 管理。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。Ubuntu 24.04.4 native Xilinx success 不等於 AMD/Xilinx official OS support；M11 bounded DDR3 hardware PASS 僅代表其報告列出的範圍，不等於全容量 DDR coverage；M12 的實體 JTAG-to-AXI round-trip 是另外的控制/資料路徑證據，仍不等於 production XRT application integration。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
