# M14 Automation / Reproducible Rebuild

**Status: IN PROGRESS.** The guarded workstation verification entry point is exercised on-host; M14 is not a complete unattended rebuild or recovery PASS.

The original 2026-10-01 run and its scope remain historical evidence below. The verifier was extended and rerun on 2026-10-02; detailed retained outputs are in [`evidence/2026-10-02/guarded-run-103455/`](evidence/2026-10-02/guarded-run-103455/).

## Tested automation

`scripts/verify_m14_workstation.sh` now creates a timestamped run directory under ignored `output/M14/runs/`, retains per-check logs, and writes a machine-readable `summary.json` with PASS / FAIL / DEFERRED / NOT_TESTED. It only performs bounded, previously validated smoke tests, version/readiness checks, and evidence-presence checks; it does not install packages, modify configuration, synthesize hardware designs, or run model inference.

### 2026-10-02 guarded run

The run from 10:34:55 to 10:35:01 +08:00 exited 0 with `PASS_WITH_DEFERRED`, 0 failures and 3 deferred/not-tested check groups. It verified:

- system inventory and exact protected package/module versions;
- bounded HIP gfx1150 and Vulkan/RADV compute checks;
- XRT 2.21.75, XDNA2 firmware 1.1.2.64 and NPU enumeration;
- strict VitisAI-only CNN execution, positive NPU hardware counter delta and zero output error;
- llama.cpp CPU, Vulkan/RADV and ROCm/HIP binary startup/device enumeration only (no model inference);
- Vivado, Vitis `v++`, `platforminfo` 2026.1 and retained HLS/SP701 software artifacts;
- Ross Vivado MCP 2026.9.1, Codex MCP configuration, 49 installed Skills, and local Knowledge Base MCP initialize/tools-list;
- targeted kernel fault audit during the verifier window.

The verifier reported, rather than hiding, these conditions:

- SP701 timing/bitstream `DEFERRED`: timing is unconstrained; bitstream remains blocked by NSTD-1/UCIO-1 due to missing verified board I/O constraints;
- SP701 physical JTAG/programming/execution `NOT_TESTED`;
- Ross HLS Skill execution, VS Code UI activation and local answer-model/end-to-end air-gap `NOT_TESTED`;
- Local LLM checks are backend readiness only; no model inference was run.

Machine-readable status and the small set of underlying logs are retained in the evidence directory linked above. Full run output remains under ignored `output/M14/runs/20261002T103455+0800/`.

## Scope boundary

This establishes **AUTOMATION VERIFIED for the executed checks above**, not complete M14 PASS. Dependency/change guard automation beyond the read-only pinned-version check, installation/rebuild helpers, recovery/checkpoint rehearsal and SP701 physical automation remain incomplete or unexecuted. Ross readiness checks are now part of the verifier; live Ross HLS / VS Code / local-answer workflows remain untested. No protected GPU/NPU stack was changed.

## 2026-10-02 status addendum

The Ross download/installation gate is cleared for the artifacts currently available under `resources/ROSS`: the 2026.9.1 Vivado MCP server, VS Code extension and Codex Agent Skills are installed; Codex CLI successfully invoked the local AMD doc-search MCP. M14 now performs repeatable version/config/Skills/local MCP readiness checks. See [M13 validation evidence](../M13/evidence/2026-10-02/ROSS_M13_VALIDATION.md) and the 2026-10-02 M14 run evidence.

M14 remains IN PROGRESS. The readiness verifier does not establish a reproducible Ross installation/rebuild. Installation helpers, stronger dependency/change guards, recovery/checkpoint rehearsal and SP701 physical automation remain outstanding. The earlier 2026-10-01 statement that Ross installation was deferred records the state at that time and is retained as history.
