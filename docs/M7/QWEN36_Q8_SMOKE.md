# Qwen3.6-35B-A3B Q8_0 low-load smoke record

Date: 2026-10-01 (Asia/Taipei). This is a model-specific download, metadata, and low-load smoke verification. It is **not** an M7 high-load or stability PASS and does not replace the previously recorded M7 baseline.

## Results

| Check | Result | Evidence |
|---|---|---|
| DOWNLOAD VERIFIED | PASS | Exact path, byte size, and nanosecond mtime in `evidence/qwen36-35b-a3b-q8/download-integrity.txt` |
| SHA256 | `d8d7842cc657d720f39546878e431937c84473aa130c36371669ac17c80c7361` | Full-file SHA256 in the same evidence file |
| GGUF PARSE VERIFIED | PASS (metadata/header and tensor descriptors) | `gguf-metadata.json`; llama.cpp bundled `gguf-py` parser. This did not load or validate all tensor payloads; full-file SHA256 covers byte integrity. |
| CPU INFERENCE VERIFIED | PASS | `cpu-smoke.log`, `cpu-run-metadata.txt`; exact response `READY.`, 3 generated tokens, context 64, batch 8, ubatch 4, four CPU threads. The test cgroup had `memory.swap.max=0`, `memory.swap.peak=0`, and `/usr/bin/time` reported 0 swaps. |
| VULKAN VERIFIED | FAIL (smoke attempted; no inference completed) | `vulkan-smoke.log`, `vulkan-run-metadata.txt`, `kernel-vulkan.log`; one output layer selected for Vulkan0, then RADV reported command submission memory failure, Vulkan device lost, and model loading failed. No fallback was accepted. |
| ROCM VERIFIED | DEFERRED / NOT RUN | ROCm device enumeration is recorded in `backend-devices.log`; inference was not attempted after the Vulkan kernel/driver errors. Enumeration is not an inference PASS. |

## File and model metadata

- File: `resources/Agent_Tools_Docs/04_Local_AI/GGUF/Qwen3.6-35B-A3B-Q8_0.gguf`
- Exact size: 36,903,139,328 bytes
- mtime: `2026-10-01 15:43:45.619663297 +0800`
- GGUF version 3; architecture `qwen35moe`; model name `Qwen3.6-35B-A3B`; size label `256x2.6B`; file quantization `MOSTLY_Q8_0`.
- Metadata reports 43 key/value entries, 733 tensor descriptors and 34,660,610,688 parameter elements (432 Q8_0 and 301 F32 tensors). Architecture metadata reports 40 blocks, embedding length 2048, context length 262144, 256 experts and 8 used experts.

## Safety and kernel observations

Each inference ran in a systemd cgroup with swap disabled. The CPU test's cgroup swap peak was zero. During both inference windows, host-wide `/proc/vmstat` swap counters increased and host swap occupancy increased; therefore this record makes no host-wide no-swap claim. The counter changes were outside the test cgroup attribution and are preserved in the per-run metadata.

The Vulkan smoke was deliberately bounded (context 64, batch 8, ubatch 4, one output layer, 32 GiB cgroup memory cap, zero cgroup swap). It failed while loading/uploading weights: the kernel log contains 685 `amdgpu_vm_validate() failed` and 685 `Not enough memory for command submission!` messages, followed by Vulkan device loss. The targeted captured log contains no page-fault, GPU-reset, TTM-corruption, ring-timeout, or soft-lockup match. Because the command-submission errors are real GPU/kernel errors, no further GPU inference was run, including ROCm. The log is retained for diagnosis; this smoke does not establish general GPU stability.

The separate initial `llama-gguf` inspection attempt was terminated by its 2 GiB cgroup memory limit (exit 137) after partial tensor-descriptor output. The metadata PASS comes from the later bounded Python `gguf-py` parse, which completed without loading tensor weights. This parser-tool OOM is not a model inference result.

No high-load benchmark, 4096/8192 context run, long-duration test, or full GPU offload was performed. Do not infer M7 high-load/stability PASS from this record.
