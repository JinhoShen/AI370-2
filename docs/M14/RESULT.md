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

## 2026-10-02 read-only evidence audit

`scripts/verify_m14_evidence.sh` is a separate safe-to-rerun evidence/package/module guard. It verifies the saved M11/M12/M13 SHA256 manifests, the M12 physical AXI transaction markers, the M13 HLS C-simulation/synthesis evidence, Git whitespace, and currently installed protected package/module versions. It does not run HIP, Vulkan, NPU, LLM, FPGA programming, or other accelerator workloads.

The earlier 2026-10-02 15:18:00 run returned **PASS_WITH_DEFERRED**, 0 failures and 5 deferred/not-tested groups. The 15:29:15 rerun after adding the M12 clean-rebuild check also returned **PASS_WITH_DEFERRED**, 0 failures and 5 deferred/not-tested groups. Protected Kernel, Mesa, libdrm, ROCm/HIP, XRT, amdxdna and firmware were checked read-only. This audit does not replace the broader 10:34:55–10:35:01 workstation run; together they cover dynamic bounded checks and current evidence integrity at different times. Current run artifacts are saved under [`evidence/2026-10-02/evidence-audit-20261002T152915+0800/`](evidence/2026-10-02/evidence-audit-20261002T152915+0800/).

## APT dependency/change guard

`scripts/apt_change_guard.py` accepts package names only, captures `apt-get -s` output, and blocks installs/upgrades/removals in protected Kernel, graphics, ROCm/HIP/HSA, XRT, amdxdna and GPU/NPU firmware families. It fails closed if APT returns an unrecognized transaction shape. Six parser tests cover safe packages, Mesa/libdrm, kernel/XRT/firmware removals, ROCm/AMDGPU driver changes, mixed actions and unknown output. A real APT simulation for the absent `cowsay` package returned `SAFE_SIMULATION` with only one userspace install planned; no package was installed. Evidence and exact simulation transcript are in [`evidence/2026-10-02/apt-guard/`](evidence/2026-10-02/apt-guard/).

## Scope boundary

This establishes **AUTOMATION VERIFIED for the executed checks above**, not complete M14 PASS. The new APT dependency/change guard is VERIFIED for six parser cases and one safe userspace simulation; live protected-stack transactions remain deliberately untested. A clean, out-of-tree M12 source-to-bitstream rebuild also completed successfully with zero DRC errors and timing constraints met. Its bitstream has four timestamp-header bytes different from the previously retained artifact and was not programmed; see [clean rebuild evidence](evidence/2026-10-02/m12-clean-rebuild/). This verifies one design's software rebuild procedure, not full toolchain reinstallation or recovery. Recovery/checkpoint rehearsal and SP701 physical automation remain incomplete or unexecuted. Ross readiness checks are now part of the verifier; Ross HLS C simulation/synthesis/report now have separate M13 evidence; HLS cosimulation/implementation, VS Code activation and local-answer workflows remain untested. No protected GPU/NPU stack was changed.

## 2026-10-02 status addendum

The Ross download/installation gate is cleared for the artifacts currently available under `resources/ROSS`: the 2026.9.1 Vivado MCP server, VS Code extension and Codex Agent Skills are installed; Codex CLI successfully invoked the local AMD doc-search MCP. M14 now performs repeatable version/config/Skills/local MCP readiness checks. See [M13 validation evidence](../M13/evidence/2026-10-02/ROSS_M13_VALIDATION.md) and the 2026-10-02 M14 run evidence.

M14 remains IN PROGRESS. The readiness verifier does not establish a reproducible Ross installation/rebuild. The clean M12 rebuild is a bounded design-level result; full workstation/toolchain rebuild, recovery/checkpoint rehearsal and SP701 physical automation remain outstanding. The evidence audit validates retained M12 physical logs without claiming the live target is currently attached. The earlier 2026-10-01 statement that Ross installation was deferred records the state at that time and is retained as history.


## 2026-10-05 local provider compatibility check

A standalone M13 probe (not part of the repeatable M14 workstation verifier) confirmed that Codex CLI 0.159.2 received a bounded text reply from the local Qwen3.8 Responses provider. Codex also dispatched a standard `exec_command` for a read-only `cat` in an isolated `/tmp` workspace, but Bubblewrap failed before running the command with `Failed RTM_NEWADDR: Operation not permitted`. No unconfined fallback was attempted. The M14 local-LLM automated verifier remains backend-readiness only; local tool-command automation is BLOCKED until the sandbox can be run safely. Evidence: [Codex local provider check](../M13/evidence/local-model-fpga-engineering-2026-10-05/codex-local-provider-20261005/README.md).
