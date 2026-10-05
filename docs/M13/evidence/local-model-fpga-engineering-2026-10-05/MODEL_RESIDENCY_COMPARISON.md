# Local model comparison for bounded FPGA RTL editing

Date: 2026-10-05. Purpose: compare already available CPU GGUF candidates for a small, real RTL edit and assess practical memory/latency versus patch reliability. This is not a general benchmark and does not measure idle `llama-server` residency.

All runs used the existing CPU-only `llama-cli` build, context 4096, batch 8 / ubatch 4, 24 threads, no CPU quota, per-run `MemoryMax=30G`, `MemorySwapMax=0`, and a 900-second timeout. The host had 24 online CPU threads. No GPU/NPU backend was used. Global swap was already partly occupied by unrelated existing activity; each model process reported zero swap use. Local models had no shell, file-write, Vivado, or simulator access.

Byte-exact copies of raw response/patch-check text files that contain terminal trailing spaces are retained alongside them as `.raw.gz`; their readable text counterparts differ only by stripped terminal whitespace/blank lines so repository whitespace checks remain clean.

## Results

| Model | File size | Engineering patch result | CPU run evidence |
|---|---:|---|---|
| Qwen3.8-27B-UD-Q4_K_XL | 17,559,178,144 bytes | **PASS after explicit patch-check feedback**. Correct minimal conditional change; patch applied unchanged; XSim and Vivado synthesis passed. | 7:04 wall, 22.9 CPU cores average, 19,585,876 KiB peak RSS, 0 swaps. The model needed a precise repair prompt with the exact failed hunk location/counts. |
| Qwen3.8-27B-UD-Q4_K_M | 16,464,440,224 bytes | **FAIL within its bounded attempts**. Its patch responses remained malformed and were not applied. | Final recorded correction run: 2:34 wall, 23.0 CPU cores average, 20,178,944 KiB peak RSS, 0 swaps. |
| Qwen3.8-27B-Uncensored-Q4_K_M | 16,810,714,528 bytes | First response expressed the right RTL behavior, but its patch had incorrect hunk counts. One correction returned the same malformed hunk count. **FAIL; not applied.** | First run: 4:18 wall, 22.46 CPU cores average, 27,954,444 KiB peak RSS, 0 swaps. Correction: 4:26 wall, 23.07 CPU cores average, 27,969,164 KiB peak RSS, 0 swaps. First-run prompt/generation rate: 12.5 / 3.3 tokens/s; correction: 11.5 / 2.8 tokens/s. |
| Qwen3.5-9B-UD-Q4_K_XL | 5,966,095,584 bytes | First response introduced a duplicate 0x04 write register and an incomplete/invalid patch. The first correction prompt accidentally contained an evaluator instruction to edit the existing REG_CONTROL write case, so that response is retained but excluded from model scoring. After a corrected prompt explicitly kept write logic unchanged, the model still emitted a patch that redundantly redefined existing AXI ready assignments; patch-check failed. **FAIL; not applied.** | First run: 1:51 wall, 22.79 CPU cores average, 7,465,320 KiB peak RSS, 0 swaps; 34.4 / 9.4 tokens/s. Clean-feedback correction: 2:18.90 wall, 23.22 CPU cores average, 7,926,944 KiB peak RSS, 0 swaps; 28.3 / 7.8 tokens/s. |

The Qwen3.8 model hashes were already recorded by the M7 model inventory: Q4_K_XL `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`; Q4_K_M `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`; Uncensored `4c5e2db039e9325ac7724c8846c71356a24ad1cdfa28002d73ecb6be645f9675`. The Qwen3.5-9B repeated cache file was opened successfully as GGUF by llama.cpp; no trusted hash is asserted here.

## Verified RTL and tool result

The task changed REG2 to return `input_reg + offset_reg` when existing control bit 1 is set, preserving `~input_reg` otherwise. The model-generated Q4_K_XL patch is retained at [alternate-model-q4kxl/model-generated.patch](alternate-model-q4kxl/model-generated.patch), and the output source SHA256 is in [functional-validation/source.sha256](alternate-model-q4kxl/functional-validation/source.sha256).

Vivado Simulator compile, elaboration and run all exited 0. Testbench PASS covered input write/read, new addition (`0x12345678 + 0x01020304 = 0x1336597c`), legacy behavior after disabling the mode (`0xedcba987`), and 32-bit wrap (`0xffffffff + 1 = 0`). Vivado 2026.1 synthesis exited 0: 123 Slice LUTs, 178 Slice Registers; synthetic 100 MHz report WNS +6.316 ns / TNS 0 ns. The XDC has a clock constraint but no external input/output delay constraints, so this is only sandbox synthesis evidence.

## Recommendation

For engineering edits that need reliable source patches, use **Qwen3.8-27B-UD-Q4_K_XL as the current CPU candidate**, with Codex retaining patch review and tool execution. It is the only tested candidate here to produce a usable patch and pass functional/synthesis verification. Expect about 18.7 GiB peak RSS and several minutes for this full-source task on CPU. Start it on demand; this run does not justify keeping a 19 GiB process permanently loaded.

Qwen3.5-9B is the lightweight option at roughly 7.1 GiB RSS and 9.4 tokens/s generation for this prompt, but it failed the RTL task twice. It may suit general short local assistance, but it is not currently evidenced as the sole FPGA engineering agent. The uncensored 27B variant used about 26.7 GiB RSS, was slower, and did not repair its patch after feedback; it is a poor always-loaded choice for this workstation. Q4_K_M's bounded patch-generation result was unsuccessful despite its lower RSS than Q4_K_XL.

This recommendation is limited to these CPU patch-generation trials. Existing M7 bounded backend smokes remain separate; no Qwen3.6 Vulkan case, large-model GPU stress test, or protected-stack change was run here.
