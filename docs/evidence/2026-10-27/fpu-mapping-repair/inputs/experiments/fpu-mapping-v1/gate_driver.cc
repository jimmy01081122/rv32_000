#include "model.cc"
#include <cstdint>
#include <cstdio>
#include <memory>

template<size_t N> const value<N>& current(const wire<N>& v) { return v.curr; }
template<size_t N> const value<N>& current(const value<N>& v) { return v; }
template<size_t N> value<N>& drive(wire<N>& v) { return v.next; }
template<size_t N> value<N>& drive(value<N>& v) { return v; }

static uint32_t rng = 0x745f19b3;
static uint32_t random32() {
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng;
}

int main() {
    auto model = std::make_unique<cxxrtl_design::p_top>();
    auto &m = *model;
    uint64_t cycles = 0, comparisons = 0, digest = 1469598103934665603ULL;
    uint64_t stalls = 0, flushes = 0, resets = 0, accepted = 0;
    uint32_t coverage[256][8] = {};
    auto equal = [&]() {
        return current(m.p_gd) == current(m.p_md) && current(m.p_gv) == current(m.p_mv)
               && current(m.p_gr) == current(m.p_mr);
    };
    auto check = [&]() {
        comparisons++;
        if (!equal()) {
            std::fprintf(stderr, "Mismatch at cycle %llu comparison %llu\n",
                         (unsigned long long)cycles, (unsigned long long)comparisons);
            for (unsigned i=0;i<5;i++) std::fprintf(stderr, "%08x/%08x ", current(m.p_gd).data[i], current(m.p_md).data[i]);
            std::fprintf(stderr, "\n");
            std::exit(1);
        }
        for (auto word : current(m.p_gd).data) digest = (digest ^ word) * 1099511628211ULL;
    };
    auto clock = [&](bool reset, bool flush, bool valid, bool ready, bool initialized=true) {
        m.p_rst.set(reset); m.p_flush.set(flush); m.p_valid.set(valid); m.p_ready.set(ready);
        m.p_clk.set(false); m.step();
        if (initialized) check();
        resets += reset; flushes += flush;
        stalls += m.p_gv.get<bool>() && !ready && !reset && !flush;
        accepted += valid && m.p_gr.get<bool>() && !reset && !flush;
        m.p_clk.set(true); m.step(); check(); cycles++;
    };
    auto field = [&](unsigned low, unsigned bits, uint32_t value) {
        for (unsigned i=0;i<bits;i++) drive(m.p_req).set_bit(low+i, (value >> i)&1);
    };
    m.p_fault.set(false); clock(true,false,false,true,false);
    // An injected result-bit error must be detected by the actual comparator.
    m.p_fault.set(true); m.step();
    if (equal()) { std::fprintf(stderr,"Negative output-bit control escaped\n"); return 2; }
    m.p_fault.set(false); m.step(); check();
    constexpr uint32_t edge[] = {0,0x80000000,0x3f800000,0xbf800000,1,0x007fffff,
        0x00800000,0x7f7fffff,0x7f800000,0xff800000,0x7fc00001,0x7f800001,
        0x3f800001,0x3f000000,0x40000000,0x80800000};
    for (unsigned op=0;op<256;op++) for (unsigned rm=0;rm<8;rm++) for (unsigned k=0;k<16;k++) {
        for (auto &word:drive(m.p_req).data) word=random32();
        drive(m.p_req).data[12] &= 0x1ffff;
        field(276,8,op); field(155,3,rm);
        field(64,32,edge[k]);field(32,32,edge[(k+5)&15]);field(0,32,edge[(k+11)&15]);
        m.p_state.set(k&7); clock(false,false,true,true); coverage[op][rm]++;
        if ((k&3)==0) { clock(false,false,true,false);clock(false,false,false,false); }
        if (k==15) clock(false,true,true,false);
    }
    for (unsigned k=0;k<65536;k++) {
        for (auto &word:drive(m.p_req).data) word=random32();
        drive(m.p_req).data[12] &= 0x1ffff;
        uint32_t controls=random32(); m.p_state.set(controls&7);
        clock((k%257)==0,(k%31)==0,(controls&8)!=0,(controls&16)!=0);
    }
    unsigned covered=0;
    for (auto &op:coverage) for (auto count:op) covered += count==16;
    if (covered!=2048 || !stalls || !flushes || !resets || !accepted) return 3;
    std::printf("{\"passed\":true,\"cycles\":%llu,\"comparisons\":%llu,\"opcode_rounding_pairs\":%u,\"edge_vectors\":32768,\"random_vectors\":65536,\"stall_cycles\":%llu,\"flush_cycles\":%llu,\"reset_cycles\":%llu,\"accepted\":%llu,\"negative_result_bit_control\":true,\"output_digest\":\"%016llx\"}\n",
                (unsigned long long)cycles,(unsigned long long)comparisons,covered,
                (unsigned long long)stalls,(unsigned long long)flushes,(unsigned long long)resets,
                (unsigned long long)accepted,(unsigned long long)digest);
}
