# 2026-10-15 read-only closeout audit

Command: `bash scripts/verify_m14_evidence.sh`

Actual start: 2026-10-15T18:28:21+08:00, input HEAD 47fcd0c. Exit 1: 25 PASS, 2 FAIL, 5 DEFERRED/NOT_TESTED. Full package/module and checksum logs are retained. The two failures are Mesa/libdrm package revisions .2 versus accepted .1, recorded in protected-stack-drift.txt. Expected baseline remains unchanged.

The separate new local-engineering semantic audit passed: 36 retained repairs, real Ross provenance, 664 SHA256 entries, 20 three-repetition measured configurations and preserved ROCm resource stop. These are historical evidence checks, not newly executed FPGA/model tasks. Four negative policy tests passed; executed source copies are retained. No packages, model services or T7 data were changed.

The package drift predates this run and was already present in both 2026-10-14 model-optimization snapshots. Approval/actor provenance remains UNKNOWN. No automatic downgrade or baseline acceptance was attempted.
