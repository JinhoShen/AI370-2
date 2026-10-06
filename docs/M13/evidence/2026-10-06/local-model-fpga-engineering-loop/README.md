# Local Qwen → Agent → XSim bounded RTL feedback loop

**Result: PASS for this bounded behavioral RTL task. M13 overall remains IN PROGRESS.**

On 2026-10-06, Qwen3.8-27B-UD-Q4_K_XL running locally through llama.cpp (CPU) was given the requested AXI4-Lite behavior and the isolated RTL. A deterministic testbench served as the oracle. Codex reviewed and applied the model-produced one-line patch, ran the bounded XSim command inside Bubblewrap, returned the actual first simulation failure to the same local model, and applied the model's revised diff. The second actual simulation passed all checks.

This was a supervised agent-controller loop. It does not establish a single autonomous Codex CLI session completing a multi-step write workflow: two Codex CLI attempts against the local Responses provider timed out while the model was processing the CLI context. The successful bounded workflow used the local loopback chat-completions endpoint for model output and Codex as the safety controller. The exact requests/responses and XSim logs are retained here.

## Task and isolation

The task required the result register to preserve legacy `~input_reg` mode and, when `control_reg[1]` is set, return unsigned 32-bit `input_reg + offset_reg` with modulo-2^32 wraparound. The work was done only in a disposable directory under ignored `output/`; no M11/M12 project or hardware was touched. The testbench and runner are included under `source/`; their testbench SHA guard passed.

Qwen ran CPU-only with 24 threads, context 8192, no GPU layers, a 30 GiB memory cap, and swap disabled. Bubblewrap mounted the host filesystem read-only and only the disposable project writable. The host network namespace and host HOME were visible to XSim because the existing FlexNet license is host-NIC-bound and stored under `~/.Xilinx`; no license data or NIC/MAC value is in this evidence. No package, kernel, Mesa, ROCm, XRT, amdxdna, firmware, driver, or persistent sandbox setting changed.

## Model authorship and feedback

The original model output requested file discovery first; no discovery tool was executed for that response. A first focused arithmetic reply used specification aliases rather than RTL identifiers, so Codex supplied the exact identifiers and received `input_reg + offset_reg`. That expression was held for review and was not applied until after the baseline tool run.

The first actual XSim behavioral run passed the REG0 read and legacy complement checks, then failed the selected-mode comparison at 240 ns: actual `0x1336557c`, expected `0x1336597c`. Codex sent that precise error, expected value, and the unchanged RTL line to the same local Qwen model. Qwen returned the one-line diff preserved in `model/qwen-response-after-xsim-feedback.json`; Codex applied that diff without altering the testbench or other RTL.

The corrected XSim run emitted `TEST_PASS baseline_and_selected_mode=1` and completed at 460 ns. This covers baseline result behavior, addition with offset, switching back to legacy mode, and 32-bit wraparound. XSim behavioral simulation passed; this run did not perform RTL synthesis, implementation, bitstream generation, or physical FPGA programming.

## License startup observations

Two preserved infrastructure-only startups failed before the testbench ran. The first had an isolated network namespace; the second retained host networking but set HOME to a scratch directory, hiding `~/.Xilinx/Xilinx_shen.lic`. After retaining both the host NIC identity and the existing read-only host HOME, Vivado Simulator checked out its license and the seeded behavioral failure was observed. These are license-context setup observations, not design failures and not changes to the license.

## Files

- `source/seeded_rtl.v`, `source/final_rtl.v`, `source/local-model-applied.patch`: exact starting state, result and diff.
- `source/testbench.sv`, `source/run_validation.sh`, `source/task_spec.md`: independent oracle and bounded invocation.
- `model/`: raw local-model responses, including the response after actual XSim feedback.
- `runs/`: license startup logs, the first functional failure, and final PASS output plus XSim-generated logs.
- `runtime-snapshot.txt`: model, sandbox, test and protected-stack boundary.
- `SHA256SUMS`: evidence file integrity.
