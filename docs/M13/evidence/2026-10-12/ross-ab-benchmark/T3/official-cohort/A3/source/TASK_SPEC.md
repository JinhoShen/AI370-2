# T3 isolated Vitis HLS engineering task

"
        "The top function is `invert32(uint32_t input)`. Required behavior is the bitwise complement of all 32 input bits. "
        "The fixed testbench has four vectors and must remain unchanged. The source has a seeded defect.

"
        "Read this specification, source, testbench and HLS config. Run `run_hls` unchanged, diagnose its actual C-simulation failure, "
        "make the smallest source-only correction using `apply_patch` or an exact model-authored `apply_replacement`, then rerun `run_hls`. "
        "The fixed tool performs C simulation and, only after all four vectors pass, C synthesis for xc7s100fgga676-2. "
        "Do not edit the testbench/config/runner, invoke shell, or access hardware. Require both fixed PASS markers.
