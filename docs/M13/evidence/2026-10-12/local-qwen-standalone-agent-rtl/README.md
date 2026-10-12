# Standalone Local Qwen Agent → RTL → XSim repair

**Result: VERIFIED bounded Local Agent workflow; behavioral RTL test PASS.** M13 overall remains IN PROGRESS.

On 2026-10-12, `scripts/local_agent.py` used the already-loaded Qwen3.8-27B-UD-Q4_K_XL through Lemonade's loopback chat-completions endpoint. No Codex CLI, OpenAI API, cloud model, arbitrary shell tool, FPGA hardware, or package installation participated. The only source edited was a disposable copy under ignored `output/M13/`; M11/M12 projects and the SP701 were not touched.

## What ran

The agent read the task and seeded AXI4-Lite RTL, then invoked only its fixed `bash ./run_validation.sh` XSim tool. The unchanged RTL compiled and elaborated, then the self-checking testbench failed as expected at 240 ns: actual `0x1336557c`, expected `0x1336597c`. The same Qwen received that real XSim output and proposed XOR-to-addition. Its first unified diff was syntactically invalid; `git apply --check` rejected it and made no source change. The agent returned the exact patch-check error to the same Qwen. Qwen then submitted the exact old and new RTL text through `apply_replacement`; the executor verified a unique match, generated a canonical one-file unified diff from those exact model-selected strings, checked and applied it. The executor did not choose or change the arithmetic expression.

The agent reran XSim. Attempt 2 emitted `TEST_PASS baseline_and_selected_mode=1` at 460 ns. The unchanged testbench covers legacy complement mode, addition with offset, switching back to legacy mode, and 32-bit wraparound. The CLI returned `status=PASS`, 2 XSim runs, 1 model-authored correction. No RTL synthesis, timing analysis, implementation, bitstream generation, programming, or physical hardware validation was part of this test.

## Model and host

- Model file: `resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- Lemonade API: `http://127.0.0.1:13305/api/v1/chat/completions`; Lemonade forwarded locally to `127.0.0.1:8001/v1`.
- Backend: CPU; llama.cpp reported 24 threads and 24 batch threads, context 8192, one slot, zero GPU layers. Host CPU is Ryzen AI 9 HX 370, 12 cores / 24 logical CPUs.
- The filename says Q4_K_XL; llama.cpp's returned GGUF metadata describes `Q4_K - Medium`. Both are recorded as observed rather than silently reconciled.
- The model was already loaded. This work downloaded no model and changed no inference backend or protected GPU/NPU/FPGA stack.

## Tool and resource boundary

`local_agent.py` accepts only a loopback HTTP model URL, disables environment proxies and refuses redirects. It offers bounded text-file discovery/read, one-file patch/replacement, and a small fixed command allowlist; it has no shell-command tool. It rejects traversal, symlinks, credentials, models, firmware/binaries, Git internals, output/resource roots, and M11/M12 evidence. XSim is a fixed runner with 3 maximum invocations, 2 maximum corrections, finite per-call and total timeouts, capped model response/file/patch sizes, and Bubblewrap read-only host mounts with only the selected workspace writable.

A separate Local Agent call used the same loaded Qwen and read a unique marker while the child-tool namespace had no network. A fixed subprocess probe in that Bubblewrap network-isolated namespace reported external connection failure (`errno=101`). The model endpoint remained loopback-only. The workstation itself was not physically disconnected from its network during this proof, so full host-disconnection behavior is **NOT TESTED**.

The Vivado FlexNet license is bound to the host NIC MAC. For the fixed XSim runner only, Bubblewrap retained the host network namespace so Vivado could see that identity. The model did not receive a network tool, and no external service was called. Thus the Local Agent's local inference/read-only tool path is offline-ready; a physically disconnected, licensed XSim invocation is not claimed.

## Checks and boundaries

- Local Agent policy tests: 4/4 PASS.
- Telegram controller policy tests: 4/4 PASS.
- Python bytecode compilation: PASS.
- Seeded testbench SHA256 matches the existing M13 oracle: `55ccf9c733802b60af8d8f6e94c0aaf9d8d67ddedbf4ae7b0748076e050759f1`.
- Telegram's source now launches this Local Agent directly and does not invoke Codex. Live Telegram delivery/pairing remains NOT TESTED / WAITING_USER because no BotFather token is configured.
- HLS/Vitis agent workflow, multi-file repair, fully disconnected host operation, and unrelated M15 unified regression remain NOT TESTED or DEFERRED.
- No Kernel, Mesa, libdrm, ROCm/HIP, XRT, amdxdna, NPU firmware, Vivado/Vitis installation, or license file was changed.

## Files

- `local-agent-trace.jsonl`: full Local Qwen function-call responses and executor feedback, including the actual baseline mismatch, rejected patch, exact model replacement, and result.
- `source/`: starting/final RTL, unchanged testbench, active task spec, source task-spec reference and fixed XSim runner.
- `runs/`: baseline and repaired `xvlog`, `xelab`, `xsim` output/journals.
- `offline/`: offline-mode marker cycle and network-isolation probe.
- `SHA256SUMS`: integrity manifest for retained evidence.
