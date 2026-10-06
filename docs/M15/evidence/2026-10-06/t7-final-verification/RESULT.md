# T7 deployment media final checksum and bundle verification

**Date:** 2026-10-06 (Asia/Taipei)

## Actual and verified

- Mounted media: `/dev/sda1` at `/media/shen/T7`, exFAT, read/write.
- Deployment root: `/media/shen/T7/AMD_AI_Workstation/`; only this root was traversed. The sibling `/media/shen/T7/照片` was not read or touched.
- Current bundle at verification time: `02_Deployment/AI370-2/Git/AI370-2-main-23acc2f.bundle`, 13,422,027 bytes, SHA256 `a8e09b4be14fdcd1315617d811e577c95573b2cb4fddece8f7d24ef046b0b146`.
- `git bundle verify` passed. An isolated clone's `main` exactly matched `23acc2f8336a2ac7aba2880956634d7a1faaa6d9`; all three historical Golden/toolchain tags were present.
- `02_Deployment/AI370-2/Guides/` contains 968 files refreshed from that committed `main`.
- From the deployment root, `sha256sum -c SHA256SUMS` exited 0 and reported all **1,019/1,019** entries `OK`. The complete output is `sha256sum-full-check.log`, SHA256 `ad8ae37551ab661f8566ce89b1903f88cb20af66cedc764b10d2047f7db79239`.
- At the final scan the root held 1,021 files and 237,860,844,232 logical bytes; T7 free space was 180,002,881,536 bytes. Category sizes: system resources 126,171,389,008 B; deployment 107,313,434 B; models 111,581,962,495 B.

An initial `sha256sum -c` was invoked from the repository working directory, so its relative paths resolved incorrectly. That command did not alter files. The full check above was rerun from the T7 deployment root and passed.

## Remaining deployment limitation

The T7 library is integrity-verified but remains **PARTIAL**, not rebuild-ready: it contains Ubuntu 24.04.1 media while the reference host uses 24.04.4; complete offline protected-stack package closure, portable Ross/Local KB closure, and clean-host rebuild have not been verified. File integrity does not imply those capabilities.
