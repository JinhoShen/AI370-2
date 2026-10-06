# T7 final full-manifest verification at repository commit 8f6bf85

**Date:** 2026-10-06 (Asia/Taipei); exact start and completion times were not retained.

From `/media/shen/T7/AMD_AI_Workstation/`, `sha256sum -c SHA256SUMS` exited 0 and reported **1,023/1,023 entries OK**. The complete output is retained in `sha256sum-full-check.log`; its SHA256 is `adcee7405118e0c92a426b243a07e9f47e6b3bcbdf3c47cebf761094f25b97d6`.

At this verification point the T7 Git bundle was `AI370-2-main-8f6bf85.bundle`; `git bundle verify` passed and an isolated clone's `main` matched `8f6bf85573a340a6f17faff148cde6621d612695`, with all three historical Golden/toolchain tags. The convenience Guides snapshot had 971 files. The deployment root held 1,025 files / 237,874,361,103 logical bytes, with 179,988,856,832 bytes free.

The bundle/media verification did not access `/media/shen/T7/照片`. T7 integrity is VERIFIED, while deployment readiness remains PARTIAL: Ubuntu media is 24.04.1 versus the reference host's 24.04.4, complete protected-stack offline dependency closure and portable Ross/Local KB closure are unknown, and clean-host rebuild is not tested. This record does not claim migration/rebuild PASS.
