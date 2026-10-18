#include "core_roi_profile.h"
#include <cassert>
#include <sstream>

int main() {
    uint32_t words[] = {0x80000000u, 0x12345678u, 0xfeedbeefu};
    assert(CoreRoi::bits(words, 31, 32) == 0x2468acf1u);
    assert(CoreRoi::bits(words, 32, 32) == 0x12345678u);
    assert(CoreRoi::bits(words, 60, 8) == 0xf1u);
    assert(CoreRoi::kind(0x10f57653) == "fmul");
    assert(CoreRoi::kind(0x00c77753) == "fadd");
    assert(CoreRoi::kind(0x78e5f7c3) == "fma");
    assert(!CoreRoi::fma(0x02000043)); // Double is not single precision.
    CoreRoi::Profile p;
    CoreRoi::Snapshot s;
    s.rob_count = 2; s.pc = 0x80000204; s.insn = 0x78e5f7c3;
    s.head_fp_iq_ready = 6; s.dmem_pending = true;
    p.sample(s); p.finish_cycle(false, 0, 0);
    assert(p.partition["head_wait_fma"] == 1);
    assert(p.overlap["fp_head_wait_src2_only"] == 1);
    assert(p.overlap["dmem_pending"] == 1); // Overlaps, not an extra cycle.
    s.head_fp_iq_ready = 3;
    p.sample(s); p.finish_cycle(false, 0, 0);
    assert(p.overlap["fp_head_wait_src01"] == 1);
    s.can_retire = true;
    p.sample(s); p.finish_cycle(true, s.pc, s.insn);
    assert(p.instructions["fma"] == 1 && p.pcs[s.pc].head_wait == 2);
    s.insn = 0xc00022f3;
    p.sample(s); p.finish_cycle(true, s.pc, s.insn);
    assert(p.partition["retired_marker"] == 1 && p.instructions.size() == 1);
    s.can_retire = false; s.rob_count = 0;
    p.sample(s); p.finish_cycle(false, 0, 0);
    assert(p.partition["rob_empty"] == 1);
    s.rob_count = 1; s.completed = true; s.store_ack_wait = true; s.store_phase = 3;
    s.insn = 0x00f62027;
    p.sample(s); p.finish_cycle(false, 0, 0);
    assert(p.partition["store_ack_wait"] == 1 && p.store_wait["load_response_buffer"] == 1);
    s.completed = false; s.store_ack_wait = false; s.insn = 0x00072707; s.load_phase = 2;
    p.sample(s); p.finish_cycle(false, 0, 0);
    assert(p.partition["head_wait_fp_load"] == 1 && p.load_wait["own_response_buffer"] == 1);
    uint64_t total = 0;
    for (auto item : p.partition) total += item.second;
    assert(total == p.cycles && p.trace_mismatches == 0);
    p.sample(s); p.finish_cycle(true, 0, 0);
    assert(p.trace_mismatches == 1); // Decode/timing faults must be visible.
    std::ostringstream out; p.write(out);
    assert(out.str().find("\"trace_mismatches\": 1") != std::string::npos);
}
