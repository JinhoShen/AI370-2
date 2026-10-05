# T7 snapshot inventory: `AI370-2_Workstation_20261001`

Inventory date: 2026-10-05. This is a read-only classification of the existing T7 snapshot. **Nothing in the snapshot or any model was deleted, moved, rewritten, or re-extracted.** The T7 photo directory named `照片` was excluded from the inventory and remains untouched.

Snapshot path: `/media/shen/T7/Agent_Tools_Docs/AI370-2_Workstation_20261001/`
Filesystem: exFAT. `du` reports about 133 GiB (142,223,212,544 bytes of the measured `.venvs` + `output` alone; rounded top-level report was 133 GiB). The previous rounded breakdown was `.venvs` about 72 GiB and `output` about 62 GiB.

## Classification summary

Classification describes usefulness as **deployment/migration media**, not historical value. Evidence and rebuildable data remain intact. A component is not called a duplicate unless byte identity or a clearly superseding source is established.

| Primary classification | Inventory rows | Measured size | Interpretation |
|---|---:|---:|---|
| KEEP | 0 | 0 | No item in this machine snapshot is required as a deployed installed-system image. |
| REBUILDABLE | 2 | 78,685,536,256 bytes (about 73.3 GiB) | Python environment and llama.cpp source/build trees. Large and generally reproducible; exact offline closure is not established. |
| EVIDENCE | 6 | 63,569,788,928 bytes (about 59.2 GiB) | Recovery archives and historical logs/reports. Preserve as historical evidence; this is not a current-state image. |
| DUPLICATE | 0 | 0 | No large item was proven byte-identical to a newer source in this inventory. |
| UNKNOWN | 1 | 88,211,456 bytes (about 84 MiB for `.git` + `scripts` + `verify`; root metadata is additional and small) | Stale Git worktree and code/evidence whose copied state is modified and whose exFAT semantics prevent treating it as a clean clone. See exact subpaths below. |

The UNKNOWN byte total is approximate because the snapshot's copied working tree contains many modified paths and special-file semantics changed during exFAT sync. Exact top-level measured values are listed below; do not use this estimate as a deletion plan.

## Path-by-path inventory

| Path (relative to snapshot) | Size | Purpose / observed source | GitHub availability | Reproducible? | Version-sensitive? | Needed offline? | Class / recommendation |
|---|---:|---|---|---|---|---|---|
| `.venvs/npu21/` | 76,547,751,936 bytes (about 76.5 GB / 71.3 GiB; `du -h` rounds to 72 GiB) | Python virtual environment for Ryzen AI/NPU experiments; copied as part of the 2026-10-01 workspace sync. Its `lib` and `lib64` each account for about 36 GiB in `du`; exFAT copied symlinks as referent files where available. | No full venv payload in GitHub; setup evidence, requirements/freeze and local wheel references exist in M5 evidence. | Generally yes from SDK wheels and package sources, but an exact isolated offline rebuild of all dependencies was not demonstrated. | Yes: Python, NumPy, Torch and Ryzen AI wheel versions matter. | Optional convenience only; not required if wheels/index are available. | **REBUILDABLE.** Do not copy this 72 GiB environment as the new-machine install method. Preserve until a separate cleanup decision. |
| `output/recovery/CP0-20261001T024200Z/root.tar` and its companion files | root.tar 53,255,905,280 bytes; directory approximately 49.6 GiB plus EFI and metadata | CP0 historical pre-Vivado/Vitis recovery archive. SHA manifest passed and selected-file isolated restore passed in existing records; full boot restore was NOT TESTED. | The archive is not in public GitHub; small reports/verification metadata are in GitHub. | Not a deployment rebuild; only selected-file restore was verified. | Captures the 2026-10-01 pre-Xilinx state. | Historical recovery only. | **EVIDENCE.** Retain as historical CP0; never describe it as a current-state backup. |
| `output/recovery/CP0-20260930T084329Z/` | root.tar 9,606,400,000 bytes plus EFI and metadata | Earlier CP0 recovery snapshot. | Not in GitHub as a full archive. | Full restore not demonstrated. | Yes; older pre-install state. | Historical only. | **EVIDENCE.** Retain; do not assume duplicate of later CP0. |
| `output/recovery/CP0-20261001T023920Z/` | approximately 1.2 MiB | Partial/early CP0 capture; status says incomplete. | Metadata may overlap repository evidence. | No; incomplete capture. | Yes. | No for rebuild. | **EVIDENCE.** Keep its failure/incomplete record with history. |
| `output/recovery/CP5-NPU-GATE-20260930T095450Z/` | approximately 151 MiB | NPU recovery checkpoint evidence including platform archive, package/module lists and firmware digest. | Metadata is partly in GitHub; binary archive is not. | Recovery artifact, not a new-machine installer. | Yes, tightly bound to M5 stack. | Offline recovery convenience. | **EVIDENCE.** Keep; do not use as a substitute for the current exact M5 installation resources. |
| `output/M2/`, `M3/`, `M4/`, `M5/`, `M7/`, `M8/`, `diagnostics/`, `precheck/` | combined 440,401,920 bytes | Raw build outputs, package/detection logs, M5 workload results, GPU/Vulkan diagnostics and historical prechecks. | Result summaries and selected evidence are in GitHub; not every raw output is tracked. | Many checks are reproducible; exact historical logs are not. | Mixed; especially M5 driver, firmware, ROCm and Vulkan diagnostics. | Useful for offline diagnosis, not a baseline rebuild requirement. | **EVIDENCE.** Preserve relevant raw failures and successful measurements; do not present as a full deployed environment. |
| `output/M6/source/`, `build-cpu/`, `build-vulkan/`, `build-hip/` | total `output/M6/` 2,137,784,320 bytes (source about 629 MiB; builds about 1.4 GiB) | llama.cpp source/build trees for CPU, Vulkan and HIP backend work. | Build procedure and result records are in GitHub; source revision may be fetched from upstream if network is available. | Yes, by pinned source revision and build options; exact clean rebuild on a new host has not been established by retaining these build directories. | Yes; source commit, compiler, Vulkan/ROCm and CMake options. | Optional if source/network unavailable; the built tree is not a supported offline installer. | **REBUILDABLE.** New machines should rebuild from recorded source/configuration, not copy caches/build products. |
| `docs/` and `baseline/` | 31,981,568 + 262,144 bytes | CP0, M0-M9-era records, resource/download logs and baselines. | Many documents are superseded by current repository documents; some raw files are not tracked. | The prose is not a system image; exact historical observations cannot be regenerated. | Yes, historical timestamps/config. | Useful for historical investigation. | **EVIDENCE.** Retain; current committed docs remain the source of truth for present project status. |
| `.git/`, `scripts/`, `verify/`, root files | `.git` 83,886,080; scripts 2,752,512; verify 1,572,864; root files small | Workspace clone captured at commit `db83562fbb4098d9ae0b894f8825641b1bd6e408`, with a dirty copied working tree (150 tracked paths reported modified, plus untracked sync status). | Current repository is on GitHub; current local HEAD at inventory time is `8bc94d36881d8abd56e6e104c11d99d206c2c285`. | A clean clone is reproducible from GitHub or a current bundle. This copied worktree is not clean. | Yes; older code/docs and copy-time state. | No, if GitHub/T7 bundle is usable; useful only as historical fallback. | **UNKNOWN.** Do not use as a deployment source or delete before comparing unique dirty changes. exFAT sync converted available symlinks to referents and retained broken M6 symlinks as unavailable. |

### T7 capacity context (Photos excluded)

On 2026-10-05, `/media/shen/T7` was mounted exFAT with 931.5 GiB capacity, 215.2 GiB available, and 77% used. `Agent_Tools_Docs` measured 324 GiB and `AI370-2_Deployment` 48 MiB. The 324 GiB resource tree included approximately: `01_OS` 5.8 GiB; `02_FPGA` 99 GiB; `03_RyzenAI` 21 GiB; `04_Local_AI` 57 GiB; `06_AI370_2_Downloads` 9.3 GiB; and this workstation snapshot 133 GiB. Other T7 top-level usage was not exhaustively scanned. **The `照片` directory and its contents were excluded and untouched.** These figures are filesystem inventory, not an authorization to remove anything.

The Xilinx 2026.1 expanded installer tree had already been removed in an earlier authorized action; the original 105,522,216,960-byte TAR remains. This inventory did not re-extract it or touch `/home/shen/tools/Xilinx/2026.1`.

## What could eventually be left out of a deployment kit

This is a recommendation only; this turn performed no deletion. If the snapshot is confirmed to be unnecessary after preserving the historical records the user wants, the largest non-deployment payloads are:

| Candidate for exclusion from future Deployment Kit | Potential space | Condition |
|---|---:|---|
| `.venvs/npu21` | about 71.3 GiB | Rebuild from pinned wheels/requirements; offline dependency closure must be separately confirmed if offline rebuild is required. |
| llama.cpp M6 builds/source | about 1.99 GiB | Preserve build recipe/source commit in Git or fetch it; keep only if offline source/build is a requirement. |
| Older CP0 archive | 9,606,400,000 bytes | Preserve if historical recovery evidence is wanted; it is not required to build a fresh machine. |
| Newer CP0 archive | 53,255,905,280 bytes | Preserve as the requested pre-Vivado historical evidence; do not put it in a deployment kit for a clean rebuild. |
| CP5/archive and raw milestone outputs | about 0.6 GiB outside CP0s, depending on exact subdirectory grouping | Keep evidence wanted for audit; not required for a clean rebuild. |
| Stale `.git` clone and copied scripts | about 86 MiB | Only after comparing the dirty worktree against GitHub/history and preserving any unique evidence. |

Theoretical excludable volume from a future *deployment kit* is about 132 GiB if the two old CP0 archives and rebuildable environment/builds are not included. That figure is **not a deletion plan** and excludes other output/evidence. Preserve CP0 history and every item until the user authorizes cleanup.

## Local AI model inventory

Model root: `/home/shen/AI370-2/resources/Agent_Tools_Docs/04_Local_AI/`. This scan covered both `GGUF/` and `Lemonade/Qwen_Cache/`. T7 has a separate model copy under `Agent_Tools_Docs/04_Local_AI/`; this table describes system-source resources and should not be interpreted as a fresh T7 checksum audit. Metadata/SHA/test values below come from committed M7/M15 evidence where available; missing values are explicitly UNKNOWN. No inference was run for this inventory.

| Model / asset | Format, quantization, metadata | Size / SHA256 | Location | CPU / Vulkan / ROCm evidence | Migration role |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B Q8_0 | GGUF v3; `qwen35moe`; 34.66B parameter elements; 733 tensors; MOSTLY_Q8_0 | 36,903,139,328 bytes; `d8d7842cc657d720f39546878e431937c84473aa130c36371669ac17c80c7361` | `04_Local_AI/GGUF/` | CPU bounded smoke PASS (M7); Vulkan device loss / command submission failure, M7.1 OPEN; ROCm inference NOT TESTED. | OPTIONAL, high-priority known-issue reproducer only under explicit safety policy. |
| Qwen3.6-35B-A3B Uncensored IQ2_M | GGUF; `qwen35moe`; 34.66B parameter elements; 733 tensors; MOSTLY_IQ2_M | 11,659,235,456 bytes; `ba3a1d47a604f17ef74d913f9a9d9a2b456acc6925e7b168bfa2e6527246011c` | `04_Local_AI/GGUF/` | CPU, Vulkan and ROCm bounded M15 smoke PASS (context 32, max 4 tokens, one GPU layer). Not a benchmark/stability claim. | OPTIONAL selected bounded regression model. |
| Qwen3.8-27B UD Q4_K_M | GGUF; metadata architecture `qwen35`; 27.32B parameter elements; 866 tensors; Q4_K Medium | 16,464,440,224 bytes; `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482` | `04_Local_AI/GGUF/` | CPU bounded smoke PASS; Vulkan and ROCm one-layer bounded smoke PASS (M7 2026-10-02). | OPTIONAL selected Local AI evaluation. |
| Qwen3.8-27B UD Q4_K_XL | GGUF; `qwen35`; 27.32B parameter elements; 866 tensors; runtime reported Q4_K Medium | 17,559,178,144 bytes; `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e` | `04_Local_AI/GGUF/` | CPU, Vulkan and ROCm bounded one-layer smoke PASS (M7). | OPTIONAL candidate; compare only within bounded policy. |
| Qwen3.8-27B Uncensored Q4_K_M | GGUF; `qwen35`; 27.32B parameter elements; 866 tensors; Q4_K Medium | 16,810,714,528 bytes; `4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675` | `04_Local_AI/GGUF/` | CPU, Vulkan and ROCm bounded one-layer smoke PASS (M7). | OPTIONAL candidate. |
| Gemma 4 31B Q4_K_M | GGUF; `gemma4`; 30.70B parameter elements; 833 tensors; MOSTLY_Q4_K_M | 18,687,057,344 bytes; `b1fc8ee10f916da019dbf4c9a9d9a2b456acc6925e7b168bfa2e6527246011c` | `04_Local_AI/GGUF/` | CPU, Vulkan and ROCm bounded one-layer smoke PASS (M7). | OPTIONAL candidate. |
| Qwen3-14B Q4_0 | GGUF; `qwen3`; 14.77B parameter elements; Q4_0 | Archive member 8,543,001,984 bytes; model SHA `009f54ffc8d8082e7921139924229d4deea61c9174a0a357d91384bd299ff78e`; containing TAR SHA `512bc60d9b8c753494c19a62105c03c4a6dc7d7c5318e358f4302cb8811f58e1` | `04_Local_AI/Lemonade/Qwen_Cache/SER9-Qwen-Models.tar` | CPU and bounded one-layer Vulkan/ROCm smoke PASS (M7). Archive member remains in archive; no duplicate extracted model required. | OPTIONAL selected general Local AI workload. |
| Qwen3.5-9B UD Q4_K_XL | GGUF; `qwen35`; 8.95B parameter elements; runtime reported Q4_K Medium | 5,966,095,584 bytes per copy; selected copy SHA `6f5d30666c2d8ae16a306e616d95341dcf3cc46810df84d7e6f5a7d1e4c1b293`; TAR SHA above | Six same-revision cache directories plus TAR member under `Lemonade/Qwen_Cache/` | CPU, Vulkan and ROCm bounded smoke PASS on selected copy (M7); other copies not individually hashed/tested. | OPTIONAL. Prefer one verified copy; other copies are candidate duplicates, byte identity not checked. |
| Qwen3-4B Q4_0 | GGUF; name/architecture inferred from cache repository and filename; parameter metadata/hash not captured in current committed model report | 2,375,773,472 bytes per copy; SHA UNKNOWN | Six Lemonade cache directories | CPU/Vulkan/ROCm inference NOT TESTED in cited M7/M15 result. | OPTIONAL small-model candidate; metadata/hash/testing UNKNOWN. |
| Qwen3-0.6B Q4_0 | GGUF; name/architecture inferred from cache repository and filename; parameter metadata/hash not captured | 382,156,480 bytes per copy; SHA UNKNOWN | Six Lemonade cache directories | CPU/Vulkan/ROCm inference NOT TESTED in cited M7/M15 result. | OPTIONAL small-model candidate; metadata/hash/testing UNKNOWN. |
| Qwen3.5-9B mmproj F16 (Lemonade cache) | GGUF projector companion, not a standalone text model | 918,166,080 bytes per copy; SHA UNKNOWN | Six Lemonade cache directories and TAR member | Multimodal inference NOT TESTED. | OPTIONAL only if the matching multimodal workflow is required. |
| Qwen3.6-35B-A3B mmproj F16 | GGUF projector companion, 334 tensors / about 446.6M parameter elements per M15 metadata | 899,283,072 bytes; `c8e702344a81f8c226a914aa980ed6e1f604bce9374f1fed8e65c896908af414` | `04_Local_AI/GGUF/` | Multimodal inference NOT TESTED. | OPTIONAL paired asset; only useful with matching model/workflow. |

Lemonade cache contains six directories with the same visible Hugging Face snapshot revision for Qwen3-0.6B, Qwen3-4B and Qwen3.5-9B. Sizes and snapshot IDs match; a full cross-copy hash comparison was not performed, so they are **candidate duplicates, not verified byte-identical duplicates**. The Qwen3-14B model is inside the archive and need not be extracted or copied to T7 separately. Keep selected models only in the eventual deployment kit; none is required to rebuild the base GPU/NPU/FPGA workstation.

### Actual T7 Local AI payload check

Read-only inventory of `/media/shen/T7/Agent_Tools_Docs/04_Local_AI/` found about 57 GiB allocated. File-level results:

| T7 file | Exact observed size | Comparison / status |
|---|---:|---|
| `GGUF/Qwen3.6-35B-A3B-Q8_0.gguf` | 11,316,823,689 bytes | **INCOMPLETE / STALE COPY.** Expected system source is 36,903,139,328 bytes with known SHA256 above. The retained T7 sync status explicitly says the source was still downloading during copy and the T7 copy was not hash-verified. Do not use as a model or count it as available offline. |
| `GGUF/gemma-4-31b-jang-crack-Q3_K_M.gguf` | 0 bytes | **EMPTY / INVALID MODEL FILE.** Preserve untouched; not usable as an offline model. |
| `GGUF/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ2_M.gguf` | 11,659,235,456 bytes | Size matches system source; T7 copy SHA not rechecked in this inventory. |
| `GGUF/gemma-4-31b-jang-crack-Q4_K_M.gguf` | 18,687,057,344 bytes | Size matches system source; T7 copy SHA not rechecked in this inventory. |
| `GGUF/mmproj-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf` | 899,283,072 bytes | Size matches system source; T7 copy SHA not rechecked in this inventory. Companion only, not a standalone model. |
| `Lemonade/Qwen_Cache/SER9-Qwen-Models.tar` | 18,185,226,240 bytes | Size matches the local archive; local sidecar records SHA256 `512bc60d9b8c753494c19a62105c03c4a6dc7d7c5318e358f4302cb8811f58e1`. T7 copy digest was not recomputed. Contains Qwen3-14B and Qwen3.5-9B repositories plus projector. |

The three Qwen3.8 files inventoried on the system are not present as standalone GGUF files on this T7 copy. Therefore the current T7 Local AI folder is not a complete mirror of the current model collection. This is a manifest/integrity gap, not a reason to copy or remove anything in this turn.

## Git bundle fallback

T7 contains `/media/shen/T7/AI370-2_Deployment/AI370-2-main-695437f.bundle`. On 2026-10-05, `git bundle verify` **PASS**; test clone HEAD was `695437f0185bffe4820f9652d9b46ffb874f2ec2`, main branch, with three Golden/toolchain tags. Current local main at inventory time is `8bc94d36881d8abd56e6e104c11d99d206c2c285`. Thus the bundle is a valid historical/offline fallback, but **does not contain current main**. GitHub `origin` is the primary source of truth; refresh the bundle in a future separately authorized T7 write step and reverify `bundle verify`, clone HEAD and tags. No bundle was created or changed during this inventory.
