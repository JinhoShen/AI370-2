# Continuous local model engineering evaluation — started 2026-10-19

**RUNNING; not a completed benchmark or milestone PASS.** The user requested repeating the recommended model tests until they explicitly stop, with model-by-model progress and retained evidence for later evaluation.

## Fixed scope and order

1. Qwen3.8-27B-UD-Q4_K_M — explicit Vulkan profile.
2. Qwen3.8-27B-Uncensored-Q4_K_M — explicit Vulkan profile.
3. gemma-4-31b-jang-crack-Q4_K_M — explicit CPU profile. This is a separate safe candidate, not an automatic fallback or a retry of the previously blocked UI Vulkan load.
4. Qwen3.8-27B-UD-Q4_K_XL — explicit Vulkan profile.

Use only existing local files; verify full SHA256 before each model's first load and size/mtime against that snapshot on later loads. No model downloads, registration, saved-recipe updates, kernel/driver/firmware changes, FPGA programming or T7 access.

Context 16,384; all available logical CPUs (currently 24), batch/micro-batch 2048/512, one slot. One large model at a time. The resident formal model is temporarily unloaded; the existing local KB embedding helper is separate and unchanged.

Each complete cycle has **72 engineering trials**: four models × T1/T2/T3 × Ross/Non-Ross × three independent trials. The models rotate after each repetition's six-task block; per model/task the arm order is A1 → B1 → B2 → A2 → A3 → B3. A new cycle uses new workspaces and original unchanged seeds. Do not carry model patches into later trials.

T1 fixed RTL repair; T2 fixed two-file RTL repair; T3 fixed HLS C simulation/C synthesis. Real Local Agent/sandbox/tool loops are reused. Each successful RTL trial receives independent fixed sandboxed Vivado synthesis. Timing reports are not timing closure. Actual user-project onboarding, physical air-gap per model, new-board hardware, long-job cancellation and complete workstation recovery are not covered merely by these repeated tasks; mark them NOT_TESTED until separately exercised.

## Evidence and interpretation

Live state: `output/model-endurance/status.json`. The local UI at http://127.0.0.1:13306/ shows the current model/stage/task/arm. Controller messages also enter `controller.log` and each session's `events.jsonl`.

Every session retains original formal runtime and package/module state, exact harness copies/SHA256, protocol, full model SHA256, runtime commands/load duration/offload logs, smoke output, isolated model response/tool traces, accepted model patches, before/after source hashes, fixed testbench/runner, XSim/HLS/Vivado logs/reports, per-trial resource/timing/token statistics, result and scoreboard. Per-case SHA256 manifests are generated after each finished case; a session-wide manifest is generated on a controlled stop.

Success requires genuine baseline failure, a model-authored accepted patch and the unchanged validator's terminal PASS. Ross cases require actual Ross Skill/local KB calls; Non-Ross cases must have none. Source provenance is checked independently. No Codex-authored repair is substituted.

FAIL, TIMEOUT, HARNESS_INVALID, resource stops, cancellations and model-load failures stay in their original records. Scoreboard timings include recorded failed attempts; load failures are separate feasibility evidence, not fabricated engineering task trials. Partial groups do not qualify for 3/3 acceptance. Compare task/condition separately. Gemma's CPU versus Qwen's Vulkan timing measures the configured workstation workflow, not an isolated intrinsic model-speed difference. Raw token/attempt/resource fields are retained for later analysis; no universal winner is declared from an unfinished cycle.

## Safety and stopping

- Shared exclusive operation lock prevents UI jobs/model switches during evaluation. The UI remains available for progress and stopping.
- Minimum MemAvailable: max(6 GiB, 12.5% of OS-visible RAM). Maximum host swap growth per load/trial: 64 MiB. Resource stops suspend that model/configuration for the remaining session; no repeated pressure on a blocked configuration.
- Check readable kernel logs throughout loads/trials, frozen harness/source artifacts and protected package/module state. Severe kernel/GPU fault or protected-stack drift stops the controller. It must not reload the formal GPU profile after such a gate.
- Disk free below 20 GiB stops work; no automatic evidence deletion. All-configurations-blocked ends with BLOCKED instead of a busy retry loop.
- Finite load/request/agent/tool/trial timeouts. Ordinary model/task failures are recorded and other safe trials continue.
- Stop using the UI **停止目前工作**, or:

```bash
systemctl --user stop ai370-model-evaluation.service
```

An orderly stop terminates owned child tools/server and restores the formal Qwen ENGINEERING settings using explicit measured CLI arguments without `--save-options`; only a passing exact runtime verifier yields restoration PASS. Serious kernel/stack gates intentionally leave restoration DEFERRED_SAFETY. Power loss/SIGKILL cannot guarantee restoration or a complete manifest. The transient service is not enabled for boot and does not auto-restart after failure.

## Startup history retained

Initial session `20261019T161443+0800` produced zero engineering trials. Default llama-server verbosity did not expose offload proof, so loading was conservatively blocked (`GPU_OFFLOAD_NOT_PROVEN`); no CPU fallback or model reasoning failure was inferred. The controller was deliberately stopped during initialization to improve telemetry/safe-exit handling, and formal restoration PASS was recorded. The raw stop mechanism labels its signal `USER_STOP`; this first stop was initiated by the developer's preflight correction, not the user's decision to end continuous evaluation.

Current session `20261019T161655+0800` uses documented log verbosity 5. The first Qwen UD Q4_K_M log proves Vulkan0/Radeon 890M and 66/66 layers offload; integrity and a bounded API smoke passed, and T1 Non-Ross A1 started at 16:17:25 +08:00. This is startup/readiness evidence, not a completed engineering PASS.

Framework checks: 66 unit tests passed before this session, including cohort counts, explicit CPU profile, retaining failed/timeouts in statistics and suppressing GPU reinitialization after kernel/stack gates. No real GPU fault was injected. Exact live harness copies are under the session output directory.
