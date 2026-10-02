# M15 Final Golden Workstation — pre-final validation

**Status: PRE-FINAL.** The single unified software regression completed with PASS results for its tested workloads and explicit OPEN/DEFERRED items. **M15 is not FINAL GOLDEN and the project is not complete**: the current-state recovery checkpoint is blocked by local storage capacity, and off-device media is not mounted. Earlier CP0 is a pre-Vivado checkpoint and is not represented as the current workstation state.

Run: 2026-10-02 15:47:26–15:49:22 +08:00, followed by metadata-parser correction and removal of the temporary broad sudo rule. Evidence is under [`evidence/2026-10-02/unified-final-validation/`](evidence/2026-10-02/unified-final-validation/). The reproducible entry point is [`scripts/run_m15_final_validation.sh`](../../scripts/run_m15_final_validation.sh). It runs the guarded workstation verifier, records local GGUF integrity/metadata, and performs only bounded inference with the established M7 model. It does not program the FPGA or rerun the known Qwen3.6 Q8 Vulkan failure.

## Unified regression results

| Area | Result | Scope and evidence |
|---|---|---|
| Platform / protected stack | PASS | Ubuntu 24.04.4, kernel 6.17.0-14.14~24.04.1. Before/after package versions match: Mesa 25.2.8, libdrm 2.4.125, ROCm/HIP 7.2.1/7.2.53211, XRT 2.21.75, amdxdna 2.21.260102.53.release, XDNA2 firmware 1.1.2.64. No protected stack changes. |
| HIP / Radeon 890M | PASS | Strict 1,024-result HIP compute regression; gfx1150. |
| Vulkan / RADV | PASS | Strict 1,024-result shader regression; CPU fallback forbidden. |
| XRT / XDNA2 / NPU | PASS | XRT/NPU/firmware enumeration passed. Strict VitisAI CNN regression passed with CPU fallback disabled, positive NPU hardware-time delta and zero CPU-reference output error. |
| Local LLM selected M7 model | PASS — bounded smoke | CPU, Vulkan and ROCm each loaded the recorded M7 Qwen3.6-35B-A3B IQ2_M file at context 32, with at most four generated tokens and one GPU layer. Logs show backend-specific allocation (CPU mapped 11,108.63 MiB; Vulkan0 333.45 MiB plus Vulkan host 10,775.78 MiB; ROCm0 333.45 MiB plus ROCm host 10,775.19 MiB) and generation completion. This is not a benchmark or high-load stability claim. |
| GGUF inventory | PASS — integrity/metadata only | Seven local resource GGUF files, including three Qwen3.8 candidates and one mmproj, have full-file SHA256 and parseable metadata/tensor descriptors. The Qwen3.6 Q8 SHA matches the recorded `d8d784…c7361`. Full hashes, exact sizes, mtimes, metadata and tensor counts are in `models/model-summary.tsv` and adjacent evidence. Qwen3-14B is absent. Qwen3.8 inference was NOT TESTED by prior scope. |
| Qwen3.6 Q8 Vulkan | OPEN — not rerun | The earlier bounded attempt already produced RADV command-submission memory errors and Vulkan device loss. Replaying a known GPU/kernel error is unsafe; the issue remains OPEN. Its ROCm inference remains NOT TESTED, and Q8 CPU was not duplicated because the existing M7 CPU PASS is retained. |
| Vivado / Vitis / HLS | PASS — software scope | Vivado, `v++`, `platforminfo`, and `vitis-run` 2026.1 startup/version checks passed. M9/M10 RTL/HLS and M13 Ross HLS C-simulation/synthesis/report evidence remains intact. |
| SP701 physical | PASS — existing bounded evidence | M11 official MIG DDR3 test is PASS for its measured 16 MiB range; M12 physical JTAG-to-AXI four-vector roundtrip is PASS. M15 did not program the FPGA or rerun DDR. The new M12 clean software rebuild is separately documented in M14. |
| Ross | PASS — readiness scope | MCP binary/configuration, 49 Skills and local documentation MCP readiness passed. Existing local-KB-assisted M12 workflow and HLS Skill synthesis/c-simulation are VERIFIED. End-to-end local answer model/air-gap and Vitis IDE assistance remain DEFERRED / NOT TESTED. |
| Kernel fault audit | PASS | No targeted amdgpu/TTM/reset/ring-timeout/soft-lockup or amdxdna fault signature was recorded during this unified run. This does not resolve the prior Qwen3.6 Q8 Vulkan issue. |

The first metadata attempt used system Python without NumPy and failed before reading the GGUF files. The same parser was rerun with the existing `.venvs/npu21` Python (NumPy 1.26.4); all seven files parsed. The first failure and correction are both retained in the evidence, and `scripts/run_m15_final_validation.sh` now selects the NumPy-enabled local interpreter when available.

## Recovery and security

The existing CP0 archive (`CP0-20261001T024200Z`, 53,255,905,280 bytes / 49.6 GiB) passed SHA256 verification and an isolated selected-file restore. It predates Vivado/Vitis installation, so this is historical baseline evidence only. The current Xilinx installation tree occupies 250,470,367,232 bytes (about 233.2 GiB); at the latest inventory the root filesystem had 156,526,895,104 bytes free (about 145.8 GiB). The existing checkpoint helper writes an uncompressed root archive, so the Xilinx tree alone exceeds the available space. No T7/external target is mounted. Current-state checkpoint, off-device recovery and full-boot restore are therefore BLOCKED / DEFERRED, not PASS.

After workload verification, the temporary `/etc/sudoers.d/ai370-build` `NOPASSWD: ALL` rule was removed. The narrower checkpoint-verification rule remains. Noninteractive `sudo` now requires authentication; `visudo -c` could not be run after removal without interactive authorization, so sudoers syntax audit is DEFERRED. No attempt was made to bypass that authorization.

The final service inventory found no failed system-level units. One old failed user scope remains visible for the earlier `llama-gguf` Qwen3.6 Q8 parser command (2026-10-01 17:57); it is historical, not a fault from the M15 model smokes. The retained systemd state was not reset or rewritten.

## Final verdict and remaining work

The unified regression is **PASS_WITH_DEFERRED** for the executed software and bounded physical-evidence scope. M15 remains **PRE-FINAL / BLOCKED**, and no Final Golden State or tag was created. To finish M15, make enough separate storage available for a checkpoint that includes the installed Xilinx toolchain, create and verify that current-state checkpoint, and complete the final sudoers syntax/security check. Keep these known boundaries explicit:

- M7.1 Qwen3.6-35B-A3B Q8 Vulkan failure remains OPEN and is excluded from supported Local LLM workloads.
- M8 NPU LLM evaluation remains DEFERRED; no supported NPU LLM model was available.
- M12 standard XRT host-application/`xclbin` path remains DEFERRED; the physical JTAG-to-AXI path is verified.
- M13 end-to-end local answer/air-gapped agent and Vitis IDE/cosimulation flows remain DEFERRED / NOT TESTED.
- M14 full toolchain rebuild and recovery automation are not verified by one clean M12 project rebuild.
- No M15 final checkpoint or final Golden State exists.
