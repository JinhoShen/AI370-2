# M13 AMD Ross Agentic AI — research and installation gate

Review date: 2026-10-01 (Asia/Taipei). Sources were checked against AMD's current Ross product and download pages. This document separates official claims from AI370-2 local verification.

## OFFICIAL CONFIRMED

- Ross is a client-agnostic agentic layer using MCP servers, an AMD Knowledge Base, Agent Skills and Design Examples.
- AMD lists compatible IDE/CLI clients including Codex CLI; this establishes compatibility as a product claim, not a local integration result.
- Ross requires the applicable Vivado/Vitis tool licenses but AMD states no additional Ross license is required.
- AMD's current FAQ states Vivado versions are supported generally and Vitis HLS 2025.2 or later is supported; this does not certify the AI370-2 host OS.
- AMD's download page lists Linux Vivado MCP server executables and a VS Code extension. The page requires AMD credential sign-in to download the MCP executables.
- AMD documents an offline/air-gapped direction: deploy the local knowledge database with an embedding model and MCP server, then use a compatible answer-generation model. This is an official setup description, not proof that this workstation or its existing Qwen GGUF is compatible.
- AMD describes a monthly Ross release cadence independent of Vivado/Vitis release cadence.

Sources (accessed 2026-10-01):

- https://www.amd.com/en/products/software/ross-agentic-ai.html
- https://www.amd.com/en/support/downloads/ross-agentic-ai.html

## AI370-2 local status

| Capability | Status | Evidence / boundary |
|---|---|---|
| Ross executable / version | BLOCKED / NOT INSTALLED | No Ross executable or installer is present in local resources or the installed Xilinx trees. |
| AMD download access | BLOCKED BY ACCOUNT GATE | Official download page requires AMD credential sign-in; no credential was requested or stored. |
| Basic startup / health | NOT TESTED | No local binary. |
| Codex CLI ↔ Ross | PLANNED / NOT TESTED | Official client compatibility does not prove a local MCP handshake. |
| Ross MCP | BLOCKED / NOT TESTED | Linux MCP binary is unavailable locally. |
| Vivado / Vitis / HLS integration | PLANNED / NOT TESTED | Existing tools are installed, but no Ross MCP has been connected. |
| Agent Skills / Knowledge Base | PLANNED / NOT TESTED | Public product description only; no local Ross package or skill provenance was verified. |
| Local / offline / air-gapped | UNKNOWN / NOT TESTED | Official route is documented, but no local database, embedding package or MCP deployment was executed. |

No Kernel, Mesa, ROCm, system XRT 2.21.75, amdxdna or NPU firmware change was made for M13. The M13 installation gate is isolated; M14 automation and M15 pre-final work may continue with Ross explicitly deferred.
