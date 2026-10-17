#ifndef FP_ROI_PROFILE_H
#define FP_ROI_PROFILE_H
#include <array>
#include <cstdint>

// Architectural instructions strictly between the first two retired RDCYCLEs.
// This observes the commit stream and adds no modeled hardware/cycle latency.
struct FpRoiProfile {
    uint64_t cycle_reads = 0;
    uint64_t retired = 0;
    std::array<uint64_t, 4> fused = {};
    bool active = false;

    void observe(uint32_t instruction) {
        if ((instruction & 0xfffff07fu) == 0xc0002073u) {
            ++cycle_reads;
            active = cycle_reads == 1;
            return;
        }
        if (!active) return;
        ++retired;
        if (((instruction >> 25) & 3u) != 0) return; // Single precision only.
        switch (instruction & 0x7fu) {
            case 0x43: ++fused[0]; break;
            case 0x47: ++fused[1]; break;
            case 0x4b: ++fused[2]; break;
            case 0x4f: ++fused[3]; break;
            default: break;
        }
    }
};
#endif
