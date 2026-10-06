# Codex + local Qwen FPGA engineering sandbox

This is a disposable software-only AXI4-Lite RTL exercise. It is isolated under ignored `output/M13/`; it is not an M11/M12 project and must never program the SP701.

The starting RTL implements REG0 input, REG1 control, REG2 bitwise-NOT result and REG3 offset. The existing self-checking testbench also checks the requested add mode and will fail until the RTL is changed.

Requested engineering change: when REG1 bit 1 is set, REG2 must return REG0 + REG3 with unsigned 32-bit wraparound; when clear, preserve bitwise-NOT. Keep register addresses, AXI protocol, reset, byte strobes and error behavior unchanged. Edit only `rtl/local_model_axi_lite.v`.

Run `RUN_TAG=baseline ./scripts/run-validation.sh` before editing, then record and understand the expected functional failure. After editing, use a new RUN_TAG for each attempt. At most three model-driven correction attempts. Do not alter the testbench, runner or constraints. No board pins, implementation, bitstream or hardware operation is in scope.
