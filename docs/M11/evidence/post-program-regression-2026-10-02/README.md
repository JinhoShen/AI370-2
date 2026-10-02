# Post-program protected-stack regression

Date: 2026-10-02, Asia/Taipei. Ran after programming the SP701 DDR3 test design.

- HIP: PASS, 1,024 results verified on Radeon 890M / gfx1150; exit 0.
- Vulkan: PASS, 1,024 shader results verified on Radeon 890M / RADV GFX1150, CPU fallback forbidden; exit 0.
- XRT enumeration: PASS, NPU Strix present at `0000:c6:00.1`; exit 0. An initial direct attempt to invoke the non-executable helper returned 126; rerunning it with `bash` passed.
- M5 CNN: PASS, ten inferences with CPU fallback disabled; all profiled nodes on `VitisAIExecutionProvider`; NPU hardware time increased 14,691,769 ns; maximum CPU-reference error 0.0; exit 0.
- Kernel journal query succeeded for the test window. No amdgpu/amdxdna fault, page fault, TTM corruption, ring timeout, GPU reset, BUG, call trace or soft-lockup keywords were present in the filtered window.
- No protected stack package, kernel, module or firmware change was made.

This is a bounded post-program regression, not a full M15 regression or stress test. Raw command output, machine-readable NPU result/profile, and kernel log are retained alongside this note.
