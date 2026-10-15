# Graphics baseline acceptance — 2026-10-15

**Decision: ACCEPT current installed Ubuntu `.2` graphics package revisions for the executed bounded workstation scope.** This is an engineering decision under the user's delegation to complete routine work without further approval prompts. No package was upgraded, downgraded, installed or replaced. This accepts tested existing state; it does not accept future protected-stack changes or declare M15 FINAL_GOLDEN_PASS.

The earlier `2026-10-15T18:28:21+08:00` audit correctly failed against `.1`. Dpkg/APT records place the existing upgrades on 2026-10-13, and both 2026-10-14 optimization snapshots already recorded `.2`. Keep that failure as historical evidence.

## Accepted exact revisions

- `mesa-vulkan-drivers`: `25.2.8-0ubuntu0.24.04.2`
- `libdrm-amdgpu1`: `2.4.125-1ubuntu0.1~24.04.2`

Kernel, ROCm/HIP, XRT, amdxdna and firmware remain protected at their separately verified versions. No official-support or ABI-equivalence claim is inferred from the Ubuntu revision suffix.

## Actual functional evidence

Start `2026-10-15T18:35:46+08:00`; completion `2026-10-15T18:35:50.638471+08:00`.

- HIP: 1,024 GPU results verified, PASS.
- Vulkan/RADV: 1,024 shader results verified, CPU fallback forbidden, PASS.
- XRT: Strix NPU and firmware 1.1.2.64 enumerated, PASS.
- CNN: VitisAIExecutionProvider only, CPU fallback disabled, NPU hardware time increased **14,897,582 ns**, CPU-reference max error **0**, PASS.
- Kernel audit readable, no new targeted GPU/NPU/OOM fault during the test window.
- All installed package versions identical before/after the test. No model inference, FPGA programming, T7 access or installation occurred.

[Functional result](evidence/2026-10-15/graphics-baseline-acceptance/result.json), [strict NPU result](evidence/2026-10-15/graphics-baseline-acceptance/npu-result.json).

Only after those checks passed, the two expected revisions were updated in `verify_m14_evidence.sh` and `verify_m14_workstation.sh`. The read-only audit at `2026-10-15T18:37:35+08:00` then passed **27 checks, zero failures, five deferred/not-tested groups**. [Accepted-baseline audit](../M14/evidence/2026-10-15/accepted-baseline-audit/summary.json). It did not rerun the broad workload suite. Prior .1 baseline reports and failed drift evidence were retained unchanged.

## Scope

The baseline review gate is **RESOLVED**. M15 remains PRE-FINAL for the separate deployment/offline/rebuild and final scope requirements. ROCm18 tuning remains safety-deferred; Qwen3.6 remains retired/OPEN; M8 NPU LLM remains DEFERRED. The formal Qwen profile was not changed by this acceptance.
