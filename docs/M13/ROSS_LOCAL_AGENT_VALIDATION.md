# Ross + Local Qwen Agent validation

**Overall result: PARTIAL.** This file records only exercised behavior. The existing Non-Ross RTL repair PASS from commit `345a54c` is a prior reference result, not a benchmark sample.

## Implemented integration

`scripts/local_agent.py` remains the single agent framework. Without an explicit Ross endpoint, its tool schema contains no Ross Skill or MCP calls. With `--ross-docsearch-url` (or `AI370_ROSS_DOCSEARCH_URL`), it adds two constrained tools:

- `ross_skill_read` returns selected, copied AMD 2026.9.1 Skill text and one selected local reference. It cannot execute Skill-bundled code.
- `ross_doc_search` speaks the real MCP streamable-HTTP protocol to the AMD local Doc Search endpoint: initialize, enumerate tools, verify the `AMD Doc Search` server identity and read-only hint, then call `vivado_doc_search`. The URL must be the exact `/mcp/doc-search` path and resolve only to loopback or a private RFC1918 address. HTTP redirects and proxies are disabled; response size and request time are bounded. No remote Vivado MCP `vivado_doc_search` is used.

The Local Agent still offers no shell-command tool. XSim remains a fixed runner in a Bubblewrap workspace with host files read-only and only the trial workspace writable. Vivado Tcl execution, FPGA programming, M11/M12 project access, protected-stack changes, arbitrary URL fetches and cloud model URLs remain outside the tool policy. Codex does not execute, relay, or authorize Local Agent tool calls.

## Installed interface checks

- `/home/shen/.local/bin/vivado-mcp-server-2026.9.1 --version` returned `vivado-mcp-server 2026.9.1`.
- Direct stdio MCP `initialize` returned server `vivado-mcp-server` version `2026.9.1`; `tools/list` returned 13 tools. The Qwen agent is intentionally not granted its unrestricted `vivado_execute` Tcl interface.
- The local AMD Doc Search MCP returned server `AMD Doc Search` version `0.11.0`; `tools/list` exposed `vivado_doc_search` with `readOnlyHint=true`. A real local MCP search returned AMD XSim/Vivado 2026.1 documentation.
- No dedicated Vitis/HLS MCP was found. The Local Agent now exposes a bounded fixed HLS CSim/CSynth validator under explicit `--hls`; its T3 Local Qwen/Ross source-repair cohort is verified. Vitis Unified/Embedded IDE operation remains untested.

## RTL Local Agent baseline (not the A/B data)

The pre-existing bounded test committed at `345a54c` used Qwen3.8-27B-UD-Q4_K_XL on CPU through Lemonade. The model read the AXI-Lite spec and RTL, observed baseline XSim actual `0x1336557c` versus expected `0x1336597c`, submitted a malformed diff that the executor rejected without modifying source, then supplied exact old/new RTL text. The executor formatted only those model-selected strings into a canonical one-file patch. The same model read the patch error and the unchanged testbench passed after the repair. This is **Non-Ross reference evidence**, not one of the controlled A/B repetitions.

## Controlled comparison status

See [`M13_ROSS_AB_BENCHMARK_REPORT.md`](M13_ROSS_AB_BENCHMARK_REPORT.md). The T1 runner uses fresh copies of the exact same baseline files and the interleaved order A1 → B1 → B2 → A2 → A3 → B3. A uses the same model/agent/XSim policy without Ross tools; B explicitly exposes the installed Skills and actual local MCP call. Each trial gets a fresh workspace, fixed timeout and retry policy. A trial whose child inherited Ross endpoint configuration was stopped before XSim and retained separately as invalid setup evidence; it is excluded from all metrics. The corrected runner removes that endpoint from A's child environment.

Resource capture observes Qwen plus trial process RSS, host minimum available RAM, host swap use and process CPU. Dynamic guard: stop a trial if available RAM falls below `max(6 GiB, 12.5% of detected RAM)` or host swap use rises by more than 2 GiB during that run. CPU threads are not capped at four; the existing Qwen CPU backend is configured for 24 inference and batch threads.


## Completed controlled trial results (2026-10-12/13)

The T1, T2, and T3 controlled/exploratory results supersede the earlier live-progress wording above; historical baseline notes remain applicable. See [`M13_ROSS_AB_BENCHMARK_REPORT.md`](M13_ROSS_AB_BENCHMARK_REPORT.md) for per-trial tables and interpretation.

- **T1 basic RTL:** Non-Ross 3/3 PASS; Ross 0/3 PASS. All Ross trials made the required real Skill and local MCP calls, but did not produce a repair. No Ross completion-time comparison is valid.
- **T2 multi-file RTL:** Initial T2-v5 cohort Non-Ross 2/3, Ross 0/3. The later corrected controlled cohort passed Non-Ross 3/3 and Ross 1/3. Corrected Ross B1 made actual Skill/MCP calls and passed the unchanged XSim test after Qwen supplied a valid patch; B2/B3 failed at the 8192-token context ceiling. Earlier v6/v7 runs remain exploratory and are not pooled.
- **T3 HLS source validation:** Non-Ross 3/3 and Ross 3/3 PASS through fixed Vitis HLS C simulation/C synthesis checks. Mean time was 507.941 s vs 521.613 s respectively (Ross 2.69% slower). This does not establish implementation/timing/FPGA hardware validation.
- **Resource/safety:** Existing local model only, CPU with 24 threads; no GPU/NPU stress, FPGA programming, system stack change, arbitrary shell, or Golden project edit. Per-run RSS, MemAvailable, swap and trace data are captured in the raw ledgers.

**Current verdict: PARTIAL.** Genuine Ross Skill + local Knowledge Base MCP integration with local Qwen is VERIFIED; one of three corrected Ross T2 RTL trials and all three Ross T3 HLS source-validation trials passed. T1 Ross repair passed 0/3; corrected T2 passed 1/3 versus Non-Ross 3/3. Full offline/air-gapped behavior and Qwen-driven Vivado Tcl MCP integration remain NOT_TESTED. Codex is not part of the Local Agent runtime.
