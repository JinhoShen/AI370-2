# Local Qwen3.8 → Codex sandbox tool-loop smoke

**Date:** 2026-10-06 (Asia/Taipei)

**Verdict:** `PASS` for one bounded local-model tool cycle: local Qwen selected a standard `exec_command`, Codex executed it in `read-only` sandbox, and the model reported the tool's exact result. This is not a source-edit, Vivado, hardware, or full air-gap test.

## Setup and guardrails

- Model: Qwen3.8-27B-UD-Q4_K_XL, Q4_K_XL, using the existing llama.cpp CPU build (`0.5.0-dev`, commit `7fe450e19305b828c199d602c23a8337aaa1f03b`).
- Endpoint: `127.0.0.1:18080`; Codex CLI `0.159.2`; isolated temporary `CODEX_HOME`; no API key or external provider configured.
- Context 8,192; 24 CPU threads; `MemoryMax=30G`; `MemorySwapMax=0`; transient service `RuntimeMaxSec=900`.
- Codex execution sandbox: `read-only`; temporary workspace under `/tmp`; no Vivado invocation, FPGA programming, GPU/NPU inference, package/configuration change, or protected-stack change.
- The model received one instruction: use `exec_command` exactly once to read `marker.txt`, then report its exact output.

## Actual result

Codex's transcript records the executed command `cat marker.txt`, exit status 0, and output `AI370_LOCAL_TOOL_RESULT_20261006_91af`. Qwen's final answer reproduced that exact value and explicitly attributed it to the tool result. The marker is preserved in `tool-marker.txt`; the exact Codex response and execution transcript are in `codex-output.txt` and `codex-stderr.log`.

llama.cpp processed the 5,700-token request without truncation. Startup and model service completed successfully; the Codex invocation exited 0. The first Codex attempt had a 150-second timeout and ended before the large tool prompt completed; it is retained under `attempts/01-short-timeout/`. An earlier health-check attempt used absent `curl`, was stopped, and is documented under `attempts/00-invalid-health-check/`. Neither is classified as a model or sandbox failure.

The AppArmor-scoped Bubblewrap profile permitted the read-only command. Global AppArmor and `kernel.apparmor_restrict_unprivileged_userns` were not disabled. The successful read-only invocation did not require Vivado's host-network license exception.

## Boundary

This verifies the local Responses provider's standard Codex function-tool cycle for one read-only command. It does not establish write-capable model autonomy, error-driven self-repair, Vivado/Vitis agent tool orchestration in the same Codex session, or system-wide air-gap behavior. The separate supervised Qwen-authored RTL patch → Codex-reviewed application → XSim/Vivado synthesis result remains the evidence for the engineering edit flow.

No secret, license data, or MAC address is included. The model endpoint was loopback-only; no network packet audit was performed.
