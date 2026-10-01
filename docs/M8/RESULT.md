# M8 NPU Local AI evaluation — RESULT

日期：2026-10-01。狀態：NPU ONNX workload PASS；NPU LLM evaluation DEFERRED (model absent locally)。本次未安裝、移除或切換任何 NPU/GPU driver, XRT, firmware, Kernel, ROCm 或 Mesa component。

## Precheck and stack provenance

- Reused M5 Golden State `ai370-2-npu-golden`: Kernel 6.17.0-14-generic, DKMS `amdxdna` 2.21.260102.53.release, XRT 2.21.75, Strix NPU BDF 0000:c6:00.1, firmware 1.1.2.64. Provenance and firmware checksums remain in `docs/M5/reboot/`; this stage performed no stack switch.
- Existing Ryzen AI 1.7.1 local SDK wheelhouse and `.venvs/npu21` were reused. Runtime is ONNX Runtime 1.23.3.dev20260320 with VitisAIExecutionProvider; execution uses `scripts/ryzenai21.sh` and the same M5 XRT 2.21 compatibility shim.
- Local model inventory contained the 23 MiB quantized CNN ONNX, two tiny synthetic ONNX graphs and GGUF text models. It did not contain the `amd/Phi-3.5-mini-instruct_rai_1.7.1_npu_4K` NPU LLM weights/model package. A GGUF is not an NPU model and was not substituted. The local `hybrid-llm.tar.gz` contains runtime/examples, not model weights.

## NPU inference

Re-ran the existing CNN with `verify/npu_cnn.py` and CPU fallback disabled (`session.disable_cpu_ep_fallback=1`, `session.disable_fallback()`). Model SHA-256 is `7a78c7e85bac3a0681e3d2f77e69093a761e1c8f62f7fc65ff5ce3e1b82c5ba3`; input is dynamic batch x 3 x 32 x 32 FP32, output is batch x 10. Ten inferences passed. ORT profile reports only `VitisAIExecutionProvider` for every executed node; a live `/dev/accel/accel0` descriptor identifies `amdxdna_accel_driver` on 0000:c6:00.1. The NPU hardware counter rose by 14,768,241 ns, elapsed inference time was 0.01610 s, and max absolute output error against an independently computed CPU reference was 0.0 (rtol 0.001, atol 0.0001).

The local tiny MatMul (`ffad7a1d…a322`) and QDQ Conv (`d2a5fff3…ccd8`) were also preflighted under the same strict no-fallback policy. Both were rejected at session initialization because graph nodes would be assigned to the default CPU EP. They produced no inference and are recorded as unsupported graph candidates, not NPU failures or passes. Their complete logs and profile attempts are retained in ignored `output/M8/`.

The CNN run completed without a new NPU/GPU reset, page fault, TTM corruption or soft lockup in the kernel journal. Full machine-readable result and ORT profile are in ignored `output/M8/verified-cnn-result.json` and `output/M8/verified-cnn/`.

## Rebuild / reverify

```bash
NPU_OUTPUT_DIR=output/M8/verified-cnn \
NPU_RESULT_FILE=output/M8/verified-cnn-result.json \
bash scripts/ryzenai21.sh timeout 180 .venvs/npu21/bin/python \
  verify/npu_cnn.py output/M5/quicktest/quicktest/test_model.onnx
```

This completes the available local NPU vision/ONNX evaluation. NPU LLM compile/inference, quantization and context tests remain DEFERRED until the supported NPU LLM model and its exact revision/license are available locally. No claim is made that GGUF CPU/Vulkan/ROCm inference uses the NPU.
