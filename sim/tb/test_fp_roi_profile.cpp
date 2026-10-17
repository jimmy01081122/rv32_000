#include "fp_roi_profile.h"
#include <cassert>

int main() {
    FpRoiProfile p;
    p.observe(0x43); // Outside ROI.
    p.observe(0xc00022f3); // rdcycle t0, destination bits are ignored.
    for (auto instruction : {0x43u, 0x47u, 0x4bu, 0x4fu, 0x02000043u, 0x53u}) p.observe(instruction);
    p.observe(0xc0002373);
    p.observe(0x43);
    assert(p.cycle_reads == 2 && p.retired == 6);
    for (auto count : p.fused) assert(count == 1);
    assert(!p.active);
    p.observe(0xc0002073);
    assert(p.cycle_reads == 3 && !p.active);
}
