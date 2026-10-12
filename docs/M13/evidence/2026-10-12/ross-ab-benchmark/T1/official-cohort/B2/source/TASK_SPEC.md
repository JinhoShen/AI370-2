# Local Qwen RTL repair task

Read this specification and the RTL before acting. This is a disposable M13 sandbox.

Required behavior: REG0 at 0x00 stores input, REG1 at 0x04 stores control, REG2 at 0x08 returns `~REG0` when control bit 1 is zero and unsigned 32-bit `REG0 + REG3` when bit 1 is one; REG3 at 0x0c stores offset. Preserve AXI-Lite behavior. The existing testbench checks legacy mode, add-with-offset, mode switching and 32-bit wraparound. The RTL contains a seeded arithmetic defect.

You must use the tools in this order: (1) read RTL/spec, (2) call `run_xsim` on unchanged baseline, (3) analyze the actual failing XSim result, (4) use `apply_patch` to submit the smallest RTL-only repair, (5) call `run_xsim` again. If it still fails, use its actual output and you may repair once more. Never edit the testbench, runner or task spec. Do not invoke shell or other commands, access hardware, install packages, or edit outside this sandbox. The executor enforces the exact XSim command and maximum attempts.

A valid result requires the fixed runner to report `TEST_PASS baseline_and_selected_mode=1`. Report the actual first failure, exact RTL change, number of XSim attempts and whether the final independent testbench passed.
