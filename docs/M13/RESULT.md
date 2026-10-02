# M13 AMD Ross Agentic AI — status and validation

**Current status: IN PROGRESS — core Vivado MCP and local documentation search VERIFIED; full M13 is not PASS.**

Review date: 2026-10-02 (Asia/Taipei). This result distinguishes AMD-published product statements from AI370-2 execution. Detailed local evidence is in [`evidence/2026-10-02/ROSS_M13_VALIDATION.md`](evidence/2026-10-02/ROSS_M13_VALIDATION.md).

## OFFICIAL CONFIRMED

- Ross is a client-agnostic agentic layer using MCP servers, an AMD Knowledge Base, Agent Skills and Design Examples.
- AMD lists compatible IDE/CLI clients including Codex CLI; this is a product claim, while local Codex integration is separately tested below.
- AMD says Ross itself needs no additional license; applicable Vivado/Vitis tool licenses remain necessary.
- AMD lists Linux MCP server and VS Code extension downloads. The AMD account requirement was encountered during the earlier download attempt; the user subsequently supplied the local artifacts.
- AMD documents an offline Knowledge Base deployment with a local embedding model, vector database and MCP server. The answer-generation model is a separate component and must also be local for an end-to-end air-gapped agent workflow.
- AMD's bundled 2026.9.1 extension says Vitis HLS skills can guide `v++` / `vitis-run` workflows without a separate HLS MCP server. That does not establish a tested AI370-2 Vitis/HLS agent operation.
- Official product/download sources reviewed on 2026-10-01: [Ross product page](https://www.amd.com/en/products/software/ross-agentic-ai.html), [Ross downloads](https://www.amd.com/en/support/downloads/ross-agentic-ai.html), [AMD Ross Assistant documentation and skills](https://github.com/Xilinx/ross-ai-assistant). The installed 2026.9.1 extension and its bundled local-KB deployment guide were inspected on 2026-10-02.

## Historical gate — 2026-10-01

The earlier M13 checkpoint recorded Ross as not installed because the AMD Linux MCP download required AMD account sign-in and no local MCP artifact was present then. That was the state at that checkpoint; the user later downloaded the files into `resources/ROSS`, so the download gate is now cleared. The original dated research and gate are retained in Git history.

## AI370-2 local status

| Capability | Status | Evidence / boundary |
|---|---|---|
| Vivado MCP binary / version | INSTALLED / VERIFIED | AMD 2026.9.1 customer-channel Linux binary; SHA-256 and `--version` recorded in dated evidence. |
| VS Code Vivado AI extension | INSTALLED | AMD `vivado-ai-extension` 2026.9.1 is installed in VS Code 1.139.1. Extension-host activation and Copilot Chat UI were not tested in the active editor window. |
| AMD Ross Codex Agent Skills | INSTALLED / VERIFIED | Codex plugin `amd-ross-agentic-ai-assistant` 2026.9.1 is enabled; cache contains 49 `SKILL.md` files. The HLS synthesis-report skill is present. A live HLS skill execution is NOT TESTED. |
| Vivado MCP startup / discovery | PASS | Native stdio MCP initialize and `tools/list` passed; 13 tools discovered without invoking a design-changing tool. |
| Codex CLI ↔ AMD doc-search MCP | PASS | Fresh ephemeral Codex CLI session invoked `vivado_doc_search`; it returned AMD UG835 `report_timing_summary` content and source URL. |
| Vivado 2026.1 integration | PASS — bounded read-only smoke | MCP started Vivado in a new `/tmp` directory; `version` returned Vivado 2026.1, and `get_parts` recognized `xc7s100fgga676-2`; session closed. No synthesis, project modification or hardware action. |
| Vitis Unified / Vitis Embedded integration | NOT TESTED | Ross docs/skills are present, but no Vitis Unified IDE or Embedded workflow was driven through the assistant. M10 software validation remains separate evidence. |
| Vitis HLS agent workflow | NOT TESTED | HLS Agent Skills are installed. The attempt to have Codex CLI inspect/use the skill was blocked by its local `bwrap` sandbox setup (`RTM_NEWADDR` failure); no HLS command was run through Ross. Existing M10 HLS PASS is not relabeled as Ross integration. |
| Local Knowledge Base package | INSTALLED / VERIFIED | AMD package build 20260918 with Qwen3-Embedding-0.6B, preloaded llama.cpp/MCP/Weaviate/snapshot images; archive hash, versions and import result are recorded in evidence. |
| Local document retrieval | PASS | CPU embedding service loaded the packaged Qwen embedding model; Weaviate import completed 725,911/725,911 records; AMD `vivado_doc_search` returned documentation through both direct MCP and Codex CLI. |
| Retrieval container network | VERIFIED — isolated Docker network | All KB containers use a Docker `internal=true` bridge; container memory/CPU limits are configured and the MCP endpoint is reached from the host over the bridge. The configured host port is not actually published on this internal network; current Codex URL uses the live container address `172.18.0.4:8080`. Recheck the address after network/container recreation. |
| End-to-end local answering / air-gapped agent | DEFERRED / NOT TESTED | The local Codex config selects `gpt-6-luna`; the KB retrieval layer is local and network-isolated, but no local answer-generation model was attached. No claim that the overall agent workflow is air-gapped or that an existing Qwen GGUF is supported. |
| Controlled SP701 engineering workflow | PARTIAL / VERIFIED bounded local-KB-assisted workflow | The configured Ross Local Knowledge Base materially informed M12's JTAG-to-AXI architecture and Tcl transaction procedure; the resulting design was programmed and four physical transactions passed. Evidence: [`M13_M12_LOCAL_ENGINEERING_WORKFLOW.md`](evidence/2026-10-02/M13_M12_LOCAL_ENGINEERING_WORKFLOW.md). Vivado batch Tcl performed build/program/transactions; the Vivado MCP did not control these hardware actions. |

No Kernel, Mesa/RADV, libdrm, ROCm/HIP, system XRT 2.21.75, amdxdna DKMS, NPU firmware or FPGA software stack package was changed for Ross. The only APT transaction was 7 new Docker/container-runtime packages with 0 upgrades; the user was not added to the `docker` group. The local KB containers run CPU-only; no GPU/NPU inference was invoked. Docker's `.env` contains generated credentials and remains outside Git with mode 0600.

## Remaining M13 work

1. Exercise a Ross HLS skill with a disposable HLS component and verify its report output, without conflating it with prior M10 evidence.
2. Validate Vitis/Vitis Embedded assistant workflow boundaries; Ross MCP is Vivado-specific in the installed package, while HLS support is skill/CLI-driven.
3. Evaluate a separate local answer-generation model only after choosing a bounded, stable CPU workload; do not assume Qwen GGUF compatibility from the embedding package.
4. Verify end-to-end air-gap behavior for both the answer model and client. The current result establishes an isolated local retrieval backend only.
5. The bounded M12 local-KB-assisted JTAG-to-AXI engineering workflow is now VERIFIED as one M13 workflow result. Vivado MCP-driven hardware control, application-facing deployed transport, Ross HLS/Vitis skill execution and full local/air-gapped agent behavior remain DEFERRED / NOT TESTED.

M13 remains **IN PROGRESS**, not PASS. No changes were made to the protected GPU/NPU stack, and M7.1 remains OPEN.
