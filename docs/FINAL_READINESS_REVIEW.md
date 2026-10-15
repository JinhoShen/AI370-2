# AI370-2 Final Readiness Review — 2026-10-15

## Current operational checkpoint — 2026-10-15 18:52

**READY_FOR_FINAL_REVIEW / SOFTWARE_PASS_WITH_DEFERRED; full M15 remains PRE-FINAL.** The existing Qwen XL formal service now uses saved ENGINEERING Vulkan16K/24-thread options. A fresh actual Local Qwen + Ross + fixed XSim repair passed; current software regression, protected `.2` guard, strict NPU and model API all passed. The single-trial/cohort-wrapper false negative and automatic CPU recovery are preserved separately; actual model/testbench PASS was independently verified before final profile adoption. No model/driver/firmware/toolchain was replaced. [Operational handoff and evidence](LOCAL_ENGINEERING_HANDOFF.md).

Independent remaining conditions: T7 user hold, Telegram token absent/E2E WAITING_USER, clean-host rebuild/full restore and physical host-disconnected workflow NOT_TESTED. Broader IDE/direct Tcl automation remains deferred. No Final Golden, release, tag or push is claimed. Older gates and CPU-profile statements below describe their dated checkpoints; the protected baseline gate is resolved and the formal profile was subsequently promoted.

## Current resolution — 2026-10-15 18:37:35 +08:00

**Baseline gate RESOLVED; current state PRE-FINAL / remaining scope as documented.** The agent accepted existing `.2` revisions after fresh bounded HIP/Vulkan/XRT/strict NPU tests passed. Guards now expect the accepted exact versions; the subsequent evidence audit has zero failures. No system packages were changed. See [baseline acceptance](M15/GRAPHICS_BASELINE_ACCEPTANCE_2026-10-15.md). Further approval is not requested for this resolved routine decision. The following 18:28 blocker record is retained as history; its request for a baseline decision is superseded. T7 user hold, clean-target rebuild and full host-disconnected proof remain independent incomplete items, not grounds to relabel them PASS.

## Historical 18:28 review

**ACTUAL verdict: BLOCKED_BASELINE_REVIEW; M15 remains PRE-FINAL.** This closeout adds read-only evidence verification and reconciles current documentation. It does not perform accelerator/model/FPGA workloads, install software, change the formal Qwen profile, accept a new Golden baseline or declare FINAL_GOLDEN_PASS.

## Actual work and evidence

The extended M14 evidence audit ran at `2026-10-15T18:28:21+08:00`, HEAD `47fcd0c`. It returned exit 1 / **FAIL**, with **25 PASS, 2 FAIL and 5 DEFERRED/NOT_TESTED** checks. [Summary](M14/evidence/2026-10-15/closeout-evidence-audit/summary.json), [protected drift](M14/evidence/2026-10-15/closeout-evidence-audit/protected-stack-drift.txt).

The new semantic checker `scripts/audit_local_engineering_evidence.py` passed: 36 historical Qwen/Gemma engineering trials, real Ross prerequisites, unchanged Non-Ross separation, actual baseline failure/final XSim or HLS success, accepted patches matching model-response arguments, retained RTL final hashes and RTL synthesis reports. It verified 664 SHA256 entries across the practical-cohort and optimization evidence. The optimization check preserves 20 successful three-repetition configurations and the failed ROCm18 load; it checks original/restored argv, the recorded package-version comparison and actual Local Agent read-file result. It does not turn historical results into current workload PASS.

Four negative-policy tests cover missing baseline/PASS markers, non-model patch injection, Ross arm contamination and checksum/path traversal. The full M14 audit also verified retained M11/M12 evidence and the unchanged kernel/ROCm/HIP/XRT/amdxdna versions. Its two protected-package failures were retained, not suppressed.

## New protected-stack gate

| Package | Existing accepted guard | ACTUAL installed | Outcome |
|---|---|---|---|
| mesa-vulkan-drivers | 25.2.8-0ubuntu0.24.04.1 | 25.2.8-0ubuntu0.24.04.2 | FAIL: exact-version mismatch |
| libdrm-amdgpu1 | 2.4.125-1ubuntu0.1~24.04.1 | 2.4.125-1ubuntu0.1~24.04.2 | FAIL: exact-version mismatch |

`/var/log/dpkg.log` records the upgrades at `2026-10-13 06:13:44` and `06:16:25` respectively (timestamps as logged). APT history corroborates those package transitions. The 2026-10-14 Qwen optimization baseline and final package snapshots both already contain `.2`, so that optimization's before/after equality remains true. This does **not** establish equality with the older `.1` Golden stack. Actor/approval provenance remains **UNKNOWN**.

No downgrade, replacement, upgrade, hold/configuration change or baseline-version edit was performed. The evidence guard still expects `.1` and must keep failing until the discrepancy is explicitly reviewed. Existing bounded Vulkan/ROCm results after the update remain valid for their measured tasks; they do not automatically authorize a new whole-workstation Golden baseline.

## Completion matrix

| Area | Verified scope / state | Remaining / disposition |
|---|---|---|
| M11 physical FPGA | Historical bounded SP701 JTAG/DDR PASS | Full capacity/endurance outside bounded acceptance; no reprogramming required for this review |
| M12 host↔FPGA | Historical physical JTAG-to-AXI workflow VERIFIED | Standard SP701 XRT/PCIe deployment is not established; no system XRT replacement is justified. Broader application transport/workloads DEFERRED |
| M13 Local Qwen + Ross engineering | Historical Vulkan16K Qwen T1/T2/T3: 18/18 PASS, including Ross 3/3 per task; independent XSim/synthesis/HLS markers and model provenance now audited | Full M13 remains PARTIAL. Direct Qwen-driven Vivado Tcl MCP, Vitis IDE/Embedded assistant operation and physical host-disconnected workflow NOT_TESTED. No unrestricted Tcl tool was added |
| M14 automation | Existing protected-stack/evidence auditor plus new semantic verification executed | Current protected guard FAIL for two package revisions. Full clean-host toolchain rebuild/recovery remains NOT_TESTED; no full M14 PASS |
| M15 integrated workstation | Historical unified regression PASS_WITH_DEFERRED; later bounded agent/model results retained | PRE-FINAL, blocked by baseline review plus deployment/rebuild and final scope acceptance. No fresh unified regression this turn |
| Qwen profiles | FAST Vulkan8K, ENGINEERING Vulkan16K, SAFE CPU24 MTP documented | Recommendations NOT_APPLIED. Formal CPU profile adoption/change is separate; promotion is not necessary to acknowledge existing bounded engineering evidence |
| ROCm optimization | Some short configurations PASS | ROCm18 load failed swap guard; remaining tuning safety-DEFERRED; no retry |
| Offline operation | Loopback local model, local KB and isolated-tool evidence verified within recorded boundaries | Full disconnected licensed workflow NOT_TESTED; do not infer it from a private IP or no observed cloud calls |
| Telegram | Existing controller implemented; historical WAITING_USER for BotFather credential | No token inspected or live API test run this turn; live delivery/remote work remains NOT_TESTED |
| T7 deployment / migration | Historical selected media checks retained | User hold remains BLOCKED; no T7 paths or Photos accessed; no current kit verification asserted |
| Rebuild/recovery | Guide/scripts and historical CP0 selected-file restore evidence exist | Clean compatible-target rebuild and full boot restore NOT_TESTED. A 350 GB current image/installed Xilinx tree copy is NOT_REQUIRED |
| M7.1 / M8 | Qwen3.6 issue OPEN / NPU LLM DEFERRED | Retired model excluded, no retry; these do not justify reopening the entire mainline |

## Next authorized boundary

1. Review why protected Ubuntu package revisions changed and whether retaining `.2` is approved. Do not auto-downgrade or edit expected versions to manufacture PASS.
2. Once that decision is explicit, define the minimum baseline acceptance checks using post-update evidence and only missing functional checks; do not automatically rerun every M0–M15 workload.
3. Resume T7 only when the user reconnects/releases the hold; offline-resource closure and a separate safe rebuild target remain independent requirements.
4. Complete or explicitly accept the remaining offline/IDE/deployment scope before a Final Golden designation. Telegram live verification requires the user-supplied credential; keep secrets out of Git.

No release, tag, push, protected-stack edit, model/service switch, large-model stress or FPGA programming was performed. This report is a concrete readiness/blocker record, not a claim that the entire project is finished.
