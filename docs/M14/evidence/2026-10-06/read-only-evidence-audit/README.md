# M14 read-only evidence audit

**Date:** 2026-10-06 (Asia/Taipei)
**Verifier commit:** `a678708ab840f9396f82d618574bd5bea50b9814`
**Result:** `PASS_WITH_DEFERRED`; 0 failures, 5 deferred/not-tested groups.

Ran `scripts/verify_m14_evidence.sh`. This audit checked retained M11/M12/M13 evidence hashes and markers, the new local-Qwen RTL/XSim/Vivado manifest and pass records, APT guard parser tests and saved safe simulation, Git whitespace, and the pinned protected package/DKMS module versions.

The new M13 check verified every file in the local-Qwen evidence SHA256 manifest and confirmed the XSim and Vivado synthesis markers plus report summaries. The audit did not rerun HIP, Vulkan, NPU inference, Local LLM inference, Vivado synthesis, FPGA programming, or the M15 unified regression. It does not claim those workloads passed in this audit window.

Deferred/not-tested items remain: live protected-stack transaction simulation, standard SP701 XRT host application, full local-answer/air-gap validation, complete M0.1 recovery, and M15 unified regression. These are explicit scope boundaries, not hidden failures.

The machine-readable run summary, checks, protected package/module snapshot, and bounded verification logs are in this directory. Full command output remains in ignored `output/M14/evidence-audit/20261006T152712+0800/`.
