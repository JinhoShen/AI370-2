# M14 Automation / Reproducible Rebuild — guarded verifier

Date: 2026-10-01 (Asia/Taipei). This is the first tested M14 entry point. It is a verification helper, not a complete unattended workstation rebuild.

## Tested automation

`scripts/verify_m14_workstation.sh` was executed against the current host. It completed with exit status 0 and recorded `fail=0`, with explicit deferred items. The run verified:

- system/kernel/OS inventory;
- protected ROCm/HIP/XRT package versions and amdxdna DKMS path/version;
- HIP `gfx1150` smoke and Vulkan RADV smoke;
- XRT/NPU enumeration and strict VitisAI CNN no-fallback result;
- Vivado, `v++` and `platforminfo` 2026.1 version checks;
- retained HLS report, SP701 post-route DCP and utilization report;
- targeted kernel-log audit during the verifier window.

The script intentionally reports, rather than hides, these conditions:

- SP701 timing is `DEFERRED` because the design has no timing constraints;
- SP701 bitstream is `DEFERRED` because board I/O constraints are missing and Vivado DRC blocked bitgen;
- Local LLM is readiness-only in this phase; no model regression was run;
- Ross is deferred pending the user's AMD download and installation.

## Scope boundary

This is **AUTOMATION VERIFIED for the executed checks above**, not a complete M14 rebuild PASS. Installation helpers, dependency guards, recovery/checkpoint rehearsal, Ross verification and SP701 physical automation remain incomplete or unexecuted. No protected GPU/NPU stack was changed.

## 2026-10-02 status addendum

The Ross download/installation gate is cleared for the artifacts currently available under `resources/ROSS`: the 2026.9.1 Vivado MCP server, VS Code extension and Codex Agent Skills are installed; Codex CLI successfully invoked the local AMD doc-search MCP. See [M13 validation evidence](../M13/evidence/2026-10-02/ROSS_M13_VALIDATION.md).

M14 remains IN PROGRESS. No Ross verification automation has been added or tested; this manual M13 evidence does not establish a reproducible Ross rebuild. Installation helpers, dependency/change guards, recovery/checkpoint rehearsal and SP701 physical automation remain outstanding. The earlier 2026-10-01 statement that Ross installation was deferred records the state at that time and is retained as history.
