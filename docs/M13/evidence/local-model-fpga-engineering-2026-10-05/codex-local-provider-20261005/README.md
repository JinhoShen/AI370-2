# Codex ↔ local Qwen provider smoke

**Date:** 2026-10-05 (Asia/Taipei)
**Verdict:** Local Codex text-response path PASS. Codex dispatched a standard `exec_command` function call, but Bubblewrap failed before running the read-only command; the tool execution result is BLOCKED. This is not an air-gap PASS.

## Setup

- Model: `resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf`
- llama.cpp server: M6 CPU build, version `0.5.0-dev`, commit `7fe450e19305b828c199d602c23a8337aaa1f03b`
- Codex CLI: `0.159.2`
- Backend: CPU only (`--n-gpu-layers 0`); host `127.0.0.1` only; port `18080`
- Context: 8,192 tokens; generation/prompt threads: 24 (not capped at four)
- Resource guard: transient user systemd service, `MemoryMax=30G`, `MemorySwapMax=0`, `RuntimeMaxSec=900`; no persistent service/configuration was installed
- Codex configuration: isolated temporary `CODEX_HOME`, custom provider uses `wire_api="responses"`, `requires_openai_auth=false`; OpenAI key/base URL variables were unset for the process. The normal Codex user configuration was not changed.

## Results

1. `/health` returned HTTP 200 and `/v1/models` identified the loaded alias. Codex first rejected the 4,096-token setting because its request contained 6,124 tokens. With the server and isolated Codex profile set to 8,192 tokens, Codex completed a response with the exact expected text `AI370_LOCAL_RESPONSES_OK` (6,182 input tokens; 48 output tokens). See `response-context-4k-failure.jsonl`, `response-context-8k.jsonl`, and `response-context-8k-retry.jsonl`.
2. A direct local `/v1/responses` request using a standard `function` tool schema returned HTTP 200 and one `function_call` with the requested tool name and validated JSON arguments. The response is retained in `function-tool-response.json` without model reasoning text.
3. The captured Codex tool schema used standard function entries for `exec_command` and other primary tools, plus a `multi_agent_v1` namespace and `web_search`. llama.cpp skipped the latter two types. Qwen selected the standard `exec_command` tool; Codex returned `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` as the tool result, and the model relayed that error. The requested `cat` did not execute, so read-only tool execution is BLOCKED by the host sandbox runtime. No full-access fallback was attempted. A user-level systemd egress-filter probe also could not start because the user service manager cannot configure its IP firewall; no alternative sandbox was installed.
4. The service was stopped after testing and its loopback listener disappeared. Service statistics are recorded alongside each run; no systemd service remains. The 30 GiB/zero-swap guard and 24-thread setting are the recorded controls. A service memory peak is not used as a model-RSS benchmark.
5. No GPU, NPU, FPGA, kernel or protected-stack operation was performed. No system-wide network-isolation/packet audit was performed; do not describe the Codex path as air-gapped.

## Reproduction

The temporary Codex profile is retained as `config.toml`. The transient server command was:

```sh
systemd-run --user --unit=ai370-local-qwen-codex-20261005 --collect \
  --property=MemoryMax=30G --property=MemorySwapMax=0 \
  --property=RuntimeMaxSec=900 --property=Restart=no \
  /home/shen/AI370-2/output/M6/build-cpu/bin/llama-server \
  --host 127.0.0.1 --port 18080 \
  --model /home/shen/AI370-2/resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf \
  --alias qwen3.8-local --ctx-size 8192 --threads 24 --threads-batch 24 \
  --parallel 1 --n-gpu-layers 0 --no-webui
```

The config/API transcript and server log are retained alongside this report. An isolated Codex `/tmp` directory was used for the response call; there were no writable project files in that workspace.
