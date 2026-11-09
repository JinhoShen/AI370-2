# V1 Pilot remediation

V1 completed on 2026-10-29 with 72 recorded samples: 11 `PASS`, 52 `FAIL`, and 9 `BLOCKED`. The original artifacts remain authoritative for that run and must not be rewritten.

## Evidence-based findings

| Finding | Samples | Interpretation |
|---|---:|---|
| Bounded 14-turn limit | 24 | The agent spent its allowed interaction budget without verified validation PASS. |
| Malformed/truncated tool-call JSON | 11 | The server rejected a generated patch call before the executor could evaluate it. |
| Chat-template role error | 6 | The provider rejected a post-tool request because the conversation included a new user turn after tool results. |
| Model request timeout | 3 | The local provider did not reply inside the fixed request deadline. |
| Model stopped before validation PASS | 8 | The model ended its response without a verified repaired design. |
| Ross endpoint unavailable | 9 | Every T7 sample was consistently `BLOCKED`; no substitute documentation source was used. |

The 44 tool-turn, provider-protocol, or timeout failures are not valid evidence that the model could not solve the FPGA task. The eight no-PASS failures remain model-task outcomes unless a later harness investigation proves otherwise.

## Remediation applied after V1

1. The quality agent now exposes `apply_replacement`, which its prompt had already instructed the model to use after a rejected unified diff.
2. Exact source replacement accepts up to 24 KiB instead of 4 KiB, while still requiring one exact allowed source match and preserving the executor's validation rules.
3. Model completion allowance is 8,192 tokens. This prevents a long source repair from being truncated midway through the tool JSON.
4. Correction feedback no longer appends a user message after tool responses. It remains in the system guidance and tool output, preserving evidence while avoiding the observed GGUF chat-template role constraint.

No acceptance threshold, validator, corpus asset, production Agent setting, or V1 result was changed.

## Required next execution

Freeze a new harness identity and record its hashes before any V2/V3 execution. First run a non-scored fixture matrix that exercises: baseline failure, a long exact replacement, malformed diff recovery, and a multi-turn tool continuation for every candidate chat template. T7 remains `BLOCKED` until its local Ross MCP endpoint is available.
