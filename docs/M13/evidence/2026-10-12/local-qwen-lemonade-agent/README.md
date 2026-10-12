# 2026-10-12 Local Qwen and Agent readiness

This is a bounded CPU-only availability check. It does not replace the earlier Q4_K_XL FPGA engineering and XSim feedback evidence, and it does not exercise write-capable autonomy.

## Platform and resource policy

- Host: AMD Ryzen AI 9 HX 370, 12 physical CPU cores / 24 logical CPUs.
- User-provided installed memory specification: 64 GB. Linux reports `MemTotal=48,928,804 kB` (about 46.7 GiB usable by host processes); Radeon 890M reports a 16 GiB UMA/VRAM budget. These figures describe host-visible and GPU-visible memory views and must not be added together as separate installed RAM.
- Lemonade user service is active on its configured port 13305. `CPUQuotaPerSecUSec=infinity`, `MemoryMax=infinity`, `MemorySwapMax=0` were read from the active unit after restart. The prior 24 GiB / 800% CPU fixed ceilings were removed from its persistent resource drop-in. The exact final drop-in is `lemond-resource-guard.final.conf` in this evidence directory.
- No Kernel, GPU, NPU, FPGA, ROCm, Mesa, XRT, amdxdna, firmware, or model build configuration was changed.

## Lemonade API and Qwen inference

The earlier 09:53 health check probed common default ports, while this host's configured Lemonade API uses port 13305. The correct local endpoint was queried and returned HTTP 200 with `status=ok`, Lemonade `2026.39.1`. The API reports no model loaded after the smoke was unloaded.

In this execution, Qwen3.8-27B-UD-Q4_K_M was loaded with Lemonade on CPU at context 128, 24 threads, zero GPU layers; a two-token bounded Chat Completions request returned HTTP 200 and `READY` (about 1.8 seconds). No GPU/NPU inference or benchmark was run. The API health response is retained in `lemonade-health.json`.

## Local Agent tool cycle

The same Qwen3.8-27B-UD-Q4_K_M file was served CPU-only by the existing llama.cpp build with context 8192, 24 threads, one parallel slot, and zero GPU layers. A temporary Codex home selected that loopback Responses provider. Codex received a unique marker-only task, invoked `exec_command` exactly once to read `marker.txt` in a disposable read-only workspace, then returned the exact marker text. The tool result and model response match; Codex and the command both exited 0. Full JSON events are in `codex-events.jsonl`; prompt/provider config, marker and stderr are adjacent.

The first response stream emitted a reconnect message after an idle timeout, then completed successfully in the same turn. Codex also emitted its nonfatal fallback-metadata notice for the local alias. These are recorded caveats; they did not change the tool result or exit status.

This proves one bounded local model → Codex → read-only tool → tool result → local model response cycle. It does not prove write authorization, multi-step autonomous repair, complete network isolation, or Telegram E2E.

## FPGA tools, license, Telegram

Vivado and Vitis 2026.1 version checks passed in the 09:53 health run. Vitis HLS was invoked with its installed 2026.1 environment, Tcl/data/library paths and Vitis working directory; `vitis_hls -version` returned v2026.1 / SW build 6493734, exit 0. This version check did not request a license checkout or run synthesis. License-unlocked Vivado RTL and HLS synthesis PASS remain historical evidence in `docs/M9/LICENSE_UNLOCKED_VALIDATION.md`.

The Telegram controller is installed but its service is inactive and the BotFather credential is not provisioned. Credential values were not read or copied. Telegram E2E remains `WAITING_USER` / `NOT_TESTED`.

## Exact bounded local Agent task

```text
Use exec_command exactly once to run `cat marker.txt` in the current workspace. Do not run any other command. Do not modify files. Then state the exact marker text returned by the tool and nothing else.
```

Expected and observed marker: `AI370_LOCAL_AGENT_HEALTH_20261012_0953`.
