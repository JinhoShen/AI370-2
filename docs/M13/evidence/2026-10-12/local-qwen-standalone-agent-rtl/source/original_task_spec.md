# Task: repair the seeded AXI4-Lite result operation

The DUT uses REG0 input at `0x00`, REG1 control at `0x04`, REG2 result at `0x08`, and REG3 offset at `0x0c`.

Required behavior:
- `control_reg[1] == 0`: REG2 is the bitwise complement of REG0, unchanged from baseline.
- `control_reg[1] == 1`: REG2 is unsigned 32-bit `REG0 + REG3`; overflow wraps modulo 2^32.
- Preserve all AXI4-Lite protocol, address, response, reset, and write behavior.

The testbench checks baseline complement, add-with-offset, returning to legacy mode, and 32-bit wraparound. The RTL has one deliberately seeded arithmetic defect. Diagnose from XSim output and repair the RTL yourself. You may make at most two correction attempts after the first test run. Only edit `rtl/local_model_axi_lite.v`; do not change the testbench, runner, task spec, or README. Do not invoke arbitrary shell commands. Use `exec_command` only for the exact command `bash ./run_validation.sh`; use `apply_patch` for the RTL edit. Do not install packages, access networks, invoke Vivado synthesis, access hardware, or modify anything outside this disposable sandbox.

Final response must state test attempts, the observed first failure (expected and actual), exact RTL behavior change, and whether final `TEST_PASS baseline_and_selected_mode=1` was observed.
