#include <cstdint>
#include <cstdio>

std::uint32_t invert32(std::uint32_t input);

int main() {
    const std::uint32_t inputs[] = {0x12345678u, 0x00000000u, 0xffffffffu, 0xa5a5f00du};
    const std::uint32_t expected[] = {0xedcba987u, 0xffffffffu, 0x00000000u, 0x5a5a0ff2u};
    for (unsigned i = 0; i < 4; ++i) {
        const auto actual = invert32(inputs[i]);
        if (actual != expected[i]) {
            std::fprintf(stderr, "vector %u failed: got 0x%08x expected 0x%08x\n", i, actual, expected[i]);
            return 1;
        }
    }
    std::puts("PASS: 4 HLS C simulation vectors matched");
    return 0;
}
