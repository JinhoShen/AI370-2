# M14 read-only evidence audit

**Date:** 2026-10-06 (Asia/Taipei)
**Earlier verifier commit:** `a678708ab840f9396f82d618574bd5bea50b9814`

**Latest run:** 2026-10-06 16:52:07 +08:00 at pre-commit HEAD `b1e75d32bbded1d7564bf151d4dc14d07bfcadaf`

**Result:** `PASS_WITH_DEFERRED`; 0 failures, 5 deferred/not-tested groups.

Ran `scripts/verify_m14_evidence.sh`. This audit checked retained M11/M12/M13 evidence hashes and markers, the new local-Qwen RTL/XSim/Vivado manifest and pass records, APT guard parser tests and saved safe simulation, Git whitespace, and the pinned protected package/DKMS module versions.

The latest M13 checks verified every file in both the local-Qwen RTL/XSim/Vivado SHA256 manifest and the local Qwen→Codex read-only tool-loop manifest. The tool-loop check confirmed the model-selected `exec_command` succeeded and Codex returned the exact marker from its tool result. The audit did not rerun HIP, Vulkan, NPU inference, Local LLM inference, Vivado synthesis, FPGA programming, or the M15 unified regression. It does not claim those workloads passed in this audit window.

Deferred/not-tested items remain: live protected-stack transaction simulation, standard SP701 XRT host application, write-capable multi-step local-agent self-repair and full air-gap validation, complete M0.1 recovery, and M15 unified regression. These are explicit scope boundaries, not hidden failures.

The first machine-readable audit snapshot remains in this directory root. The two completed closeout runs are under [`final-20261006T164421/`](final-20261006T164421/) and [`final-20261006T165207/`](final-20261006T165207/); the latest full command output remains in ignored `output/M14/evidence-audit/20261006T165207+0800/`.
