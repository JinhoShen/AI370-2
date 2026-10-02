# M14 read-only evidence audit — 2026-10-02 15:29:15 +08:00

`summary.json` is the machine-readable result. The audit exited successfully with zero failures and PASS_WITH_DEFERRED. It validated M11–M13 evidence hashes, the M12 clean software rebuild (including routed DRC/timing and bitstream build transcript), APT guard unit/simulation evidence, and current protected package/module versions. It did not program the FPGA or run GPU, Vulkan, NPU, or LLM workloads. See the checks and logs for the exact deferred/not-tested scope.
