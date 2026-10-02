# Ross M13 validation evidence — 2026-10-02

Host-local checks performed 2026-10-02 (Asia/Taipei). This record contains no account credentials, license data, model weights or container `.env` values.

## Artifacts and installation

| Artifact | Exact bytes | SHA-256 | Result |
|---|---:|---|---|
| `resources/ROSS/vivado-mcp-server-linux-amd64-2026.9.1` | 23,998,648 | `2d1ac42f2628dab2db37bd214b4ad45d2275e541fe6eb71e879ac6ea123bb8bc` | Installed as `~/.local/bin/vivado-mcp-server-2026.9.1`; ELF x86-64, statically linked. |
| `resources/ROSS/vivado-ai-extension-2026.9.1.vsix` | 29,383,058 | `7413dfc4b20597c0a545350a42c97326612fda93dd75cb627c85998ec8f613a9` | VS Code extension installed; reports `amd.vivado-ai-extension@2026.9.1`. |
| `resources/ROSS/20260918.qwen3-embedding-0.6b.tar.gz` | 4,440,996,408 | `567138f789b4ae131d6cea5b1bf482314939a963bd729fa5b50502262aba76dc` | Extracted and deployed as AMD local doc-search build 20260918. |
| `resources/ROSS/20260918.embeddinggemma-300m.tar.gz` | 3,161,656,726 | `7e391663346bc6f91f93ffdca8e844d833c39cdeea7dfd59aabc6c9761410ab5` | Present but not extracted or deployed. |

Vivado MCP `--version` returned `vivado-mcp-server 2026.9.1`, commit `2c4e86e5`, built 2026-09-29, channel `customer`. Its standalone MCP initialize negotiated protocol `2025-06-18`; `tools/list` returned 13 tools. The server is configured in Codex at global scope with `--stdio`, which avoids starting its shared HTTP daemon.

The 2026.9.1 plugin was registered in Codex as `amd-ross-agentic-ai-assistant@amd-ross-agentic-ai-assistant`, installed and enabled from the local VSIX-bundled package at `~/.local/share/amd-ross/2026.9.1`. The installed cache contains 49 skill files. VS Code reports version 1.139.1; extension-host activation was not tested.

## Vivado MCP bounded smoke

The Vivado MCP started `/home/shen/tools/Xilinx/2026.1/2026.1/Vivado/bin/vivado` in TCL mode with `external=false` and working directory `/tmp/ross-m13-vivado-smoke`.

- `version`: exit 0; Vivado v2026.1, SW build 6511674.
- `get_parts -filter {NAME == xc7s100fgga676-2}`: exit 0; returned `xc7s100fgga676-2`.
- `vivado_stop`: success; Vivado process exited.
- No synthesis, source/project modification, bitstream generation, Hardware Manager or JTAG action occurred.

## Codex and AMD doc-search MCP

Codex CLI 0.159.2 was launched with `--ephemeral --sandbox read-only`. Its JSON event log `/tmp/ross-codex-mcp-smoke.jsonl` contains an actual call to server `amd-embedded-doc-search`, tool `vivado_doc_search`. The call returned, among other results, AMD's *Vivado Design Suite Tcl Command Reference Guide (UG835)* at:

`https://docs.amd.com/r/en-US/ug835-vivado-tcl-commands/report_timing_summary`

The user Codex config selected model `gpt-6-luna`; no local provider was configured for this smoke. This is evidence of MCP client integration and local retrieval, not an air-gapped end-to-end agent.

## Offline/local Knowledge Base deployment

AMD's Qwen embedding archive contains the local `amd-embedded-doc-search` CLI, Qwen3-Embedding-0.6B GGUF, llama.cpp server image, AMD doc-search MCP image, Weaviate image and dated document snapshot. The extracted runtime is under `~/.local/share/amd-ross/offline-qwen3-20260918`; user configuration is under `~/.config/amd-embedded-doc-search-shen`. The `.env` file is mode 0600 and is intentionally excluded from Git.

The CLI loaded the prebundled images; no registry pull was needed. Docker packages installed from Ubuntu archive were `docker.io 29.1.3-0ubuntu3~24.04.2`, `docker-compose-v2 2.40.3+ds1-0ubuntu1~24.04.1`, `containerd 2.2.1-0ubuntu1~24.04.3`, `runc 1.3.4-0ubuntu1~24.04.1`, `bridge-utils 1.7.1-1ubuntu2`, `pigz 2.8-1` and `ubuntu-fan 0.12.16+24.04.1`: 7 newly installed, 0 upgraded, 0 removed. The `docker` group exists, but the user was not added to it; a one-command supplementary-group drop was used to access the socket.

The generated compose file was resource-guarded and made host/network-local before startup:

- llama.cpp embedding service: CPU-only, 4 CPU / 6 GiB limit, context 4096;
- Weaviate: 6 CPU / 14 GiB limit;
- document importer: 4 CPU / 8 GiB limit;
- MCP service: 1 GiB limit;
- Docker bridge: `internal=true` (no external container route);
- configured MCP host endpoint: loopback `127.0.0.1:18081`.

Docker does not publish the configured host port on this internal network (`docker inspect` reports a null network port mapping), so the working Codex MCP URL uses the host-reachable bridge address `http://172.18.0.4:8080/mcp/doc-search`. The address should be rechecked if the Docker network/container is recreated. The containers remain isolated from external network routes; the Codex client itself was not air-gapped.

Importer container `amd-embedded-doc-search-shen-weaviate-docs-import-1` exited 0 at 2026-10-02 10:03:47 (Asia/Taipei), reporting 725,911/725,911 records imported. At the final check, llama.cpp, Weaviate and MCP containers were running; llama.cpp reported its model loaded, Weaviate was healthy, and the doc-search request succeeded. Import peak observation was about 24% host RAM for Weaviate and about 34 GiB available host memory; no container was OOM-killed. The short kernel audit found no new amdgpu/DRM/TTM/soft-lockup errors.

The Qwen model above is the **embedding model** for retrieval, not the answer-generation model. No local answer-generation GGUF was attached, and no GPU/NPU inference was run.

## Protected stack and repository boundary

The APT simulation and transaction showed 0 upgrades. Post-install versions remained Mesa Vulkan `25.2.8-0ubuntu0.24.04.1`, libdrm amdgpu `2.4.125-1ubuntu0.1~24.04.1`, ROCm core `7.2.1.70201-81~24.04`, system XRT base/NPU `2.21.75`, and amdxdna DKMS `2.21.260102.53.release` for kernel `6.17.0-14-generic`. No Kernel, Mesa/RADV, libdrm, ROCm/HIP, XRT, amdxdna, NPU firmware or FPGA tool package change was part of M13. Resource archives, installed package cache, container images, and `.env` were not added to Git.

## Deferred / not tested

- Live HLS Agent Skill operation; a Codex CLI file-read attempt was blocked by the CLI's local bubblewrap setup error `RTM_NEWADDR`; no HLS command ran through Ross.
- Vitis Unified / Vitis Embedded assistant-driven operation.
- Extension activation in the current VS Code window and Copilot Chat UI.
- Local answer-generation model inference and full end-to-end air-gapped chat.
- Physical SP701/JTAG, hardware programming or FPGA execution.
- Long-duration Knowledge Base load or broader kernel stability.
