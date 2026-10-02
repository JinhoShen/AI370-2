# M15 Final Golden Workstation — pre-final validation

**Status: PRE-FINAL.** The single unified software regression completed with PASS results for its tested workloads and explicit OPEN/DEFERRED items. **M15 is not FINAL GOLDEN and the project is not complete.** Under the 2026-10-02 architecture decision, a full current-machine image including the installed Xilinx tree is NOT REQUIRED. The remaining M15 closure work is deployment-kit validation and the pending sudoers syntax/security audit. CP0 remains historical pre-Vivado/Vitis recovery evidence only.

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

The existing CP0 archive (`CP0-20261001T024200Z`, 53,255,905,280 bytes / 49.6 GiB) passed SHA256 verification and an isolated selected-file restore. It predates Vivado/Vitis installation, so this is historical baseline evidence only; full boot restore is NOT TESTED. The M15 run measured the Xilinx installation tree at 250,470,367,232 bytes and root free space at 156,526,895,104 bytes. Those measurements remain valid historical observations, but the later architecture decision makes a full current-state image NOT REQUIRED. T7 is now mounted as Deployment / Migration Media; its resource validation is tracked separately in [`T7 manifest`](../deployment/T7_MANIFEST.md). Do not copy the installed `/home/shen/tools/Xilinx/2026.1` tree.

After workload verification, the temporary `/etc/sudoers.d/ai370-build` `NOPASSWD: ALL` rule was removed. The narrower checkpoint-verification rule remains. Noninteractive `sudo` now requires authentication; `visudo -c` could not be run after removal without interactive authorization, so sudoers syntax audit is DEFERRED. No attempt was made to bypass that authorization.

The final service inventory found no failed system-level units. One old failed user scope remains visible for the earlier `llama-gguf` Qwen3.6 Q8 parser command (2026-10-01 17:57); it is historical, not a fault from the M15 model smokes. The retained systemd state was not reset or rewritten.

## Final verdict and remaining work

The unified regression is **PASS_WITH_DEFERRED** for the executed software and bounded physical-evidence scope. M15 remains **PRE-FINAL**, and no Final Golden State or tag was created. The earlier `status-final.tsv` is an immutable run-time snapshot from before the architecture decision; its current-state checkpoint `BLOCKED` row is reclassified **NOT REQUIRED** by the later decision, without changing the historical evidence. True M15 closure work is to finish the T7 Deployment / Migration Kit inventory and checksums, run the pending sudoers syntax/security audit when administrative authorization is available, and perform the final scope review. No 350 GB current-state archive is required.

- M7.1 Qwen3.6-35B-A3B Q8 Vulkan failure remains OPEN and is excluded from supported Local LLM workloads.
- M8 NPU LLM evaluation remains DEFERRED; no supported NPU LLM model was available.
- M12 standard XRT host-application/`xclbin` path remains DEFERRED; the physical JTAG-to-AXI path is verified.
- M13 end-to-end local answer/air-gapped agent and Vitis IDE/cosimulation flows remain DEFERRED / NOT TESTED.
- M14 full toolchain rebuild and recovery automation are not verified by one clean M12 project rebuild.
- No M15 Final Golden State exists. The deployment kit is not yet fully verified; T7 has the Vivado/Vitis installer byte-identical to the system copy, while other resources remain partially inventoried or unverified.

## Architecture decision update — 2026-10-02

- T7's formal role is **AI370-2 Deployment / Migration Media**, for rebuilding this workstation or moving to another compatible machine with the T7, Git repository and Codex. It is not a current-machine image backup.
- The 53 GB CP0 remains historical pre-Vivado/Vitis evidence. Its checksum and selected-file restore PASS are retained; full boot restore remains NOT TESTED.
- A full current-state archive, including `/home/shen/tools/Xilinx/2026.1`, is **NOT REQUIRED**. The earlier 350 GB capacity estimate and 250 GB Xilinx-tree measurement are not M15 blockers. The existing Xilinx installation must remain in place.
- T7 is now mounted at `/media/shen/T7` (exFAT; 43.3 GB available at inspection). The 2026.1 Vivado/Vitis installer on T7 and the system copy are both 105,522,216,960 bytes and have identical SHA256 `8180734068136de4520d57cc894e34be5bb26ca311ca9e10b6534cffbc08f059`. The system copy is therefore a duplicate-safe-to-delete **recommendation only**; no file was deleted or moved.
- T7 inventory found Ubuntu 24.04.1 media rather than exact 24.04.4 media; a current repository snapshot was not present (the old snapshot is at `db83562` and has local modifications); selected ROCm/XRT/Ryzen AI packages and some GGUF files are present but not comprehensively hash-verified; Ross/Skills/Local KB deployment resources remain unverified. Alternate XRT 2.25 / amdxdna 7.0-rc packages are present under a separate Lemonade download path and are explicitly excluded from the current Golden stack.
- Deployment manifest fields, selected requirements and observed T7 entries are in [`docs/deployment/T7_MANIFEST.md`](../deployment/T7_MANIFEST.md). No local machine image or installed Xilinx tree was copied.
