# T7 AMD Ross assisted Vivado XSim: multi-file compile and elaboration repair

The isolated SystemVerilog project has a module integration defect in its public RTL. Read the original XSim diagnostics, identify the source of the compile/elaboration failure, and make the smallest repair. The public interface and behavior are fixed: `calc_top` computes 8-bit ADD, XOR, AND, or SUB selected by `op` and asserts `valid`. Only files under `rtl/` may be edited. Do not edit this task, hidden testbench, runner, or Tcl.

The evaluator compiles package, leaf module, and top in fixed order using Vivado 2026.1, elaborates `tb_calc_top`, and runs the self-checking regression. Baseline diagnostics must be observed before any repair. PASS requires all tool exit codes to be zero and `QUALITY_T7_PASS` in the simulation log.

Before any source edit or XSim validation, call the installed AMD Ross `vivado-simulate-rtl` Skill and its `references/xsim.md` guide using `ross_skill_read`, then call `ross_doc_search` for Vivado 2026.1 multi-file RTL compilation/elaboration guidance. Use both returned results in your diagnosis. Both tool calls must succeed and appear in the trace before a patch or simulation. If Ross tools are unavailable, report blocked; do not substitute another source.
