# Local Model task specification

Project: `projects/FPGA/Local_AI_FPGA_Engineering_Test/`

Read this project README and the complete RTL source before proposing a change. The baseline implements an AXI4-Lite register block:

- `REG0` at `0x00`: 32-bit input value.
- `REG1` at `0x04`: 32-bit control register.
- `REG2` at `0x08`: read-only result. Current/legacy behavior is bitwise NOT of `REG0`.
- `REG3` at `0x0c`: configurable 32-bit offset register.

Requested change: add operation mode selected by `REG1[1]`. If bit 1 is one, `REG2` must return `REG0 + REG3` using 32-bit modulo arithmetic. If bit 1 is zero, preserve the existing bitwise-NOT result. Keep the AXI4-Lite protocol, register addresses, byte strobes, reset behavior and error responses intact. Do not change unrelated files or introduce vendor IP.

Return (1) a short plan naming the behavior and RTL location to change, then (2) one unified diff against `projects/FPGA/Local_AI_FPGA_Engineering_Test/src/local_model_axi_lite.v`. Do not provide shell commands, invoke tools, or claim validation. Make the smallest sufficient source change. The test oracle will check legacy mode, add mode, mode disable and 32-bit overflow.
