# T8 規格缺陷與既有樣本重新分類（2026-11-11）

## 缺陷

`docs/LOCAL_MODEL_LAB/quality-corpus/v1` 的 T8（Autonomous Agent）`TASK_SPEC.md` 要求「依本檔案的介面與行為需求」實作 `rtl/axi_regs.sv`，但檔案沒有任何介面說明：沒有 port 名稱、方向、位寬，也沒有說明 reset 是同步或非同步、高態或低態有效。public starter 只有 `module axi_regs;`。hidden testbench 以名稱連接 `aclk`、`aresetn` 與 17 個 `s_axi_*` port。同類型的 T1 有完整 port 骨架，並寫明「Reset is synchronous, active-low」。

模型只能從 baseline elaboration 錯誤推測 port 名稱，位寬沒有任何線索。

## 對既有樣本的影響（唯讀統計）

統計對象為 `output/QUALITY_MODEL_VALIDATION/*/cycle-*/samples/*/T8/V*/sample-result.json`。

| 項目 | 數量 |
|---|---:|
| T8 樣本記錄 | 115 |
| 已執行（FAIL） | 42 |
| 未執行（NOT_TESTED） | 73 |
| PASS | **0** |
| 有 validator 執行記錄的 T8 workspace | 37 |
| 最後一次嘗試仍有 port 錯誤（如 `VRFC 10-3180 cannot find port 's_axi_rready'`） | **37／37** |
| 其中只跑過 baseline | 35 |
| 其中多次嘗試仍未對上 port | 2 |
| 任何 T8 XSim 出現 `QUALITY_T8_PASS` | **0** |

同期其他七題共有 40 個 PASS。T8 的 0 通過率反映的是猜測介面，而不是工程能力。

| Session | T8 樣本 |
|---|---|
| `20261022T202138` | V1 FAIL 3、V2 FAIL 2、V3 FAIL 2（早期試跑，原本即不計入正式比較） |
| `20261027T180437` | V1 FAIL 4、NOT_TESTED 5 |
| `20261028T104940` | V1 FAIL 9（V1 Pilot） |
| `20261103T145322`、`20261103T154254`、`20261103T160424` | 各 V2／V3 NOT_TESTED 18 |
| `20261103T163856` | V2 FAIL 4、NOT_TESTED 14 |
| `20261105T132707` | V2 FAIL 9、V3 FAIL 9 |

## 重新分類

依 `QUALITY_VALIDATION_PLAN.md` 第 3 節（題目缺陷時，受影響的共同變體對九款模型全數標為 `HARNESS_INVALID`，修好並凍結新版本後共同重跑）：

- 上述所有 corpus v1 的 T8 樣本**在分析與報告中一律視為 `HARNESS_INVALID`**，不計入任何模型的通過率、失敗率或排名。
- **原始證據不修改**：`output/` 中的 `sample-result.json`、trace 與 log 維持原樣，仍記錄當時判定的 `FAIL`／`NOT_TESTED`。重新分類以本文件為準；彙整工具與報告需排除 corpus v1 的 T8。
- T1–T7 的既有樣本不受本缺陷影響。

## 修正

新增 `docs/LOCAL_MODEL_LAB/quality-corpus/v2`：

- T1–T7 與 v1 逐 byte 相同。
- T8 的 hidden testbench、reference 與 starter（仍為 `module axi_regs;`）不變；三個變體的 `TASK_SPEC.md` 新增「Interface」小節，列出與 T1 骨架相同的完整 port 清單（`build_quality_corpus.PORTS`），並寫明 `aclk` 為 clock、`aresetn` 為同步低態有效 reset。
- v1 原封保留，作為既有樣本的對照記錄。
- `prepare_quality_workspace.py`、`quality_task_executor.py`、`validate_quality_corpus.py`、`run_quality_pilot.py`、`freeze_quality_v2_v3_plan.py` 改用 v2。
- `scripts/test_build_quality_corpus.py` 鎖定 v1→v2 只差 T8 規格與 manifest，並檢查 T8 規格列出 hidden testbench 連接的每一個 port。

新版本以實際 Vivado／Vitis 執行 `validate_quality_corpus.py --task all` 驗證；結果見 `QUALITY_VALIDATION_PLAN.md` 第 13 節。九款模型須以 v2 共同重跑 T8。
