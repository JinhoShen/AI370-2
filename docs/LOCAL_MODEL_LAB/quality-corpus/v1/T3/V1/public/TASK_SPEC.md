# T3 Testbench Generation: self-checking AXI4-Lite regression

Create `sim/tb_axi_regs.sv`, a self-checking SystemVerilog testbench for the supplied correct `axi_regs` design. Only the testbench is editable. The public module interface and four register addresses are in `rtl/axi_regs.sv`; reset values in order are 0x10203040, 0xA5A55A5A, 0x0BADF00D, 0x55AA33CC.

Exercise and check all of the following: reset values; AW-before-W; W-before-AW; simultaneous AW/W; all four WSTRB byte lanes including a partial write; unmapped and unaligned accesses; B response backpressure with stable BVALID/BRESP; R response backpressure with stable RVALID/RDATA/RRESP; and multiple consecutive transactions. Use self-checking assertions or `$fatal` on any mismatch and a finite watchdog. Do not alter the DUT, task specification, runner or hidden test data.

The fixed evaluator runs your testbench on the correct DUT and on five hidden mutated DUTs. PASS requires the correct DUT to print `QUALITY_T3_PASS`, emit each required `QUALITY_T3_SCENARIO_<name>_PASS` marker, and every mutant to fail without the terminal marker. Required names: reset, aw_before_w, w_before_aw, simultaneous, wstrb, unmapped, b_backpressure, r_backpressure, consecutive. The evaluator itself, rather than a language model, checks mutation sensitivity.
