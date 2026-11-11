# AI370-2 FPGA 工程模型品質驗證規格

**文件狀態：`QUALITY_HARNESS_READY`；最新正式執行狀態：`PREFLIGHT_BLOCKED`；完整比較：`NOT_COMPLETED`。**

使用者已明確指示開始執行並再次確認「直接開始」。本次已開始 harness／工具校準；校準資料不計入新題庫的正式分數。正式 72 個 Pilot 樣本仍須等凍結題庫、八題固定 runner、validators 與安全 preflight 完成後才可計數。

使用者明確同意在 SwapFree 低於 2 GiB 時繼續；這只豁免開始門檻中的 2 GiB 建議值，不豁免執行期間的 64 MiB swap 增長、RAM、持續 swap-out、PSI、磁碟、GPU/kernel、OOM 與 harness integrity 停止閘門。不執行 `swapoff`、清 cache 或改正式 Agent 模型設定。

效能前階段的結案紀錄為 `PERFORMANCE_COMPLETE / COMPLETE_WITH_NOTES`，涵蓋 22 款模型、44 組 CPU/Vulkan、1,829 個完成 case 與 5,487 次請求。基準報告：`output/ALL_MODEL_SPEED/20261020T175626+0800/REPORT.md`。

## 1. 目的和公平原則

本階段比較九款本機模型執行受控工程任務的能力。評分只依固定規格、固定工具和固定驗收器的結果；不由 Codex 或另一個 LLM 判定工程正確性。

九款模型在同一任務使用完全相同的 prompt、輸入檔案 bytes、seed/變體、工具集合、工具版本、驗收器、timeout、completion/tool-call 上限及 PASS 條件。不同重複樣本使用三份凍結等價變體；每份變體都由九款模型完整跑過，模型順序平衡輪替。每個樣本都從原始模板建立乾淨 workspace，不共用生成結果。

既有 Qwen3.8 工程資料只用來確認 harness 與估計執行時間，**不計入正式比較**。九款模型都在同一份新凍結題庫從頭重測。

## 2. 參賽模型

八款新候選加一款既有工程基準。模型 ID、GGUF 檔名、位元組數、SHA256、GGUF metadata（量化、架構、參數資訊）寫入每個 run 的 protocol；下列速度只作選型背景，不作品質分數。

| 類別 | 固定模型 ID | GGUF 檔案（目前位於 `models/`） | 既有 Vulkan 生成中位數 token/s |
|---|---|---|---:|
| 高速工程候選 | `Mellum2.1-12B-A2.5B-Thinking-Q4_K_M` | `Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf` | 47.56 |
| 高速 Agent 候選 | `gpt-oss-20b-UD-Q4_K_XL` | `gpt-oss-20b-UD-Q4_K_XL.gguf` | 32.29 |
| 高速大型候選 | `Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M` | `Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf` | 35.77 |
| 通用候選 | `gemma-4-26B_q4_0-it` | `gemma-4-26B_q4_0-it.gguf` | 27.72 |
| 輕量 Agent | `Qwen3-4B-Q4_0` | `Qwen3-4B-Q4_0.gguf` | 31.06 |
| 中型候選 | `Qwen3.5-9B-UD-Q4_K_XL` | `Qwen3.5-9B-UD-Q4_K_XL.gguf` | 14.13 |
| 低量化候選 | `Qwen3.8-27B-UD-IQ2_XXS` | `Qwen3.8-27B-UD-IQ2_XXS.gguf` | 9.68 |
| Coding 專用候選 | `Devstral-Small-2-24B-Instruct-2512-Q3_K_M` | `Devstral-Small-2-24B-Instruct-2512-Q3_K_M.gguf` | 7.14 |
| 既有基準 | `Qwen3.8-27B-UD-Q4_K_XL` | `Qwen3.8-27B-UD-Q4_K_XL.gguf` | 4.63 |

全檔大小、SHA-256 和 mtime 已擷取至 `output/QUALITY_MODEL_VALIDATION/20261022T182952+0800/model-integrity.json`。此實際 inventory 顯示模型放在 `models/`，不是目前舊設定中的 `models/GGUF/`；新 runner 必須明確採用經 hash 驗證的上述路徑。

## 3. Pilot 和總樣本分配

總計 **9 模型 × 8 題 × 3 個共同變體 = 216 個主樣本**。Pilot 是第一個完整共同變體，不是九款模型各自抽測部分題目：

| 階段 | 分配 | 數量 | 用途 |
|---|---|---:|---|
| Pilot P1 | 每款模型各跑 T1–T8 的變體 V1 | 9 × 8 × 1 = **72** | 驗證題庫、固定工具、時間及資源閘門；模型間可比較 V1 |
| 完整樣本 P2 | 每款模型各跑 T1–T8 的變體 V2 | 72 | 增加第二個共同樣本 |
| 完整樣本 P3 | 每款模型各跑 T1–T8 的變體 V3 | 72 | 增加第三個共同樣本 |

V1、V2、V3 在各模型間是完全相同的輸入 bytes 和驗收條件。題目數值或缺陷位置可依變體改變，但同一變體不得因模型而變。模型、題目、變體的執行次序用 protocol 記錄的固定隨機 seed 平衡排列；同一時間只載入一款模型。

先跑完 72 個 Pilot。Pilot 後檢查題目有效性、測試器穩定性、OOM/Swap/GPU 狀態及各題耗時；若發現 harness 缺陷，該題所有模型在該變體的樣本標成 `BLOCKED/HARNESS_INVALID`，修好並凍結新版本後，九款模型一起重跑該共同配對，不單獨補跑失敗模型。Pilot 不因得分不好而改門檻或丟棄結果。Pilot 通過審查後才進 P2/P3。

使用者提出「重複做」時，完整 216 樣本結束後才可開始下一 cycle；下一 cycle 必須凍結新版本且所有模型共用，舊 cycle 永不覆寫。每個 cycle 需要明確 status 與 stop marker。

## 4. 凍結題庫 T1–T8

以下每一題建立三份 V1–V3。每份含 `TASK_SPEC.md`、輸入工程檔、隱藏驗收素材、唯讀固定 runner、工具版本記錄和 SHA256 manifest。參賽模型看得到完整需求和允許讀取的普通輸入檔，看不到隱藏向量、mutant、預期答案和驗收器實作。每題的九模型共用相同檔案及工具輸出條件。

| ID | 完整任務規格 | 可修改檔案 | 固定工具與 PASS 證據 |
|---|---|---|---|
| **T1 RTL Generation** | 依固定 AXI4-Lite 子集規格，從空白 `rtl/axi_regs.sv` 完成 32-bit slave：AW/W 獨立握手並最多保留一筆 pending write；四個 word-aligned register；WSTRB byte write；OKAY response；單筆 read response；read/write backpressure 不丟交易；reset 後值確定。禁止實作規格以外的 AXI features。V1–V3 變更 register map 常數與 reset 值但介面/難度相同。 | 唯一允許 `rtl/axi_regs.sv` | 固定自檢 testbench 以多種 AW/W 到達次序、背壓、WSTRB、邊界位址及 reset 驅動 DUT；Vivado 2026.1 XSim compile+run 必須有 marker；固定 Vivado synthesis 再檢查 latch 和 elaboration。兩項均過才 PASS。 |
| **T2 RTL Debug** | 給一個可編譯但行為錯誤的 AXI-Lite slave 和真實 baseline XSim log。找出一筆寫交易在 AW、W 非同拍時遺失的缺陷，修正 handshake/state；不得改介面或測試條件。V1–V3 對應三種等價缺陷 seed，要求一致。 | 唯一允許 DUT RTL 檔 | Vivado 2026.1 XSim：未修 baseline 必須 FAIL 指定 assertion，修後完整固定 regression PASS；固定 synthesis/elaboration PASS；來源 diff 必須只在 allowlist。 |
| **T3 Testbench** | 針對提供的正確 AXI-Lite DUT 和介面 spec，產生自檢 SystemVerilog testbench。至少覆蓋獨立 AW/W 次序、雙向 backpressure、byte strobes、非法/未映射讀寫、reset、連續交易和 response 穩定性；不能改 DUT。V1–V3 用同一 scenario 集合及不同隱藏資料值。 | 唯一允許 `sim/tb_axi_regs.sv` | 固定 harness 對正確 DUT 執行 XSim 必須 PASS；再對固定的每一個 mutation DUT（例如 AW/W 同拍假設、忽略 WSTRB、response/backpressure 錯誤、reset 值錯誤）執行，必須全部被 testbench 偵測而 FAIL。固定 coverage/parser 確認每個要求 scenario 有執行記錄。不得用 LLM 判斷 testbench 品質。 |
| **T4 Vivado XSim** | 給有多檔 RTL、介面正確但含 compile/elaboration 缺陷的隔離專案及原始 XSim diagnostic。定位 top/source/package/width/port connection 缺陷並修允許的設計檔，讓完整模擬通過；報告實際診斷、修改與模擬命令結果。三變體使用同一模組拓撲、不同等價缺陷。 | 固定 allowlist 中的 DUT/package RTL；不能改 testbench、Tcl、runner | 使用固定、唯讀 Tcl 的 Vivado 2026.1 XSim compile/elaborate/sim；runner 先確認缺陷 diagnostic，再要求修後 terminal PASS marker 和完整 exit code 0。 |
| **T5 Synthesis** | 給含一個 latch/incomplete assignment 及一個位寬/資源效率缺陷的可綜合 RTL。修好兩者，維持功能規格及 I/O；不要求時序 closure。V1–V3 是等價缺陷。 | 固定 allowlist 的設計 RTL | Vivado 2026.1 固定 synthesis Tcl、固定 part/constraints；檢查 exit 0、top 存在、零 inferred latches、零指定嚴重 DRC/elaboration error、資源上限在凍結規格內，並輸出 utilization report。固定 RTL regression 必須 PASS。WNS 僅記錄，不作 timing closure 宣稱。 |
| **T6 Vitis HLS** | 修正固定 `invert32` 類型之 C++ kernel，使每個輸入 sample 按 spec 反相/映射、支援定長 frame 和邊界；不得改 testbench/config/interface。V1–V3 改變 frame/vector golden data但共用同一計算需求。 | 唯一允許 `src/invert32.cpp` | AMD Vitis HLS 2026.1 固定流程執行 C simulation 與 C synthesis；兩個 exit/terminal markers 都 PASS、golden output 全相等、不得有不可綜合警告類別。保存 csim/csynth report、latency/II/resources（工具未產生者 N/A）。 |
| **T7 AMD Ross** | 先依題目讀指定 AMD Ross Skill/reference，查詢相符 Vivado 2026.1 文件，再完成一個與 T4 同介面/同 V1–V3 共用資料的新 XSim 修復任務；以文檔證據支援診斷，不能只寫摘要。 | 與 T4 同一 allowlist 規則 | 固定本機 `ross_skill_read`、`ross_doc_search` 和 Vivado XSim。兩種實際 MCP call 成功且發生在修改/模擬前；trace 保存來源標題、查詢、回覆及工具結果；XSim 最終 PASS。Ross 工具不可用時該樣本 BLOCKED，不能改用網路搜尋或略過。 |
| **T8 Autonomous Agent** | 以一個新的隔離 AXI-lite 小專案，從讀規格、baseline 執行、診斷、設計修正、模擬、synthesis 到產生交付摘要完成閉環。題目要求與隱藏 check 固定；三變體等價。Agent 必須根據實際工具回饋迭代，禁止人為補修。 | 只允許該題凍結 allowlist 中的 DUT/HLS source；runner、測試、Tcl、規格唯讀 | 同一受限 Local Agent function tools + 固定 XSim、Vivado synthesis 驗證工具；所有階段需 trace、來源 hash 和 PASS marker。總工具呼叫/時間上限在 frozen protocol 固定；超限不 PASS。驗收器自動確認交付摘要提及的結果與實際 log/hash 一致。 |

### 題庫和 M13 的關係

- **T2** 沿用 M13 T1（單檔 AXI-Lite）與 T2（多檔 AXI-Lite）的隔離方式、baseline-first、最多三次驗證和 fixed XSim 驗收模式；正式 V1–V3 需建立未用於過往模型比較的等價 defects/values，M13 原題只供 harness calibration，不計分。
- **T6** 沿用 M13 T3 `invert32` 的安全隔離、固定 testbench/config、C simulation + C synthesis 方式；建立新凍結 V1–V3 vectors。M13 舊模型結果不混入新比較。
- **T1、T3、T4、T5、T7、T8** 是此品質階段新增題型，不能用過往結果代替九款模型的正式共同測試。
- 任何 seed 複製前先查明來源、license/可用性、hash；凍結後九款模型一律用同一版本。

## 5. 模型與執行設定

- 每款模型固定 Vulkan；載入 log 必須證明正向 GPU offload。CPU fallback、另一模型 fallback 均禁止。若某候選載入/OOM/offload 失敗，按狀態表記錄並停止該候選，不偷換設定。
- 固定 llama-server binary hash/version、GPU/device、context=16384、threads=24（啟動時重新讀 affinity，並全 run 固定）、batch/ubatch=2048/512、parallel=1、reasoning off、temperature=0、seed 和 API prompt body。completion、單次 request timeout、總樣本 timeout、tool-call cap 固定並寫 protocol；建議沿用 LocalAgent 上限：最多 14 calls、最多 2,048 completion tokens、每樣本總時限 2,400 秒。若任務需要不同上限，必須在批准前修訂，不能中途調高。
- system prompt、LocalAgent commit/hash、tools schema、tool adapter、Ross 回覆截斷長度、工具版本、Vivado/Vitis build、Tcl、hidden validators 一併凍結。各模型只替換 model ID/path/endpoint，其餘參數相同。
- prompt、完整模型原始輸出及工具輸入/輸出 trace 僅保存在隔離 output evidence 目錄；不得截掉失敗診斷。所有模型每次以相同請求上限和 timeout 運行。

## 6. 工具及人工介入邊界

- XSim 由本機固定 Vivado 2026.1 batch Tcl/runner 執行；不允許模型修改 runner 或 testbench（T3 除外，T3 僅允許改 testbench）。
- Synthesis 由固定 Vivado batch Tcl 執行；輸出 utilization/timing summary；不執行 implementation、燒錄或硬體 programming。
- HLS 由固定 Vitis HLS 2026.1 config/script 執行 `csim_design` 和 `csynth_design`。
- 代理工具只能包括隔離 workspace 的 `list_files/read_file/apply_patch/apply_replacement/run_xsim/run_synthesis/run_hls/ross_skill_read/ross_doc_search` 中該題 allowlist 的子集。無一般 shell、任意網路、寫正式 repo 或讀 hidden checker 的能力。題庫實作前須為尚未存在的 `run_synthesis` 增加固定 allowlist executor，並由非模型 fixture 驗證。
- 不允許 Codex/人員在模型樣本執行期間修改答案。所有修補必須出自該模型 trace，並以 before/after hash 與 patch path 證明。

## 7. 狀態定義

| 狀態 | 判定 |
|---|---|
| **PASS** | 樣本完成；所有指定固定 validator 產生 exit 0 與 terminal PASS marker；hidden scenario/mutation、檔案 allowlist、工具 trace、hash 均符合；無未解資源/安全異常。 |
| **FAIL** | 題目與工具有效、模型已取得公平執行機會，但未按期限完成、固定 validator 失敗、工具操作違規、修改禁止檔案、漏掉必需 Ross call 或交付內容與實際 log 不符。保留錯誤原因及最後狀態。 |
| **BLOCKED** | 無法公平開始或繼續：模型缺檔/hash mismatch/load/offload failure、硬體/工具/license/MCP 故障、安全閘門、或容量不足。記 blocker 與 evidence；不將其算模型能力 FAIL，不自動 fallback。 |
| **NOT_TESTED** | 尚未排程、因 cycle 停止未開始，或 blocker 發生後尚未執行；只允許這類狀態不計 pass-rate denominator。 |
| **HARNESS_INVALID** | 凍結題庫/runner/validator 自身錯誤或結果不確定。受影響的共同 seed 對九款模型全數標此狀態，修復後以新版本共同重測。不得判成模型 FAIL。 |
| **PARTIAL** | 樣本已開始並產生有用中間結果，但整體任務未達 PASS；彙總為未通過，保留實際子階段證據。 |

Pilot 各模型/題目結果都保留。不得因 pilot 成績而重寫題目、改驗收器、剔除某模型或改變 timeout。題庫自身有效性由固定 validator 和工具 fixture 驗證，不用 LLM judge。

## 8. 指標與比較

每樣本保存並以 machine-readable JSON/JSONL 彙總：模型 ID、GGUF bytes/SHA256/metadata、prompt hash/完整 prompt、輸出文字與 token usage、所有 tool-call arguments/results、模型 request 時間、每一 tool 時間、整體 wall time、baseline/final status、驗證輪數、修改輪數、patch/diff、修改前後 hash、PASS/FAIL marker、stdout/stderr、XSim/Vivado/HLS logs/reports、RAM/swap/GPU/kernel samples、失敗分類、seed、runner/validator/binary hashes。

比較欄位：每題共同變體通過數（0–3）與率、整體通過數（0–24）與率、一次驗證通過率、patch 次數、tool calls、Ross 成功使用率、模型推論秒數、固定工具秒數、完整 wall seconds，以及全 PASS 樣本的時間中位數/範圍。失敗/timeout wall time 另列，不能從效率比較中隱去。

先以通過率比較，再以修正/驗證次數及全 PASS 完成時間做多目標 Pareto 比較。T1–T8 分項呈現，不以單一 token/s 或 LLM 評審分數定勝負。小樣本只作方向性結果，不宣稱統計顯著性；最終建議保留 1–2 個通用/工程主力，可能另列專用模型。任何刪除都不在本階段授權內。

## 9. 安全 preflight 與停止閘門

效能階段結束觀察到 swap used 約 7.2 GiB、free 約 0.8 GiB；此值不代表目前壓力，但必須重新量測，不能直接開始長時間模型輪替。本文件制定以下 preflight，**不會自行 `swapoff`、清 cache 或以其他方式釋放 swap**：

1. 讀取 `MemAvailable/MemTotal`、`SwapFree/SwapTotal`、至少 5 分鐘的 `pswpin/pswpout` delta、`/proc/pressure/memory`、磁碟空間、Vulkan device health、相關 kernel journal、LeMonade/local UI health 和現有 model server/process。所有檢查唯讀。
2. 開始條件：MemAvailable ≥ `max(8 GiB, OS RAM 20%)`；SwapFree ≥ **2 GiB**；連續觀察 5 分鐘 pswpout 與 pswpin 各自增量均 <1 MiB；memory PSI `full avg10 < 1%` 且沒有持續上升；disk free ≥20 GiB；GPU 無 reset/fault；工具/模型狀態空閒。任一項不符則 `PREFLIGHT_BLOCKED`，只回報、不載入模型、不嘗試整理 swap。
3. 每次模型載入前和樣本執行中輪詢 RAM、Swap、swap-in/out rate、PSI、disk、GPU/kernel audit。停止閘門：MemAvailable < `max(6 GiB, OS RAM 12.5%)`；相對本 session 基線 swap used 增加 >64 MiB；pswpout 達 ≥1 MiB/min 並持續 60 秒；PSI full ≥20% 持續 10 秒；disk free <20 GiB；GPU reset/fault/kernel audit unreadable；model server crash/OOM；protected package/module/harness hash drift。
4. 任一閘門觸發：立即停止本 controller 與本 controller 建立的 process group，記錄目前樣本 `BLOCKED` 或 `PARTIAL`、未開始項目 `NOT_TESTED`，保存 manifest/status；不停止 embedding、桌面、其他服務，不啟動下一模型。嚴重 GPU/kernel fault 時不重新載入正式 Qwen GPU model。
5. 每個模型載入前驗證 hash/size；只使用一個本次 controller 持有的 llama-server；正式 Agent Qwen 模型設定只讀，停止後不寫入 config/recipe。不要因歷史驗證記錄而跳過真實 preflight。

## 10. Git 與正式模型保護

目前 Git 工作目錄已有先前未提交修改及未追蹤模型檔。執行前保存本次讀到的 `git status --short`，不 stash、reset、checkout、clean、commit 或刪除檔案。新 runner 只新增隔離腳本/題庫檔；既有 user changes 保持原狀。正式 Agent 使用的 Qwen3.8 model ID、path、recipe/config、API profile 不修改；不註冊候選為預設模型。

## 11. 執行前仍需完成的製備工作

使用者已批准開始準備和執行；以下驗證完成前不得把結果標為正式 Pilot：

1. 依 T1–T8 建立三份共同變體及 hidden golden/mutant assets。
2. 實作題目隔離 workspace、固定 XSim/Vivado synthesis/Vitis HLS adapters；新增工具需明確 allowlist，不能暴露 shell。
3. 用非參賽固定 fixture 驗證每題 baseline FAIL/預期 PASS、mutation sensitivity、resource cleanup、manifest/hash 與 stop marker；不呼叫九個參賽模型。
4. 凍結所有 prompts、models metadata、commands、tools、validators、random seed、timeout、資源閘門和 stop protocol；在開始前重跑唯讀 preflight。
5. 開始 P1 前重跑唯讀 preflight；SwapFree 2 GiB 規劃門檻依使用者指示豁免，其餘安全條件照常。題庫 fixtures 必須全部通過，才可開始 P1 的 72 個 Pilot。
6. 只有完成一個共同變體矩陣後才能開始下一變體；依使用者「開始執行，直到我說停止」的指示，完成 V1–V3 後建立新 cycle 繼續。每個 cycle 使用獨立輸出與 manifest，永不覆寫舊結果。若 T7 Ross endpoint 缺失，所有模型的 T7 樣本一致記為 BLOCKED，並保留其他樣本執行。

## 12. 框架與執行狀態（2026-10-27）

- 規格文件：本檔 `docs/LOCAL_MODEL_LAB/QUALITY_VALIDATION_PLAN.md`。
- 九款 GGUF、T1–T8 題庫與 V1–V3 變體維持凍結；模型速度只作候選背景，不計入工程品質分數。
- 九款 GGUF 已完成全檔 SHA-256 記錄。
- M13 T1 baseline XSim 與 M13 T6 Vitis 只作工具校準；Mellum M13 T1 曾以 512 token 上限和 2,048 上限各跑一次，兩次均未完成修補，且因使用舊題／現有 LocalAgent tool policy，不計入正式比較。
- T1–T8 的 V1–V3 凍結題庫、隔離 workspace、固定 XSim/Vivado synthesis/Vitis HLS adapters、hidden validators 與非模型 fixture 均已完成；所有 24 個變體 fixture 通過。證據列在 `docs/LOCAL_MODEL_LAB/quality-corpus/v1/CORPUS_PROGRESS.json` 及 `output/QUALITY_MODEL_VALIDATION/20261022T182952+0800/fixtures/runs/`。
- 品質 runner 提供 `--pilot-only`，只排程共同 V1 的 9×8=72 個樣本並在該矩陣結束後停止；完整週期排程為共同 V1、V2、V3 三個 72 樣本矩陣，共 216 個。每個矩陣先由全部模型完成，再進入下一變體；不同變體的模型與任務順序以記錄的 seed 輪替。
- runner 強制唯讀 preflight 至少 300 秒，不提供略過 preflight 的 CLI 選項。安全中止或使用者停止後，未執行的排程項目明確保存為 `NOT_TESTED`；workspace／runner 錯誤會標為 `HARNESS_INVALID`，不算模型 FAIL。
- 框架程式測試：`scripts/test_quality_pilot.py` 10/10 通過（含 mocked orchestrator、72/216 排程、preflight gate、stop ledger，以及 24 個 frozen workspace 隔離 smoke）；`scripts/test_quality_local_agent.py` 6/6 通過；相關 Python `py_compile` 與 `git diff --check` 通過。這些測試不啟動參賽模型，也沒有執行 preflight。
- 2026-10-22 的舊試跑在第 54 個樣本停止，統計為 47 FAIL、7 BLOCKED，原因是 `SUSTAINED_SWAPOUT_GUARD`；此批次不是完整共同 Pilot，且含早期 harness 版本問題，**不得用作九模型排名**。原始資料保留於 `output/QUALITY_MODEL_VALIDATION/20261022T202138/cycle-0001/`。
- 2026-10-27 的三次五分鐘唯讀 preflight 均以 `SWAPIN_DURING_PREFLIGHT` 阻擋，沒有開始新的模型樣本。最新狀態為 `output/QUALITY_MODEL_VALIDATION/status.json`，三份紀錄分別位於 `output/QUALITY_MODEL_VALIDATION/20261027T162155/preflight.json`、`20261027T162747/preflight.json`、`20261027T163315/preflight.json`。
- 正式 T7 需要本機 AMD Ross Doc Search MCP。`AI370_ROSS_DOCSEARCH_URL` 未設定，且 `http://127.0.0.1:8080/mcp/doc-search` 連線遭拒；Pilot 將把九款模型的 T7 樣本一致標記 BLOCKED，不使用替代文件來源。
- 使用者指示先完成測試框架程式；本輪僅修改品質 runner、隔離測試與規格文件，未重跑 preflight 或模型品質樣本，未更動安全門檻、正式模型設定或服務。

## 13. Harness 變更與可比性限制（2026-11-09）

本節記錄 `scripts/local_agent.py` 的 harness 行為變更。**未執行 freeze**：`output/LOCAL_MODEL_CONTROLLER/plans/20261103T065105Z/v2-v3-plan.json` 仍是最新凍結計畫，未建立新計畫，也未啟動 runner 或模型。

### 變更內容

- **Correction feedback 只保留最新一則**：第一次 correction 的 system prompt 與舊版逐字相同；自第二次起，新 correction 取代上一則而非累加，單則上限 4,000 字元。舊版每次 correction 都附加到 system prompt（實測 5 次 correction 由 846 增至 1,706 字元）。
- **Trace 預設不保存 prompt 原文**：`model_request` 只記錄 request 參數（model、temperature、max_tokens、seed、tool_choice）、完整 request body 的 SHA-256 與 bytes、每則 message 的角色／bytes／SHA-256，以及工具名稱。不保存任何 prompt 文字或摘錄。
- **單筆 trace 事件上限 64 KiB**：超過時改寫為摘要，只保留 `event`／`name`／`call`、原始 bytes 與 SHA-256。實測既有 trace 中 `tool_call` 與 `model_response` 單行最大約 5–6 KB，正常樣本不會觸發；舊版 `model_request` 單行最大約 52 KB，且佔 trace 總量約 81%。
- `max_completion_tokens` 可接受上限為 8,192（CLI 預設仍為 512）。
- **可選的嚴格 trace 模式**：設 `AI370_TRACE_MODE=hash-only` 時，除 `event`、`name`、`call`、`model`、`path(s)`、`request_sha256`、`request` 等 metadata 外，模型回覆、工具參數／結果、patch 與錯誤訊息一律只記 bytes 與 SHA-256；工具結果另保留 `ok`／`stage`／`status`。預設為 `full`，維持第 4 節 T7 對 Ross 查詢／回覆的 trace 要求與失敗診斷；其他值會使 agent 拒絕啟動。品質 runner 以 `os.environ.copy()` 啟動子程序，環境變數會傳到 agent。使用嚴格模式的樣本無法從 trace 回看 T7 證據，必須在該批次 protocol 中註明。

### 可比性限制

- `local_agent.py` 的 SHA-256 自 commit `b0638ca` 起已和 2026-11-03 凍結計畫記錄的值（`d96c6e87063f…`）不同，本次再度變更。凍結計畫中的 `harness_sha256` 只是記錄，不被任何程式強制比對；每個樣本實際使用的 harness 以該樣本 `protocol.json` 的 `runner_sha256` 為準。
- **新 harness 產生的樣本不得與既有 V1／V2（及先前 V3、T7 補充）樣本直接混合比較或合併計分。** 舊樣本在其記錄的 `runner_sha256` 下仍有效。要比較，必須依第 3 節原則，以同一 harness 讓九款模型重跑整個共同變體。
- 第 5 節「prompt…trace 保存」與第 8 節「prompt hash／完整 prompt」中的**完整 prompt 保存要求由本節取代**：prompt 一致性改以 `request_sha256` 與各 message SHA-256 證明；要重現 prompt 原文，需以相同 harness 與輸入重新產生。工具輸入／輸出與模型回覆仍保存於 trace，受 64 KiB 單筆上限約束。

### Controller 可靠性變更（不影響模型樣本內容）

- 健康資料無法讀取（`/proc` 讀取失敗或欄位缺漏／型別不符）時，若有 runner 執行中即 fail-closed：記錄 `HEALTH_UNREADABLE_GUARD`，以既有 `CHILD_SAFETY_STOP` 流程停止 runner；controller 持續輪詢，不自動重跑。
- 同一份無效 command 在單一 controller process 內只記錄一次 `COMMAND_REJECTED`；讀到有效 command 後重置，controller 重啟後也會重新記錄。
- 每次 runner 執行只送一次 guard SIGINT：舊版在 runner 結束前每 30 秒重送 SIGINT 並重複記錄 `CHILD_SAFETY_STOP`，可能打斷 runner 記錄未完成樣本的收尾流程。controller 關閉時的 `CONTROLLER_SHUTDOWN` 停止流程不變。
- 收到 SIGTERM 後 1 秒內開始關閉：舊版主迴圈一次 `sleep` 30 秒，SIGTERM 要等睡完才生效（實測 27.1 秒）；2026-11-09 19:33 與 11-11 09:02 兩次登出時 session 先被拆除，controller 未能寫入 `CONTROLLER_STOPPED`。若當時有 runner 執行，`CONTROLLER_SHUTDOWN` 停止流程也會被略過。新版每秒檢查停止旗標，實測 0.1 秒正常結束。11-09 23:42 的 GNOME Shell 當機（KVM 切走後螢幕不存在，又以 AnyDesk 遠端操作，觸發 mutter `logical_monitor` assertion）期間 controller 持續運作，telemetry 沒有中斷。

### 輔助工具修正（非 harness 身分檔案，不影響既有樣本可比性）

- `validate_quality_corpus.py`：latch 判定改與 executor 相同，可辨識 Vivado `Synth 8-327` 的 `inferring latch`；T3 reference 記錄改以 repo 根目錄解析，不依賴 cwd；T3 reference 編譯失敗改記為 fixture FAIL，不再中止整個 run；executor 最後一行若為合法 JSON 但非 object，記為 `HARNESS_INVALID`。已唯讀檢查既有 fixture 記錄：30 個含 latch 警告的檔案全是 T5 baseline（預期內），T1/T2 reference 沒有 latch 警告，因此 2026-10-22／11-03 的 fixture 結論不受舊 regex 影響。
- `run_quality_remediation_fixtures.py`：fixture 逾時時 Python 回傳 bytes 輸出，舊版會在寫 JSON 時崩潰而沒有 `report.json`；現已解碼後照常寫入。
- `freeze_quality_v2_v3_plan.py`：所有雜湊輸入讀取成功後才建立計畫目錄，輸入缺漏時不再在 plans 目錄留下空的時間戳目錄。
- `run_all_model_speed.py`：沒有可用模型時不再空轉，直接以 `NO_ELIGIBLE_MODELS` 結束。

### Harness 評分與安全修正（2026-11-11；改變評分或安全分類）

以下修改 harness 身分檔案，與上述 correction／trace 變更同屬新 harness，不得與 V1／V2 混比。

- `quality_task_executor.py`：T1／T2／T8 與 T3–T6 一致，驗證期間來源被改動即不得 PASS（舊版會判 PASS 並僅記錄 `source_unchanged_during_validation: false`）。
- `run_quality_guarded_trial.py`：
  - 同一輪輪詢觸發多個 guard 時依固定優先序取最強原因：完整性與安全 guard 優先於 `USER_STOP`，`SAMPLE_TIMEOUT` 最低。舊版後執行的逾時或使用者停止會覆蓋資源 guard，使樣本記為 `PARTIAL` 而 pilot 不進入 SAFETY_STOP。未登記的原因名稱會直接報錯。
  - 執行中使用啟動時驗證過的 protocol 副本，並比對 `protocol.json` 雜湊；舊版每次重新讀取，可同時替換 runner 與其雜湊而通過。
  - 執行中重驗 workspace Git HEAD，並以 `--ignored` 檢查，涵蓋 commit 或 `.git/info/exclude` 隱藏的 allowlist 外檔案。
  - `/proc` 讀取失敗記為 `RESOURCE_TELEMETRY_UNREADABLE`，journalctl 逾時或無法執行記為 `KERNEL_AUDIT_UNREADABLE`，兩者都 fail-closed 並照常寫出 `guarded-result.json`；舊版直接拋出例外，pilot 只能記為 `HARNESS_INVALID` 而無 guard 細節。
  - 可編輯檔以啟動時驗證過的 protocol 為準；controller 提供的清單與 protocol 不一致時拒絕啟動。舊版未提供清單時，T4–T7 會得到錯誤的預設檔 `rtl/axi_regs.sv`。
  - 結束 agent 時精確比對 `--workspace` 參數；舊版以子字串比對，會連帶中斷 `…/workspace2` 或只是在其他參數提到該路徑的 agent。
- `quality_task_executor.py`（2026-11-11 下午）：Vivado／Vitis 工具逾時改記為該步驟失敗（`exit_code: null`、`timed_out: true`，記錄附 `QUALITY_TOOL_TIMEOUT`），任務判 FAIL 並照常寫出 `result.json`；舊版拋出例外，`main()` 回報 `HARNESS_INVALID`，pilot 因而停止整個 cycle。T3 中 mutant 模擬逾時代表 testbench 沒有規格要求的有限 watchdog，記為 `TOOL_TIMEOUT` 且**不算**抓到 mutant。T6 C simulation 逾時改提供「超過時間限制」診斷，不再誤稱 vector mismatch。Vivado／Vitis 環境設定載入失敗仍為 `HARNESS_INVALID`。

### 已知但未修正的 harness 問題

- **T8 題目缺陷**：`TASK_SPEC.md` 要求「依本檔案的介面與行為需求」實作，但未列出任何介面（port 名稱、位寬、reset 同步／非同步與極性），public stub 也只有 `module axi_regs;`；hidden testbench 依賴 `aclk`、`aresetn` 與 17 個 `s_axi_*` port。模型只能從 baseline elaboration 錯誤推測名稱，位寬沒有線索。依第 3 節規則，修正需建立新版題庫並讓九款模型共同重跑 T8；既有 T8 樣本是否改標 `HARNESS_INVALID` 需另行決定。
- `quality_task_executor.py`：T6 C simulation 非逾時的失敗（編譯錯誤或 vector mismatch）仍使用同一句 vector mismatch 診斷。

### 執行下一批樣本前

1. 確認接受上述可比性限制，並決定剩餘 harness 問題是否在下一批之前修正。
2. controller 已於 2026-11-11 13:39 重啟並載入 SIGTERM 修正。harness 檔案（executor、guarded trial、agent）由每個樣本的新程序載入，修改後不需重啟 controller。
3. 以實際 Vivado／Vitis 執行 `scripts/validate_quality_corpus.py --task all`，確認題庫在新 harness 下仍全部通過。
4. 刻意執行 `scripts/freeze_quality_v2_v3_plan.py` 建立新凍結計畫。注意 controller 的 `AUTO_CONTINUE_V2_V3 = True`：狀態符合時，凍結後可能自動開始模型執行。

### 離線測試

`scripts/test_local_agent.py`、`test_local_agent_ui.py`、`test_quality_local_agent.py`、`test_local_model_controller.py` 涵蓋上述行為，不啟動模型、runner、systemd 或網路。`test_quality_local_agent.py` 改由版本控制中的 corpus 在系統 temp dir 建立 workspace，fresh clone 不再依賴被忽略的 `output/`。缺少模型權重時，`test_local_model_lab.py` 的權重存在性檢查預設 skip；設 `AI370_REQUIRE_MODEL_WEIGHTS=1` 可強制驗證。另有 `test_quality_task_executor.py`、`test_run_quality_guarded_trial.py`、`test_build_quality_corpus.py`、`test_validate_quality_corpus.py`、`test_freeze_quality_v2_v3_plan.py`、`test_run_quality_remediation_fixtures.py`、`test_run_all_model_speed.py` 以 mock 取代 Vivado／XSim／Vitis／模型／`/proc`，驗證各工具的決策邏輯；它們不能證明真實工具輸出的格式。
