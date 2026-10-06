# T7 Deployment Media Revalidation

**Date:** 2026-10-06 (Asia/Taipei)  
**Scope:** T7 deployment-media inventory, existing SHA256 manifest validation, and offline Git bundle clone. No system packages, protected GPU/NPU stack, FPGA hardware, or models were modified or executed. The `/media/shen/T7/照片` directory was not accessed.

## Actual mount and layout

- Mount: `/media/shen/T7`, source `/dev/sda1`, exFAT, read/write.
- Capacity: 1,000,169,668,608 bytes; used 819,967,819,776 bytes; free 180,201,848,832 bytes (about 167.8 GiB).
- Formal root: `/media/shen/T7/AMD_AI_Workstation/` with `01_System_Resources/`, `02_Deployment/`, and `03_AI_Models/`.
- At inspection, category logical sizes were 126,175,674,368 bytes (system resources), 36,700,160 bytes (deployment), and 111,583,559,680 bytes (models). The kit included 237,780,362,941 logical file bytes before the refreshed README/manifest/sums are written.

## Integrity and bundle verification

- Ran `sha256sum -c SHA256SUMS` from the deployment root. All 100 entries present in that pre-refresh manifest returned `OK`, including the 2026.1 Vivado/Vitis installer, Ubuntu ISO, selected ROCm and Ryzen AI/XRT/XDNA resources, model files, model manifest, guide snapshot, and the prior historical Git bundle.
- Created bundle `02_Deployment/AI370-2/Git/AI370-2-main-1328371.bundle`, 13,382,800 bytes, SHA256 `809f5d1c17b6eb381db60d1100c401f618690f45226057c00b4cf5f692dff665`.
- `git bundle verify` passed. A temporary clone's `HEAD` exactly matched `1328371464ad4c73c54412d027a13e72984c0a70`; the bundle includes `main` and the three recorded Golden/toolchain tags.
- The older `AI370-2-main-f3fce03.bundle` remains untouched as a historical artifact. A newer documentation commit may supersede the bundle above; the final commit-addressed bundle identity is recorded in the T7 root `MASTER_MANIFEST.md` after refresh.

## Status and limitations

Integrity of the listed files is VERIFIED. This does not establish a full offline install closure or a clean rebuild on another machine. The available Ubuntu media is 24.04.1, while the reference host is 24.04.4; exact-point media is absent. Complete protected-stack package/dependency closure, portable Ross/Local KB resources, and clean-host rebuild remain UNKNOWN/NOT TESTED. The kit therefore remains `PARTIAL`, not `READY`.

No payload was deleted, moved, or duplicated during this revalidation. Large installer and model files were not recopied.
