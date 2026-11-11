# T5 Vivado synthesis: remove inferred latch while preserving behavior

Repair `rtl/mux_math.sv`. For `sel` 0, 1, 2, 3, compute respectively 8-bit wrapping add, XOR, AND, and subtract; for selectors 4–7, output zero. `y` must be fully combinational and have no inferred latch. Only the DUT file is editable.

The fixed evaluator first runs a self-checking XSim regression (including all eight selector values), then Vivado 2026.1 synthesis for the frozen FPGA part. PASS requires the regression marker, successful synthesis, a utilization report, and no latch diagnostics. Timing closure is not required.
