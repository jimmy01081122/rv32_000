#ifndef RV32_FP_OBSERVER_H
#define RV32_FP_OBSERVER_H
#include <array>
#include <map>
#include <string>
#include <stdexcept>
#include "core_roi_profile.h"

// Host-only, const access to the retained Verilator 4.038 model. A cycle is
// sampled after low-edge eval. No CPU input or internal state is written.
namespace FpObserve {
inline unsigned unit(unsigned fu) {
    if (fu == 10) return 0; // FU_FP_MISC
    if (fu == 9) return 2;  // FU_FP_DIVSQRT
    if (fu == 6 || fu == 7 || fu == 8 || fu == 11) return 1;
    throw std::runtime_error("unexpected FP fu_class");
}
inline unsigned instruction_unit(uint32_t insn) {
    if (CoreRoi::fma(insn)) return 1;
    if ((insn & 127) != 0x53) throw std::runtime_error("non-FP instruction in FP unit");
    switch (insn >> 25) {
        case 0: case 4: case 8: case 0x60: case 0x68: return 1;
        case 12: case 44: return 2;
        case 0x10: case 0x14: case 0x50: case 0x70: case 0x78: return 0;
        default: throw std::runtime_error("unexpected FP instruction");
    }
}
struct Snapshot {
    bool flush = false, ex_valid = false, target_ready = false;
    bool input_ready = false;
    unsigned ex_unit = 0, ex_tag = 0, ex_insn = 0, iq_mask = 0;
    std::array<bool,3> ready{}, valid{}, grant{};
    std::array<unsigned,3> tags{};
    std::array<unsigned,4> iq_units{};
};
template<class T> Snapshot read(const T& t) {
    Snapshot s;
    s.flush = t.rv32_ooo_core__DOT__flush_valid;
    s.ex_valid = t.rv32_ooo_core__DOT__fp_ex0_valid_q;
    s.target_ready = t.rv32_ooo_core__DOT__fp_target_ready;
    s.input_ready = t.rv32_ooo_core__DOT__fp_ex0_in_ready;
    s.ready = {{bool(t.rv32_ooo_core__DOT__u_fp_simple__DOT__can_accept),
                bool(t.rv32_ooo_core__DOT__u_fp_execute__DOT__can_accept),
                bool(t.rv32_ooo_core__DOT__fp_divsqrt_issue_ready)}};
    s.valid = {{bool(t.rv32_ooo_core__DOT__u_fp_simple__DOT__holding_valid),
                bool(t.rv32_ooo_core__DOT__u_fp_execute__DOT__holding_valid),
                bool(t.rv32_ooo_core__DOT__fp_divsqrt_cmp_valid)}};
    s.grant = {{bool(t.rv32_ooo_core__DOT__fp_simple_cmp_ready),
                bool(t.rv32_ooo_core__DOT__fp_heavy_cmp_ready),
                bool(t.rv32_ooo_core__DOT__fp_divsqrt_cmp_ready)}};
    const uint32_t* packets[] = {t.rv32_ooo_core__DOT__u_fp_simple__DOT__holding_data,
        t.rv32_ooo_core__DOT__u_fp_execute__DOT__holding_data,
        t.rv32_ooo_core__DOT__fp_divsqrt_cmp_data};
    for (unsigned i=0;i<3;++i) s.tags[i]=CoreRoi::bits(packets[i],138,16);
    // renamed_uop=305, exec_req=401; FP IQ entry prepends valid and appends
    // three readiness bits. Cross-check class against opcode and ROB owner.
    auto owner = [&](unsigned tag, uint32_t insn) {
        const auto* e=t.rv32_ooo_core__DOT__u_rob__DOT__entries[tag&15];
        if (!CoreRoi::bits(e,244,1) || CoreRoi::bits(e,227,16)!=tag ||
            CoreRoi::bits(e,163,32)!=insn) throw std::runtime_error("FP owner/layout mismatch");
    };
    if(s.ex_valid) {
        const auto* e=t.rv32_ooo_core__DOT__fp_ex0_req_q;
        s.ex_unit=unit(CoreRoi::bits(e,272,4));
        s.ex_tag=CoreRoi::bits(e,284,16);s.ex_insn=CoreRoi::bits(e,337,32);
        if(!s.flush) owner(s.ex_tag,s.ex_insn);
        if(s.ex_unit!=instruction_unit(s.ex_insn) || s.target_ready!=s.ready[s.ex_unit])
            throw std::runtime_error("FP EX0 class/ready mismatch");
    }
    s.iq_mask=t.rv32_ooo_core__DOT__u_fp_iq__DOT__ready_mask;
    unsigned expected_mask=0;
    for(unsigned i=0;i<4;++i) {
        const auto* e=t.rv32_ooo_core__DOT__u_fp_iq__DOT__entries[i];
        if(!CoreRoi::bits(e,308,1))continue;
        s.iq_units[i]=unit(CoreRoi::bits(e,179,4));
        auto insn=CoreRoi::bits(e,244,32);
        if(s.iq_units[i]!=instruction_unit(insn))throw std::runtime_error("FP IQ class mismatch");
        if(!s.flush)owner(CoreRoi::bits(e,191,16),insn);
        if(CoreRoi::bits(e,0,3)==7 && t.rv32_ooo_core__DOT__u_rob__DOT__current_state==0)
            expected_mask|=1u<<i;
    }
    if(expected_mask!=s.iq_mask || s.input_ready!=(!s.ex_valid||s.target_ready))
        throw std::runtime_error("FP readiness/layout mismatch");
    return s;
}
struct Profile {
    struct Pending { bool valid=false, roi=false, seen=false; unsigned tag=0,insn=0; uint64_t cycle=0; };
    std::array<Pending,3> pending{};
    std::array<uint64_t,3> last_issue{};
    std::array<bool,3> have_issue{};
    std::map<std::string,uint64_t> counts;
    std::map<std::string,std::map<uint64_t,uint64_t>> hist;
    uint64_t now=0, cycles=0;
    bool was_roi=false;
    static const char* name(unsigned i) { const char* n[]={"simple","arithmetic","divsqrt"};return n[i]; }
    void sample(const Snapshot& s,bool roi) {
        ++now;if(roi)++cycles;
        if(was_roi && !roi)for(auto& p:pending)if(p.valid&&p.roi){++counts["issued_in_roi_censored_at_roi_end"];p.roi=false;}
        was_roi=roi;
        if(s.flush) {
            for(auto& p:pending){if(roi&&p.valid&&p.roi)++counts["issued_in_roi_cancelled_by_flush"];p={};}
            if(roi)++counts["flush_cycles"];return;
        }
        unsigned mask=0;
        for(unsigned i=0;i<3;++i)if(s.valid[i])mask|=1u<<i;
        if(roi)++hist["completion_valid_mask"][mask];
        if(roi && s.ex_valid && !s.target_ready) {
            ++counts["ex0_blocked"];++counts[std::string("ex0_blocked_")+name(s.ex_unit)];
            bool any=false;std::array<bool,3> eligible{};
            for(unsigned i=0;i<4;++i)if((s.iq_mask>>i)&1) {
                auto u=s.iq_units[i];if(u!=s.ex_unit && s.ready[u])eligible[u]=any=true;
            }
            if(s.iq_mask)++counts["blocked_ex0_with_ready_iq"];
            if(any)++counts["blocked_ex0_with_other_unit_ready_iq"];
            for(unsigned i=0;i<3;++i)if(eligible[i])++counts[std::string("eligible_other_")+name(i)];
        }
        for(unsigned i=0;i<3;++i) {
            auto& p=pending[i];const std::string n=name(i);
            if(s.valid[i]) {
                if(!p.valid || s.tags[i]!=p.tag)throw std::runtime_error("FP completion ownership mismatch");
                if(!p.seen) {
                    if(roi && p.roi){++hist[n+"_issue_to_first_valid"][now-p.cycle];
                        ++hist["opcode_"+CoreRoi::kind(p.insn)+"_issue_to_first_valid"][now-p.cycle];}
                    p.seen=true;
                }
                if(roi)++counts[n+(s.grant[i]?"_completion_grants":"_completion_blocked")];
                if(s.grant[i]) {
                    if(roi&&p.roi)++hist[n+"_issue_to_grant"][now-p.cycle];
                    p={};
                }
            }
            if(s.grant[i] && !s.valid[i])throw std::runtime_error("grant without completion");
            if(roi)++counts[n+(s.ready[i]?"_ready_cycles":"_not_ready_cycles")];
        }
        if(s.ex_valid && s.target_ready) {
            auto u=s.ex_unit;auto& p=pending[u];
            if(p.valid)throw std::runtime_error("overlapping single-slot FP ownership");
            p.valid=true;p.roi=roi;p.tag=s.ex_tag;p.insn=s.ex_insn;p.cycle=now;
            if(roi) {
                ++counts[std::string(name(u))+"_issues"];
                ++counts["opcode_"+CoreRoi::kind(s.ex_insn)+"_issues"];
                if(have_issue[u])++hist[std::string(name(u))+"_issue_gap"][now-last_issue[u]];
                last_issue[u]=now;have_issue[u]=true;
            }
        }
    }
    void write(std::ostream& out) const {
        out<<"{\n\"scope\":\"Read-only ROI counters. Opportunity counts overlap and are not saved cycles. Latencies count low-edge samples from accepted issue to first valid/grant; include only pairs inside ROI, excluding flush-cancelled pairs.\",\n\"cycles\":"<<cycles<<",\n\"counts\":{";
        bool first=true;for(const auto& kv:counts){out<<(first?"":",")<<"\n\""<<kv.first<<"\":"<<kv.second;first=false;}
        out<<"\n},\n\"histograms\":{";first=true;
        for(const auto& kv:hist){out<<(first?"":",")<<"\n\""<<kv.first<<"\":{";first=false;bool inner=true;
            for(const auto& bin:kv.second){out<<(inner?"":",")<<"\""<<bin.first<<"\":"<<bin.second;inner=false;}out<<"}";}
        out<<"\n}\n}\n";
    }
};
}
#endif
