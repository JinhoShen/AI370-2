# AI370-2 local engineering handoff — 2026-10-15

**Current checkpoint: READY_FOR_FINAL_REVIEW / SOFTWARE_PASS_WITH_DEFERRED.** The workstation is ready for the bounded local engineering workflows verified here. This is not a full M15 FINAL_GOLDEN_PASS, arbitrary-project autonomy guarantee, physical air-gap certification or clean-machine rebuild PASS.

## Daily configuration

- Model: existing Qwen3.8-27B-UD-Q4_K_XL; same SHA256/artifact.
- Lemonade API: `http://127.0.0.1:13305/api/v1`; existing user service `lemond.service`.
- Formal model profile adopted and saved: **ENGINEERING**, Vulkan0 / Radeon 890M, 24 inference and batch threads, context 16,384, 99 requested GPU layers (the identical measured model configuration offloads 66/66), batch/micro-batch 2048/512, auto Flash Attention, f16 K/V cache, reasoning off, one slot. Same installed llama.cpp Vulkan binary. No CPU fallback is accepted as this profile.
- Offline mode and no-fetch-executables enabled; telemetry and automatic model checks/updates disabled. These existing settings were inspected, not invented. Model/client calls are local; Ross KB uses the existing internal Docker network. Full physical Internet disconnection was **not tested**.
- CPU24 / context8192 / draft-MTP remains the documented explicit SAFE fallback. It is not a second resident model or silently selected fallback.

The existing model's recipe options were saved through Lemonade, not by editing the GPU/NPU stack. Current configured custom binaries remain under `output/M6/build-{cpu,vulkan,hip}/bin/`. These local build outputs are runtime prerequisites on this machine, not suitable to copy wholesale as new-machine deployment; use the rebuild guide on a new host.

## What actually passed

1. Earlier controlled Qwen engineering cohort: T1/T2/T3, Ross and Non-Ross, 18/18 PASS; RTL trials have independent synthesis and HLS trials have CSim/CSynth. This is prior evidence, not this turn's A/B benchmark.
2. Fresh formal-profile integration on 2026-10-15: local Qwen → genuine Ross Skill and local KB MCP → real XSim baseline failure → model-authored one-file RTL patch → unchanged testbench PASS. 320.158 seconds, one applied patch, two actual XSim executions. One preliminary blocked Ross-prerequisite request is not a third simulator run. Codex did not author the fix and is not a runtime dependency.
3. Fresh bounded graphics baseline acceptance: HIP/Vulkan 1,024 results each; XRT/firmware and strict VitisAI CNN, no CPU fallback and zero reference error. Existing Ubuntu Mesa/libdrm `.2` revisions accepted; no packages were modified.
4. Final bounded current software suite at 18:52:40–18:52:50.062535 +08:00: workstation GPU/NPU/tool/Ross checks, saved evidence, actual resident formal-model inference, HLS startup and kernel audit PASS. It borrows the resident model and never loads Qwen3.6 or a second large model.
5. M14 fail-closed behavior tested: protected mismatch exits before any timed workload. Runtime verifier rejects missing model, backend fallback, changed artifact metadata and incompatible offline settings.

[Formal integration evidence](M15/evidence/2026-10-15/formal-engineering-integration/), [final software summary](M15/evidence/2026-10-15/unified-software-validation/summary.json), [baseline decision](M15/GRAPHICS_BASELINE_ACCEPTANCE_2026-10-15.md).

One development-controller false negative is retained: the old benchmark `main()` requires six trials and returned 1 when deliberately asked for only B1, although B1's Local Agent exited 0 and the fixed XSim test passed. The controller conservatively restored CPU. The raw failure, exact trace and successful single-trial verification remain saved; the successful trial was not repeated. Only after independently checking the model patch and true PASS marker was the Vulkan profile saved. This is not a failed RTL/model trial or hidden retry.

## Normal checks

From `/home/shen/AI370-2`:

```bash
systemctl --user is-active lemond.service
python3 scripts/verify_local_agent_runtime.py --no-inference --output output/runtime-readiness.json
bash scripts/verify_m14_evidence.sh
```

The runtime command checks the resident ENGINEERING profile and prior full SHA256 record plus unchanged size/mtime, without pretending to perform a fresh whole-model rehash. Omit `--no-inference` for one four-token actual API smoke. It refuses absent/wrong-backend models before calling an API that might auto-load one.

Run `bash scripts/run_m15_final_validation.sh` only when an integrated bounded regression is needed. It executes small GPU/NPU checks, saved evidence and the resident model; it does not change profiles or program FPGA. It emits FAIL on the first failing gate and SOFTWARE_PASS_WITH_DEFERRED when applicable checks pass. Do not run old performance drivers as readiness checks: their historical preflight expects CPU8K and intentionally refuses the current formal Vulkan16K profile.

## Local Agent operation

Use `scripts/local_agent.py` directly, with the selected isolated workspace and task. Codex/OpenAI/cloud services are not needed by that runtime. Existing bounded profiles are `--xsim`, `--multi-file-xsim`, and `--hls`; supply the explicit editable source paths. These profiles require the known fixed validators/testbenches and do not grant arbitrary shell or unrestricted Vivado Tcl.

Enable Ross explicitly with `--ross-docsearch-url http://172.18.0.4:8080/mcp/doc-search`, and use the measured excerpt budgets `--ross-context-chars 1800 --ross-mcp-chars 1200`, `--max-completion-tokens 2048`. Recheck the actual internal KB endpoint after container/network recreation; do not substitute a cloud endpoint. Keep one large model and one engineering job active at a time. Reuse existing workspaces only as inputs to a new isolated copy, never edit M11/M12 Golden evidence.

The executed command, exact task/spec/seed, source patch and trace for the new formal-profile trial are preserved in the evidence link above. They are a reproducible bounded example, not permission to replace testbenches or weaken acceptance for new designs. For new work, explicitly configure validators before allowing the model to execute them.

## Actual remaining external/unverified items

- T7 remains on user hold; no media/Photos access occurred. Current local commits are not yet a verified on-media update. Deployment kit/offline package closure remains PARTIAL.
- Telegram credential file is absent (presence checked only; no secret read). Bot authentication/private pairing/phone delivery needs the user's BotFather token; existing controller remains available but E2E WAITING_USER.
- No separate compatible rebuild target has been exercised; full boot restore and clean-host rebuild remain NOT_TESTED. CP0 is historical pre-Vivado only. No 350 GB current-state archive or installed Xilinx-tree copy is required.
- Full host-disconnected licensed workflow, Vitis IDE/Embedded agent control and direct Qwen-driven Vivado Tcl MCP remain NOT_TESTED. The genuine KB MCP plus fixed local XSim/HLS tools are verified; do not conflate them with unrestricted MCP tool control.
- M7.1 remains OPEN for the retired Qwen3.6 case; do not replay it. M8 NPU LLM and further ROCm tuning remain DEFERRED. These do not prevent using supported local Qwen/Vulkan and verified CNN/FPGA workflows.

No new release/tag or GitHub push was made. A local current-main Git bundle can be prepared and clone-verified without T7, but that alone is not media/deployment readiness.
