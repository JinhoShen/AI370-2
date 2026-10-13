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
- Ross HLS run-flow Skill and local Qwen HLS CSim/CSynth source-validation cohort later exercised under M13; VS Code UI activation and local answer-model/end-to-end air-gap remain `NOT_TESTED`;
- Local LLM checks are backend readiness only; no model inference was run.

Machine-readable status and the small set of underlying logs are retained in the evidence directory linked above. Full run output remains under ignored `output/M14/runs/20261002T103455+0800/`.

## 2026-10-02 read-only evidence audit

`scripts/verify_m14_evidence.sh` is a separate safe-to-rerun evidence/package/module guard. It verifies the saved M11/M12/M13 SHA256 manifests, the M12 physical AXI transaction markers, the M13 HLS C-simulation/synthesis evidence, Git whitespace, and currently installed protected package/module versions. It does not run HIP, Vulkan, NPU, LLM, FPGA programming, or other accelerator workloads.

The earlier 2026-10-02 15:18:00 run returned **PASS_WITH_DEFERRED**, 0 failures and 5 deferred/not-tested groups. The 15:29:15 rerun after adding the M12 clean-rebuild check also returned **PASS_WITH_DEFERRED**, 0 failures and 5 deferred/not-tested groups. Protected Kernel, Mesa, libdrm, ROCm/HIP, XRT, amdxdna and firmware were checked read-only. This audit does not replace the broader 10:34:55–10:35:01 workstation run; together they cover dynamic bounded checks and current evidence integrity at different times. Current run artifacts are saved under [`evidence/2026-10-02/evidence-audit-20261002T152915+0800/`](evidence/2026-10-02/evidence-audit-20261002T152915+0800/).

## APT dependency/change guard

`scripts/apt_change_guard.py` accepts package names only, captures `apt-get -s` output, and blocks installs/upgrades/removals in protected Kernel, graphics, ROCm/HIP/HSA, XRT, amdxdna and GPU/NPU firmware families. It fails closed if APT returns an unrecognized transaction shape. Six parser tests cover safe packages, Mesa/libdrm, kernel/XRT/firmware removals, ROCm/AMDGPU driver changes, mixed actions and unknown output. A real APT simulation for the absent `cowsay` package returned `SAFE_SIMULATION` with only one userspace install planned; no package was installed. Evidence and exact simulation transcript are in [`evidence/2026-10-02/apt-guard/`](evidence/2026-10-02/apt-guard/).

## Scope boundary

This establishes **AUTOMATION VERIFIED for the executed checks above**, not complete M14 PASS. The APT dependency/change guard is VERIFIED for six parser cases and one safe userspace simulation; live protected-stack transactions remain deliberately untested. A clean, out-of-tree M12 source-to-bitstream rebuild also completed successfully with zero DRC errors and timing constraints met. Its bitstream has four timestamp-header bytes different from the previously retained artifact and was not programmed; see [clean rebuild evidence](evidence/2026-10-02/m12-clean-rebuild/). This verifies one design's software rebuild procedure, not full toolchain reinstallation or recovery. Recovery/checkpoint rehearsal and SP701 physical automation remain incomplete or unexecuted. Ross readiness checks are part of the verifier; direct HLS C/RTL co-simulation/implementation and the supervised local-Qwen source-edit flow have separate M13 evidence. Ross/Codex agent-driven HLS, VS Code activation and full local-answer/air-gap workflows remain untested. No protected GPU/NPU stack was changed.

## 2026-10-02 status addendum

The Ross download/installation gate is cleared for the artifacts currently available under `resources/ROSS`: the 2026.9.1 Vivado MCP server, VS Code extension and Codex Agent Skills are installed; Codex CLI successfully invoked the local AMD doc-search MCP. M14 now performs repeatable version/config/Skills/local MCP readiness checks. See [M13 validation evidence](../M13/evidence/2026-10-02/ROSS_M13_VALIDATION.md) and the 2026-10-02 M14 run evidence.

M14 remains IN PROGRESS. The readiness verifier does not establish a reproducible Ross installation/rebuild. The clean M12 rebuild is a bounded design-level result; full workstation/toolchain rebuild, recovery/checkpoint rehearsal and SP701 physical automation remain outstanding. The evidence audit validates retained M12 physical logs without claiming the live target is currently attached. The earlier 2026-10-01 statement that Ross installation was deferred records the state at that time and is retained as history.

## 2026-10-06 Codex sandbox and license follow-up

The initial read-only diagnosis recorded the then-missing Ubuntu Bubblewrap AppArmor profile and the `apparmor_restrict_unprivileged_userns=1` restriction. Under the user's authorization, the scoped profile was subsequently installed; a restricted read-only Codex sandbox probe passed, while global AppArmor and the kernel restriction remain enabled. The historical diagnosis is annotated and retained at [M13 sandbox evidence](../M13/evidence/2026-10-06/codex-sandbox-diagnostic.md).

A separate follow-up identified the Vivado license failure: the host-locked FlexNet license depends on a NIC MAC hidden by the default sandbox network namespace. A bounded workspace-write invocation with `sandbox_workspace_write.network_access=true` restored host identity and passed the Qwen-authored XSim/Vivado synthesis flow without changing the license or protected stack. The precise comparison and invocation scope are in [M13 license evidence](../M13/evidence/2026-10-06/local-qwen-codex-fpga-loop/sandbox-license-diagnosis.md).

The read-only M14 evidence auditor was extended to verify the new local-Qwen source/test/report manifest and pass markers, then extended again to verify the model-feedback RTL repair evidence, exact XSim failure/pass markers and its checksum manifest. The broad workstation verifier was deliberately not rerun because it repeats HIP/Vulkan/NPU checks; its previous full result remains dated evidence.

The initial 2026-10-06 audits at 16:44:21 and 16:52:07 +08:00 both exited 0 with **PASS_WITH_DEFERRED**, 0 failures, and 5 deferred/not-tested groups. After adding the bounded Qwen→XSim feedback-repair evidence, the audit ran at 18:24:40 +08:00 and again exited 0 with **PASS_WITH_DEFERRED**, 0 failures and 5 deferred/not-tested groups. All M11/M12/M13 retained evidence, APT guard tests/safe simulation and current protected package/module versions passed. M15 unified regression was explicitly NOT_TESTED by this read-only audit. See [the original audit series](evidence/2026-10-06/read-only-evidence-audit/README.md) and [18:24 closeout audit](evidence/2026-10-06/read-only-evidence-audit-182440/README.md).

The M14 evidence auditor verifies both the read-only local-provider tool cycle and the bounded same-model XSim feedback repair. The original repair was a supervised one-file loop; subsequent isolated M13 A/B work attempted multi-file repair and Ross-assisted HLS source validation, with mixed results recorded in M13. These experiments do not verify M14-wide unattended automation. The full workstation verifier was not rerun.

## 2026-10-12 integration readiness observation

The existing Lemonade and local-Qwen Agent services were checked without rerunning M14's broad HIP/Vulkan/NPU verifier. Lemonade's actual port 13305 health endpoint and a bounded CPU inference passed; a fresh read-only Codex-to-local-Qwen tool cycle passed and its complete event transcript is retained under [M13 evidence](../M13/evidence/2026-10-12/local-qwen-lemonade-agent/). The resource policy now follows this host's detected capacity: no fixed CPUQuota or MemoryMax, with swap still disabled for the model service; this is a host configuration observation, not newly verified rebuild automation. No protected stack or accelerator regression was run. M14 remains IN PROGRESS because the clean-host rebuild, recovery rehearsal and fully reproducible deployment closure are still unverified.


## 2026-10-05 local provider compatibility check

A standalone M13 probe (not part of the repeatable M14 workstation verifier) confirmed that Codex CLI 0.159.2 received a bounded text reply from the local Qwen3.8 Responses provider. Its initial `exec_command` failed at Bubblewrap startup; this is retained as historical evidence. The authorized AppArmor-profile remediation later enabled restricted sandbox execution. On 2026-10-06 the local provider selected a standard read-only `exec_command`; Codex executed it successfully and returned the exact marker. This verifies one direct local-provider tool cycle; write-capable multi-step self-repair and full air-gap remain unverified. The M14 local-LLM automated verifier remains backend-readiness only and does not run model inference. Evidence: [Codex local provider check](../M13/evidence/local-model-fpga-engineering-2026-10-05/codex-local-provider-20261005/README.md), [sandbox/license follow-up](../M13/evidence/2026-10-06/local-qwen-codex-fpga-loop/README.md), and [tool-loop result](../M13/evidence/2026-10-06/local-agent-tool-loop/README.md).

## 2026-10-12 standalone Local Agent tool framework

`scripts/local_agent.py` adds a reusable local Qwen/Lemonade tool loop without Codex or cloud APIs. Its provider is restricted to loopback, proxies/redirects are disabled, text paths are workspace-relative and bounded, patching is limited to a single existing file, and arbitrary shell commands are not exposed. Fixed subprocess checks and XSim run in Bubblewrap; the host filesystem is mounted read-only except for the selected workspace. The XSim runner has bounded invocation/correction/time limits and retains host NIC identity only for the already MAC-bound Vivado license.

The four Local Agent policy tests and four Telegram controller policy tests passed. The standalone Qwen→RTL→XSim repair executed with actual model/tool evidence and passed the existing testbench. The offline-mode Local Agent read a unique marker through its local tool; an external network probe inside the Bubblewrap tool namespace returned `errno=101`. The model API itself stayed on loopback. The new evidence manifest and complete transcript are in [standalone Local Agent evidence](../M13/evidence/2026-10-12/local-qwen-standalone-agent-rtl/README.md).

This adds a tested bounded verification component to M14; it does not complete the unattended clean-host rebuild, full recovery rehearsal, offline dependency closure or whole-workstation automation. Telegram's code path now uses the Local Agent, but live Bot API authentication/pairing remains WAITING_USER. No protected stack or FPGA hardware was changed, and the full workstation verifier was not rerun.

## 2026-10-13 Ross-agent policy and experiment support

The Local Agent gained bounded opt-in AMD Ross Skill/local MCP calls and a guarded two-file patch policy for isolated M13 A/B trials. Policy unit tests and measured experiment results are documented in [M13 Ross benchmark report](../M13/M13_ROSS_AB_BENCHMARK_REPORT.md). This verifies the scoped agent component only; it does not verify M14's full workstation automation, offline rebuild, or recovery workflow. The broad verifier was not rerun.


## 2026-10-13 M13 Ross benchmark closeout

The fixed corrected M13 T2 multi-file A/B cohort has now completed all six trials; T1/T2/T3 outcomes and checksummed curated evidence are in [the M13 Ross benchmark report](../M13/M13_ROSS_AB_BENCHMARK_REPORT.md). This closes the benchmark sample collection, not the broader M14 automation scope. The M14 full workstation verifier and accelerator regressions were not rerun.


The 2026-10-13 M13/Model Lab support verification reran `python3 scripts/test_local_agent.py` (17/17) and `python3 scripts/test_telegram_agent.py` (4/4), Python byte-compilation for the Local Agent and T1/T2/HLS/Model Lab runners, and `bash -n` for the fixed T2/HLS validators. This is a scoped test-suite update; no M14-wide verifier or GPU/NPU/FPGA regression was rerun.
