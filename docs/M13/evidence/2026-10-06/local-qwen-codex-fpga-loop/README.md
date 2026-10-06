# Local Qwen → Codex → XSim/Vivado bounded engineering validation

**Date:** 2026-10-06 (Asia/Taipei)
**Scoped verdict:** `LOCAL_MODEL_FPGA_ENGINEERING_PASS` for this disposable RTL task. This is not an M11/M12 hardware result and does not make all of M13 PASS.

## Result

Qwen3.8-27B-UD-Q4_K_XL (Q4_K_XL, CPU llama.cpp backend) analyzed the task and AXI4-Lite RTL, returned a minimal `REG_RESULT` conditional assignment, and that model-authored expression was applied unchanged to the disposable sandbox copy. The existing self-checking XSim test passed the legacy operation, requested add-with-offset mode, and unsigned 32-bit wraparound. Vivado 2026.1 synthesis then exited 0 and generated utilization and timing reports. No Vivado/Vitis executable or installation configuration was changed; no FPGA was programmed.

## Sandbox license diagnosis and minimal execution setting

Outside and inside the default Codex `workspace-write` sandbox, `HOME`, UID, and license-related environment-variable state were the same; the existing local license file was readable in both contexts. The sandbox mounted the license parent read-only, but passing an alternate HOME and explicit path to the same existing license did not fix checkout. The decisive difference was the network namespace: the host-locked license is bound to a network-interface MAC address, but the default sandbox namespace hides that licensed host NIC/MAC. FlexNet therefore rejects checkout as an invalid host. The host namespace exposes the required NIC identity.

The minimum verified workaround was invocation-scoped Codex configuration:

```sh
codex exec --sandbox workspace-write \
  -C /home/shen/AI370-2/output/M13/codex-qwen-engineering-20261006/project \
  -c 'sandbox_workspace_write.network_access=true' ...
```

With that setting, host network access restored visibility of the license-bound NIC/MAC and the bounded Vivado synthesis passed using the already-installed license. The setting was supplied only to these validation invocations; no persistent Codex/global sandbox setting, license file, license environment variable, Vivado/Vitis installation, or protected GPU/NPU stack was changed. Keep the override limited to tasks that require host-bound licensed tools. Do not record or publish license contents or the MAC value.

The earlier read-only diagnosis remains historical evidence in [`../codex-sandbox-diagnostic.md`](../codex-sandbox-diagnostic.md). The scoped AppArmor profile was separately installed as authorized; global AppArmor and `kernel.apparmor_restrict_unprivileged_userns` remain enabled.

## Verification

- Vivado version command: exit 0; tool reported 2026.1.
- Initial full-runner attempt without environment defaults stopped at the existing `set -u`/`PYTHONPATH` issue. The runner was left unchanged.
- Rerun used invocation-only `PYTHONPATH=` and `MATLABPATH=`; no script or RTL configuration was changed for these variables.
- XSim: `TEST_PASS baseline_and_selected_mode=1`; includes the new operation, legacy mode, and wraparound vectors.
- Vivado synthesis: exit 0; `Synthesis finished with 0 errors`; `synth_design completed successfully`; pass marker emitted.
- Post-synthesis timing: WNS `+6.316 ns`, TNS `0.000 ns`; Vivado reported all user-specified constraints met. This is synthesis timing only, not place-and-route timing.
- Utilization: 123 Slice LUTs, 178 Slice Registers, 0 DSPs, 0 Block RAM Tiles.
- Both utilization and timing-summary reports were generated.
- The first trial with default sandbox networking did not find a valid license. The successful retry required only the scoped network setting above; existing license content was not opened, copied, modified, or included here.

## Project and model provenance

- Disposable project: `output/M13/codex-qwen-engineering-20261006/project/` (Git-ignored), separate from M11/M12.
- The original RTL is preserved as `source/original_local_model_axi_lite.v`; modified RTL is preserved as `source/modified_local_model_axi_lite.v`.
- Qwen's exact conditional-expression hunk is preserved under `model/patch-hunk.md`; no Codex-authored RTL correction was substituted.
- Modified source SHA256: `e06d7b4c8d9caf3a1a1d190676d0ee6c40a6b2e0e975f2c69c03e7cf0ff58afd`.
- Compact XSim output is retained in `logs/xsim-patched-network-sandbox.log`. Raw Vivado logs are intentionally excluded because they contain machine paths and license-environment diagnostics; the sanitized run summary and report metrics above preserve the relevant result.

## Boundaries

No synthesis/implementation work was run on an M11/M12 project, no bitstream was generated, and SP701 was not programmed. No Kernel, Mesa/RADV, libdrm, ROCm/HIP, XRT, amdxdna, firmware, package, license, or Vivado/Vitis installation was changed by this validation. This result closes only the bounded supervised RTL-edit-to-XSim/Vivado-synthesis loop; Ross full air-gapped operation, unrestricted local tool protocol integration, and remaining M13 items retain their separately documented statuses.
