# AI370-2 T7 Deployment / Migration Kit

**Media role:** deployment and migration resources for rebuilding AI370-2 on this or another compatible workstation. T7 is not a current-machine image or a full-system tar target. Do not copy `/home/shen/tools/Xilinx/2026.1` to T7 for the purpose of M15 closure.

**Status:** T7 is mounted at `/media/shen/T7` as exFAT with 43.3 GB available at inspection. Inventory below is a partial observation (initial filesystem/path inspection was read-only); the full deployment kit and clean rebuild have not been validated. `PRESENT` means a path was observed, not that its payload is complete or usable. Only the Vivado/Vitis installer row has a full-file SHA256 comparison in this session.

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

`SHA256SUMS` should be generated in the deployment-kit directory for the selected payloads and repository bundle. Keep paths relative to a stable T7 directory, use `sha256sum -c` to verify, and record manifest generation date and commit. Do not put credentials or license keys in it.

## Observed T7 resources (2026-10-02)

The media is mounted, but resource closure is not complete. The statuses below are inventory facts only.

| Resource | Requirement | Observed path / identity | Exact size | SHA256 / verification | Purpose / notes |
|---|---|---|---:|---|---|
| Ubuntu installer | REQUIRED | `Agent_Tools_Docs/01_OS/Ubuntu/ubuntu-24.04.1-desktop-amd64.iso` | 6,203,355,136 | Full SHA256 `c2e6f4dc37ac944e2ed507f87c6188dd4d3179bf4a3f9e110d3c88d1f3294bdc` recomputed and matched the existing T7 checksum list. **Not the exact 24.04.4 install image.** | Base install media observed. Suitability for a reproducible 24.04.4 deployment remains to be decided/verified; no new download was made. |
| AMD/Xilinx Vivado/Vitis unified installer | REQUIRED | `Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700.tar` | 105,522,216,960 | SHA256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`; full T7 and system-file hashes matched; system copy is byte-identical. | Rebuild installer. The system duplicate may be considered safe to delete, but **no deletion is authorized or performed**. Preserve the installed toolchain at `/home/shen/tools/Xilinx/2026.1`. |
| Existing expanded Vivado/Vitis installer tree | OPTIONAL | `Agent_Tools_Docs/02_FPGA/Vivado_Vitis_2026.1/FPGAs_AdaptiveSoCs_Unified_SDI_2026.1_0616_1700/` | Not measured as a tree | NOT VERIFIED | Present alongside the archive; not equivalent to the installed `/home/shen/tools/Xilinx/2026.1` tree and not yet assessed as a clean installer source. |
| Ryzen AI 1.7.1 package archive | CONDITIONAL — M5/NPU rebuild | `Agent_Tools_Docs/03_RyzenAI/RyzenAI_1.7.1/ryzen_ai-1.7.1.tgz` | 10,954,641,946 | Existing T7 checksum-list entry exists; not recomputed in this session. | Package source observed. Installability and exact closure against the protected host stack are NOT TESTED. |
| XRT/XDNA NPU 2.21 resources | CONDITIONAL — M5/NPU rebuild | `Agent_Tools_Docs/03_RyzenAI/XRT_NPU/` including XRT 2.21.75 base/base-dev/NPU packages and `xrt_plugin.2.21.260102.53.release_24.04-amd64-amdxdna.deb` | Files individually present; the plugin `.deb` is 6,799,692 bytes | NOT RECOMPUTED in this session | Intended version family matches the recorded M5 golden stack; package installation/rebuild not tested here. |
| Alternate XRT 2.25 / amdxdna 7.0-rc packages | EXCLUDED | `Agent_Tools_Docs/06_AI370_2_Downloads/LocalAI/Lemonade-Ubuntu24.04/debs/` | Present | NOT VERIFIED | **Do not use for the AI370-2 Golden stack** without a new explicit compatibility gate; these files differ from protected XRT 2.21.75 / amdxdna 2.21 release. |
| ROCm 7.2.1 package resources | REQUIRED — GPU rebuild | `Agent_Tools_Docs/06_AI370_2_Downloads/AMD/ROCm-7.2.1/` | Directory present; total not measured | NOT VERIFIED | Package files observed. Complete package-set checksum, dependency closure and clean install replay are not tested. |
| AI370-2 project snapshot | REQUIRED | `Agent_Tools_Docs/AI370-2_Workstation_20261001/`, branch `main`, HEAD `db83562` | Directory tree not measured | NOT CURRENT: working tree has modifications; does not represent current local HEAD | Do not treat this snapshot as the deployment repository. A current commit-addressed repository bundle is still to be placed and verified. |
| Ross MCP / Skills / Local Knowledge Base | CONDITIONAL — M13 rebuild | No dedicated portable release/KB bundle confirmed in the targeted inventory | UNKNOWN | UNKNOWN | Current workstation readiness is recorded in M13/M15; T7 presence and reproducibility are NOT VERIFIED. Never assume the installed local database is included in Git. |
| Local GGUF models | OPTIONAL | `Agent_Tools_Docs/04_Local_AI/GGUF/`; Qwen3.6 Q8 and IQ2 plus other files observed | Per-file values are in existing T7 directory; not re-inventoried here | Existing checksum list covers some, not all; no blanket verification | Select only desired models for migration; models are not needed to rebuild the base workstation. No model inference was run for this inventory. |
| Xilinx license / credentials | NEVER INCLUDE | No path recorded | — | — | Keep license files, keys, passwords and tokens out of Git and deployment manifests. Re-provision secrets separately through the authorized license process. |

## Deployment-kit acceptance

The kit is ready only when its selected resource list is closed, every REQUIRED payload has a version/path/byte-size and verified SHA256 (or a documented trusted package source), the repository bundle points to a named AI370-2 commit and passes `git bundle verify`/clone checks, and `SHA256SUMS` passes on T7. A clean rebuild/migration smoke is separate evidence; inventory alone is not a rebuild PASS.

When updating T7, use a new `AI370-2_Deployment/` directory and preserve the existing `Agent_Tools_Docs` tree. Do not overwrite the old project snapshot, delete the system installer, alter the installed Xilinx toolchain, or include current-machine root images. Record only observed assets; unresolved entries remain `UNKNOWN` or `NOT VERIFIED`.

## Next actions once media is available

1. Reconfirm mount, filesystem health/status, free space and exact paths; retain the existing T7 data.
2. Place a bundle for the committed current `main` branch in a new deployment directory; verify it and test cloning to a temporary location.
3. Generate a T7-local `SHA256SUMS` for that bundle and chosen installer/runtime payloads. The Vivado/Vitis installer is already verified byte-identical to the system copy.
4. Resolve the OS media gap (the observed ISO is Ubuntu 24.04.1; AI370-2's installed host is 24.04.4) without asserting official AMD/Xilinx support.
5. Confirm required AMD/XDNA2, ROCm, Ross/Skills/KB and selected model resources; explicitly exclude incompatible alternate XRT/DKMS packages from the Golden rebuild set.
6. Do not delete the system installer unless the user separately directs it. A duplicate-safe-to-delete recommendation is supported by the exact matching size and SHA256, but deletion has not occurred.
