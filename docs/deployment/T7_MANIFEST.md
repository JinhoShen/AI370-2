# AI370-2 T7 Deployment / Migration Kit

**Media role:** deployment and migration resources for rebuilding AI370-2 on this or another compatible workstation. T7 is not a current-machine image or a full-system tar target. Do not copy `/home/shen/tools/Xilinx/2026.1` to T7 for the purpose of M15 closure.

**Current status (2026-10-06):** T7 was synchronized, checksum-verified and then safely unmounted and powered off at the user's request. It is currently unavailable at `/media/shen/T7`; no fake mount point is in use. The last verified media snapshot is at repository commit `25125e77734e27bd6beacd9a2b8490cd2d658cd9`, with the bundle verified/cloned and all current changed/new manifest paths checked against SHA256; that snapshot is stale relative to subsequent repository documentation commits and must be refreshed after reconnection. The media root `/AMD_AI_Workstation/` contains `01_System_Resources`, `02_Deployment`, and `03_AI_Models`. This is a deployment-media integrity check, not a clean-machine rebuild. Resource closure remains PARTIAL: exact Ubuntu 24.04.4 media, complete protected-stack dependency closure, and clean rebuild remain unverified. The `照片` directory was not accessed. See [the dated M15 evidence](../M15/evidence/2026-10-06/t7-latest-sync/RESULT.md) and the T7 root `MASTER_MANIFEST.md` for the last on-media snapshot identity.

**Historical note:** Sections below retain the dated 2026-10-02 and 2026-10-05 observations. Statements that the media was detached, the final root was unverified, or the bundle was stale describe those earlier snapshots only and are superseded by the 2026-10-06 update below. Historical evidence and prior status transitions are not rewritten.

The rebuild process is documented in [AI370-2_REBUILD_GUIDE.md](AI370-2_REBUILD_GUIDE.md). The full read-only snapshot classification and model inventory is in [AI370-2_WORKSTATION_SNAPSHOT_INVENTORY.md](AI370-2_WORKSTATION_SNAPSHOT_INVENTORY.md). Neither document authorizes deletion or movement of media contents.

## Manifest schema

Maintain one row per resource with:

| Field | Meaning |
|---|---|
| Requirement | `REQUIRED` for the selected clean-rebuild scope, `OPTIONAL` for convenience/selected workloads, or `CONDITIONAL` for a milestone-specific capability. |
| Media path | Exact path relative to the T7 root; use `UNKNOWN` until observed. |
| Version / identity | File-reported or package filename identity; distinguish this from host verification. |
| Exact size | Byte size from `stat`; do not infer from rounded UI values. |
| SHA256 | Full digest and source; `NOT VERIFIED` until recomputed or compared against a trusted digest. |
| Purpose | What rebuild or workflow depends on it. |
| Verification status | `VERIFIED` only for an actual integrity/rebuild check; otherwise use `PRESENT`, `USER-REPORTED`, `UNKNOWN`, `NOT TESTED`, or `EXCLUDED`. |
| Notes | Compatibility gates, license handling, prerequisites and evidence link. |

`SHA256SUMS` is generated in the deployment-kit directory for selected payloads and the repository bundle, with paths relative to the T7 root. Do not put credentials or license keys in it.

## Observed T7 resources (2026-10-02)

The media is mounted and the current AI370-2 Git bundle has been written and clone-verified. Resource closure is still partial. The statuses below are inventory facts only.

| Resource | Requirement | Observed path / identity | Exact size | SHA256 / verification | Purpose / notes |
|---|---|---|---:|---|---|
| AI-370-2 repository bundle (historical offline fallback; stale) | REQUIRED for offline fallback, NOT CURRENT | `AI370-2_Deployment/AI370-2-main-695437f.bundle`, main HEAD `695437f0185bffe4820f9652d9b46ffb874f2ec2` | 12,199,152 | SHA256 `5938b775a7f1495d16a3ecf2a018751b0be60af1cf732e05ec4820f799866496`; on 2026-10-05 `git bundle verify` PASS and test clone HEAD confirmed. | Clone contains `main` plus three historical Golden/toolchain tags. At the last manifest refresh, local `main` was `8bc94d36881d8abd56e6e104c11d99d206c2c285`; local `main` has since advanced, so use `git rev-parse HEAD` for the current revision. The bundle is stale and cannot serve as a current-main fallback until refreshed on T7. GitHub remains primary. |
| Superseded staging bundles | HISTORICAL / DO NOT USE | `AI370-2_Deployment/AI370-2-main.bundle`, `AI370-2-main-7a51ff1.bundle`, `AI370-2-main-7a51ff1-clean.bundle` | 12,217,617; 12,196,671; 12,199,839 bytes | All hashes and refs are recorded in T7 `SHA256SUMS`. | Preserved as non-destructively superseded artifacts; use only `AI370-2-main-695437f.bundle` for the current deployment snapshot. The `--all` staging bundle contains an old origin tracking ref; it is not the selected bundle. |
| Deployment SHA256 manifest | REQUIRED | `AI370-2_Deployment/SHA256SUMS` | 12 entries | Current/superseded bundles, manifest/README and four XRT packages pass `sha256sum -c`; Ubuntu ISO and Vivado installer full hashes were independently recomputed in this session. | Covers all bundle files in the kit plus companion manifest/readme, Ubuntu ISO, Vivado/Vitis archive and four XRT/NPU 2.21 packages. It does not claim all T7 resources are integrity-verified. |
| Ubuntu installer | REQUIRED | `Agent_Tools_Docs/01_OS/Ubuntu/ubuntu-24.04.1-desktop-amd64.iso` | 6,203,355,136 | Full SHA256 `c2e6f4dc37ac944e2ed507f87c6188dd4d3179bf4a3f9e110d3c88d1f3294bdc` recomputed and matched the existing T7 checksum list. **Not the exact 24.04.4 install image.** | Base install media observed. Suitability for a reproducible 24.04.4 deployment remains to be decided/verified; no new download was made. |
| AMD/Xilinx Vivado/Vitis unified installer | REQUIRED | `Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar` | 105,522,216,960 | SHA256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`; full T7 and system-file hashes matched; system copy is byte-identical. | Rebuild installer. The system duplicate may be considered safe to delete, but **no deletion is authorized or performed**. Preserve the installed toolchain at `/home/shen/tools/Xilinx/2026.1`. |
| Existing expanded Vivado/Vitis installer tree | NOT PRESENT (removed earlier) | `Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700/` | — | Read-only `test -e` on 2026-10-05: absent | It is not needed on deployment media. Original TAR remains. The installed `/home/shen/tools/Xilinx/2026.1` tree was not touched. |
| Ryzen AI 1.7.1 package archive | CONDITIONAL — M5/NPU rebuild | `Agent_Tools_Docs/03_RyzenAI/RyzenAI_1.7.1/ryzen_ai-1.7.1.tgz` | 10,954,641,946 | Existing T7 checksum-list entry exists; not recomputed in this session. | Package source observed. Installability and exact closure against the protected host stack are NOT TESTED. |
| XRT/XDNA NPU 2.21 resources | CONDITIONAL — M5/NPU rebuild | `Agent_Tools_Docs/03_RyzenAI/XRT_NPU/` | base `.deb` 7,288,220 bytes; base-dev 4,234,376; NPU 1,453,830; plugin 6,799,692 | SHA256 computed: base `bd0e1b216cab193d572a5c006bf5a98df47c6b3a6c14fe392f2395e2b97023fa`; base-dev `f11f570f9fac26fb10d3f7a24798e933f1414be5563bf537ea9b918478d19ed9`; NPU `2c35e090958619317e6756888119dfa719ca69b2dc077ab7d9ae62939e7e326b`; plugin `802696333ef159bc0cbf9ba65f89acc5e3fb3023d461c3ad1307fe7a05436ccb`. | The XRT package family matches 2.21.75. Exact standalone amdxdna DKMS installer matching `2.21.260102.53.release` was not identified in the targeted file inventory; do not assume the plugin package alone supplies it. Package installation/rebuild not tested. |
| RyzenAI XRT/NPU archive | CONDITIONAL — M5/NPU rebuild | `Agent_Tools_Docs/03_RyzenAI/XRT_NPU/RAI_1.7.1_Linux_NPU_XRT.zip` | 18,797,282 | PRESENT; hash not verified in this session | Potential source for NPU runtime/driver components; archive contents and exact amdxdna package identity remain UNKNOWN. |
| Alternate XRT 2.25 / amdxdna 7.0-rc packages | EXCLUDED | `Agent_Tools_Docs/06_AI370_2_Downloads/LocalAI/Lemonade-Ubuntu24.04/debs/` | Present | NOT VERIFIED | **Do not use for the AI370-2 Golden stack** without a new explicit compatibility gate; these files differ from protected XRT 2.21.75 / amdxdna 2.21 release. |
| ROCm 7.2.1 package resources | REQUIRED — GPU rebuild | `Agent_Tools_Docs/06_AI370_2_Downloads/AMD/ROCm-7.2.1/` | Directory present; total not measured | NOT VERIFIED | Package files observed. Complete package-set checksum, dependency closure and clean install replay are not tested. |
| Earlier AI370-2 project snapshot | OPTIONAL / HISTORICAL | `Agent_Tools_Docs/AI370-2_Workstation_20261001/`, branch `main`, HEAD `db83562` | Directory tree not measured | NOT CURRENT: working tree has modifications; does not represent current local HEAD | Preserve as-is; do not treat it as the deployment repository or overwrite it. Use the commit-addressed bundle above. |
| Ross MCP / Skills / Local Knowledge Base | CONDITIONAL — M13 rebuild | No dedicated portable release/KB bundle confirmed in the targeted inventory | UNKNOWN | UNKNOWN | Current workstation readiness is recorded in M13/M15; T7 presence and reproducibility are NOT VERIFIED. Never assume the installed local database is included in Git. |
| Local GGUF models | OPTIONAL / selected | `Agent_Tools_Docs/04_Local_AI/` including `GGUF/` and `Lemonade/Qwen_Cache/` | About 57 GiB allocated; exact observed files and source comparisons in [snapshot/model inventory](AI370-2_WORKSTATION_SNAPSHOT_INVENTORY.md) | T7 Qwen3.6 Q8 is only 11,316,823,689 bytes versus 36,903,139,328-byte source and is explicitly stale/incomplete; one Gemma Q3 file is 0 bytes. Other T7 hashes were not rechecked. | Do not use the incomplete/empty files as offline model resources. Models are optional and not needed for base system rebuild. |
| Xilinx license / credentials | NEVER INCLUDE | No path recorded | — | — | Keep license files, keys, passwords and tokens out of Git and deployment manifests. Re-provision secrets separately through the authorized license process. |

## Deployment-kit acceptance

The kit is ready only when its selected resource list is closed, every REQUIRED payload has a version/path/byte-size and verified SHA256 (or a documented trusted package source), the repository bundle points to a named AI370-2 commit and passes `git bundle verify`/clone checks, and `SHA256SUMS` passes on the selected bundle, manifest, Ubuntu/Vivado installer and four listed XRT/NPU packages on T7. A clean rebuild/migration smoke is separate evidence; inventory alone is not a rebuild PASS.

Final target architecture (user decision; actual T7 paths are not verified while the media is detached): `/AMD_AI_Workstation/01_System_Resources/`, `/AMD_AI_Workstation/02_Deployment/AI370-2/`, and `/AMD_AI_Workstation/03_AI_Models/`. The `Agent_Tools_Docs/` and `AI370-2_Deployment/` paths above are historical source observations. After remount, compare hashes before reorganizing into the final root; preserve uncertain files and never access `/照片`. Do not delete the system installer, alter the installed Xilinx toolchain, or include current-machine root images. Record only observed assets; unresolved entries remain `UNKNOWN` or `NOT VERIFIED`.



## Historical media availability recheck (2026-10-05)

A later read-only check on 2026-10-05 found `/media/shen/T7` was not mounted (`findmnt -T /media/shen/T7` returned no mount). No T7 contents were accessed or changed in that recheck. This is a dated historical observation, superseded by the mounted check on 2026-10-06.

## 2026-10-05 inventory update

The original rows above retain their 2026-10-02 observations. This read-only refresh established:

| T7 path / category | Current observation | Deployment meaning |
|---|---|---|
| `Agent_Tools_Docs/` | about 324 GiB | Source resources and the old 133 GiB workstation snapshot coexist here. Detailed category sizes are in the linked inventory. |
| `Agent_Tools_Docs/01_OS/` | about 5.8 GiB | Ubuntu/OS installation resources; observed ISO is still 24.04.1, not 24.04.4. |
| `Agent_Tools_Docs/02_FPGA/` | about 99 GiB | Original 2026.1 Vivado/Vitis TAR retained; expanded installer directory is absent. No re-extraction was done. |
| `Agent_Tools_Docs/03_RyzenAI/` | about 21 GiB | Version-sensitive Ryzen AI/XRT/NPU payloads; exact offline closure and all checksums remain incomplete. |
| `Agent_Tools_Docs/04_Local_AI/` | about 57 GiB | Models/cache resources. See the model table in the linked inventory; models are OPTIONAL selected payloads. |
| `Agent_Tools_Docs/06_AI370_2_Downloads/` | about 9.3 GiB | ROCm and other downloaded resources; package closure/checksum verification remains incomplete. |
| `Agent_Tools_Docs/AI370-2_Workstation_20261001/` | about 133 GiB | Contains 76,547,751,936-byte `.venvs/npu21`, 65,675,460,608-byte `output` and historical docs/code. Classification is in the linked report. |
| `AI370-2_Deployment/` | about 48 MiB | Existing bundles/manifests, including valid but stale main bundle at `695437f`. |

The newest CP0 archive is historical pre-Vivado/Vitis recovery evidence: its `root.tar` is 53,255,905,280 bytes (49.6 GiB); prior SHA verification and selected-file restore PASS remain historical evidence. It is not current-state recovery; full boot restore remains NOT TESTED. No 350 GiB current-state image is required by the deployment/migration architecture.

### Required / optional planning

- **REQUIRED for a reproducible base rebuild:** a current AI370-2 repository revision (GitHub, or a current verified bundle when offline); compatible Ubuntu installation source and its verified digest; selected Vivado/Vitis original installer and digest if FPGA toolchain is in scope; verified, compatible AMD GPU/NPU package sources and firmware matching the chosen target; build/verification scripts and records.
- **OPTIONAL / selected:** Local AI models, Ross/Knowledge Base resources when their exact artifact set is selected, nonessential FPGA examples/platform archives and extra OS media.
- **Not part of the deployment recipe:** installed Xilinx tree, expanded installer, venvs, caches, generated build output and CP0 root image. CP0 remains historical evidence, not an image to apply to a new machine.
- **UNKNOWN / incomplete:** exact complete AMD Ryzen AI offline installer closure, standalone matching amdxdna DKMS source/package, complete ROCm package/dependency closure, portable Ross Local KB snapshot and selected skills, and whether the older `.venvs` copy can be reconstructed fully offline.

At the 2026-10-05 inventory checkpoint, the manifest was not READY: the bundle was stale, exact-point Ubuntu media differed, a legacy Qwen3.6 Q8 copy was incomplete and a model stub was empty, resource closure was incomplete, and clean migration had not been exercised. The 2026-10-06 mounted-media verification below supersedes the then-stale bundle and selected-payload hash status; the kit remains PARTIAL for the explicitly listed offline-closure and rebuild gaps.

## Historical next actions before the 2026-10-06 remount

Those actions were pending at the earlier inventory date. On 2026-10-06 the mount and formal root were rechecked, a current bundle was created and clone-tested, and all 100 then-listed sums passed. Remaining work is limited to refreshing the media's README/manifest/checksum inventory, resolving or documenting resource gaps, and deciding whether a clean-media rebuild is part of M15 acceptance. No deletion of the system installer is authorized or needed for this update.

## 2026-10-06 mounted-media result

| Item | Actual / verified result |
|---|---|
| Mount | `/dev/sda1` at `/media/shen/T7`, exFAT, read/write. Capacity 1,000,169,668,608 B; free 180,201,848,832 B at inspection. |
| Final directory root | `/media/shen/T7/AMD_AI_Workstation/`; `01_System_Resources`, `02_Deployment`, and `03_AI_Models` all exist. |
| Category sizes before final manifest refresh | `du -sx -B1` allocated usage: system resources 126,175,674,368 B; deployment 36,700,160 B; models 111,583,559,680 B. Final logical-byte totals are in the T7 root manifest. |
| Existing payload checksums | Historical pre-refresh run: 100 entries passed. Commit `23acc2f` checkpoint: 1,019/1,019 passed. Latest full refreshed manifest at commit `8f6bf85`: 1,023/1,023 passed, including installer, resources, models, Guides and current bundle; exact final counts and size are in the T7 root manifest. |
| Git bundle | The commit-addressed `8f6bf85` bundle passed `git bundle verify`; an isolated clone's HEAD exactly matched source `main` and all three Golden/toolchain tags were present. The T7 root `MASTER_MANIFEST.md` identifies the latest bundle after subsequent documentation commits. |
| Models | All manifest-listed Qwen3.8 and retained historical model files passed integrity checks. Qwen3.8 is the current candidate family; Qwen3.6 remains RETIRED, and integrity of its truncated Q8 copy does not make it a usable deployment model. No model inference was run. |
| Data changes | No large installer or model was copied again. No file was deleted. The system Xilinx installation was not copied. The Photos directory was not accessed. |
| Kit verdict | `PARTIAL`. Ubuntu 24.04.1 is present, not exact 24.04.4; protected-stack offline dependency closure, portable Ross resources and clean-host rebuild remain unverified. |

This mounted-media result supersedes the dated detached/stale-bundle observations above without deleting or rewriting their history. Exact final file counts, logical bytes, refreshed bundle identity and SHA256 coverage are in the media root manifest and `SHA256SUMS`.

## Latest 2026-10-06 full-manifest pass

The current bundle was refreshed to repository commit `71f8248d4fa3d67bf703fc6d7d563fbb7b00bf20`, verified and cloned at the exact HEAD. Its full deployment-root `SHA256SUMS` check returned 1,027/1,027 `OK`. The current root manifest records 1,025 files, 237,874,361,103 logical bytes and 179,988,856,832 bytes free. The T7 kit remains `PARTIAL`; integrity does not substitute for missing exact-point OS/dependency resources or a clean-host rebuild.


## 2026-10-06 complete T7 verification

The updated bundle and all 974 committed Guides files correspond to main at `71f8248`; the bundle clone matched exact HEAD and contained three historical tags. The complete T7 checksum manifest passed 1,027/1,027. T7 readiness remains PARTIAL because offline dependency closure and clean-host rebuild remain unverified. See [M15 full verification evidence](../M15/evidence/2026-10-06/t7-full-verification/).

## 2026-10-06 latest media sync and safe removal

The final on-media snapshot was refreshed to `25125e77734e27bd6beacd9a2b8490cd2d658cd9`. Its bundle verified and an isolated clone matched `main`; all 978 changed/new checksum entries (977 committed Guides files plus the bundle) passed, and the remaining 53 unchanged entries were covered by the preceding complete 1,027-entry pass. The media was then synced, `/dev/sda1` was unmounted and the T7 device powered off successfully. It is not currently connected. Since this repository gained documentation/evidence after that snapshot, refresh the bundle, manifest and sums after T7 is connected again. The device remains PARTIAL pending offline dependency closure and a clean-host rebuild.
