# T7 full deployment manifest verification

**Date:** 2026-10-06 (Asia/Taipei); exact start/end time not retained.

At repository commit `71f8248d4fa3d67bf703fc6d7d563fbb7b00bf20`, the T7 deployment root `/media/shen/T7/AMD_AI_Workstation/` passed `sha256sum -c SHA256SUMS`: **1,027/1,027 entries OK**, exit 0. The full command output is retained in `sha256sum-final-1027.log`; SHA256 `612475337f95b57d68af9a5742a2d1f5a33dc54cc9dbc0aca438f6d0e27863cc`.

The current-main bundle at that point was `02_Deployment/AI370-2/Git/AI370-2-main-71f8248.bundle`, size 13,443,302 bytes, SHA256 `64f96c65c40842bf39b2d7581107eb5146bc5e198b324f1488793c82d7932be7`. `git bundle verify` passed. An isolated `git clone --branch main` matched exact HEAD `71f8248d4fa3d67bf703fc6d7d563fbb7b00bf20` and contained all three historical Golden/toolchain tags.

The Guides snapshot contains 974 tracked README/docs/scripts files. The deployment root held 1,029 files at verification time. No files in `/media/shen/T7/照片` were accessed. Integrity is VERIFIED; deployment readiness remains PARTIAL because exact Ubuntu 24.04.4 media, complete protected-stack offline dependency closure, portable Ross/Local KB closure and a clean-host rebuild are not verified.
