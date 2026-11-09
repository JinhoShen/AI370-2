# T6 Vitis HLS: bitwise inversion kernel

Implement `std::uint32_t invert32(std::uint32_t input)` in `src/invert32.cpp` so it returns the 32-bit one's complement of the input. Only this source file is editable. Do not change the fixed HLS config or private C testbench.

The fixed Vitis HLS 2026.1 evaluator runs C simulation against four frozen vectors and C synthesis for `xc7s100fgga676-2`. PASS requires the `QUALITY_T6_CSIM_PASS` marker, successful C synthesis and a generated `invert32_csynth.rpt`. The checker does not use an LLM judge.
