# Local Agent Write Sandbox

Disposable M13 agent-write/self-repair exercise. This folder is ignored build/test output and is separate from all M11/M12 projects.

Read `TASK_SPEC.md`, then inspect `rtl/local_model_axi_lite.v`. The testbench under `sim/` is the independent oracle and must not be edited. `run_validation.sh` compiles and runs bounded Vivado XSim, preserving each attempt log under `runs/`. The RTL begins with one intentional arithmetic defect in add mode. Fix only the RTL after using actual XSim tool feedback.
