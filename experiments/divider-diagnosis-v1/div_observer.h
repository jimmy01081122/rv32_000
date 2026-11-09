#ifndef RV32_DIV_OBSERVER_H
#define RV32_DIV_OBSERVER_H
#include <cstdint>
#include <map>
#include <ostream>
#include <stdexcept>
#include <string>
#include "core_roi_profile.h"
namespace DivObserve {
inline void require(bool b,const char* msg) { if(!b)throw std::runtime_error(msg); }
inline bool is_div(uint32_t i) { return (i&0x7f)==0x33 && (i>>25)==1 && ((i>>12)&7)>=4; }
inline uint32_t magnitude(uint32_t a,bool sign) { return sign && (a>>31)?uint32_t(0-a):a; }
inline unsigned clz(uint32_t a) { unsigned n=0;for(uint32_t b=0x80000000;b && !(a&b);b>>=1)++n;return n; }
inline uint32_t result(uint32_t a,uint32_t b,unsigned op) {
    bool sign=op==4 || op==6, rem=op>=6;
    if(!b)return rem?a:0xffffffff;
    uint64_t aa=magnitude(a,sign), bb=magnitude(b,sign);
    uint32_t v=rem?aa%bb:aa/bb;
    bool negative=sign && (rem?(a>>31):((a^b)>>31));
    return negative?uint32_t(0-v):v;
}
inline std::string category(uint32_t a,uint32_t b,unsigned op) {
    bool sign=op==4 || op==6;
    auto aa=magnitude(a,sign),bb=magnitude(b,sign);
    if(!b)return "existing_zero";
    if(sign && a==0x80000000 && b==0xffffffff)return "existing_overflow";
    if(bb==1)return "abs_divisor_one";
    if(aa<bb)return "abs_dividend_less";
    if((bb&(bb-1))==0)return "remaining_power_two";
    return "general";
}
struct Snapshot {
    bool flush=false,request=false,ready=false,valid=false,grant=false;
    unsigned tag=0,rtag=0,pc=0,insn=0,a=0,b=0,value=0;
};
template<class T> Snapshot read(const T& t) {
    Snapshot s;
    s.flush=t.rv32_ooo_core__DOT__flush_valid;
    s.request=t.rv32_ooo_core__DOT__u_int_execute__DOT__div_req_valid;
    s.ready=t.rv32_ooo_core__DOT__u_int_execute__DOT__div_req_ready;
    s.valid=t.rv32_ooo_core__DOT__u_int_execute__DOT__div_rsp_valid;
    s.rtag=t.rv32_ooo_core__DOT__u_int_execute__DOT__u_divider__DOT__rob_tag_q;
    s.value=t.rv32_ooo_core__DOT__u_int_execute__DOT__u_divider__DOT__result_q;
    const auto* cmp=t.rv32_ooo_core__DOT__int_cmp;
    s.grant=s.valid && CoreRoi::bits(cmp,154,1) && CoreRoi::bits(cmp,138,16)==s.rtag;
    if(s.request) {
        const auto* r=t.rv32_ooo_core__DOT__int_ex0_req_q;
        s.tag=CoreRoi::bits(r,284,16);s.insn=CoreRoi::bits(r,337,32);
        s.pc=CoreRoi::bits(r,369,32);s.a=CoreRoi::bits(r,64,32);s.b=CoreRoi::bits(r,32,32);
        require(is_div(s.insn),"divider request opcode/layout mismatch");
        bool sign=(((s.insn>>12)&7)==4 || ((s.insn>>12)&7)==6);
        require(magnitude(s.a,sign)==t.rv32_ooo_core__DOT__u_int_execute__DOT__u_divider__DOT__abs_op0 &&
                magnitude(s.b,sign)==t.rv32_ooo_core__DOT__u_int_execute__DOT__u_divider__DOT__abs_op1,
                "divider operand/layout mismatch");
        if(!s.flush && s.ready) {
            const auto* e=t.rv32_ooo_core__DOT__u_rob__DOT__entries[s.tag&15];
            require(CoreRoi::bits(e,244,1) && CoreRoi::bits(e,227,16)==s.tag &&
                    CoreRoi::bits(e,163,32)==s.insn,"divider request ROB ownership mismatch");
        }
    }
    return s;
}
struct Profile {
    struct Pending {bool valid=false,roi=false,seen=false;unsigned tag=0,pc=0,op=0,want=0;uint64_t cycle=0;};
    Pending pending;uint64_t now=0,cycles=0;bool was_roi=false;
    std::map<std::string,uint64_t> counts;
    std::map<std::string,std::map<uint64_t,uint64_t>> hist;
    void sample(const Snapshot& s,bool roi) {
        ++now;if(roi)++cycles;
        if(was_roi && !roi && pending.valid && pending.roi){++counts["censored_at_roi_end"];pending.roi=false;}
        was_roi=roi;
        if(s.flush) {
            if(pending.valid && pending.roi)++counts["cancelled_by_flush"];
            pending={};if(roi)++counts["flush_cycles"];return;
        }
        if(roi && s.request && !s.ready)++counts["request_not_ready_cycles"];
        if(s.valid) {
            require(pending.valid && pending.tag==s.rtag,"divider completion ownership mismatch");
            require(pending.want==s.value,"divider arithmetic mismatch");
            if(!pending.seen && roi && pending.roi)++hist["issue_to_first_valid"][now-pending.cycle];
            pending.seen=true;
            if(roi)++counts[s.grant?"completion_grants":"completion_blocked_cycles"];
            if(s.grant) {
                if(roi && pending.roi){++hist["issue_to_grant"][now-pending.cycle];++counts["issued_in_roi_completed_in_roi"];}
                pending={};
            }
        }
        if(s.request && s.ready) {
            require(!pending.valid,"divider overlapping single-slot ownership");
            unsigned op=(s.insn>>12)&7;
            pending={true,roi,false,s.tag,s.pc,op,result(s.a,s.b,op),now};
            if(roi) {
                ++counts["accepted_issues"];++counts["opcode_"+std::to_string(op)];
                auto cat=category(s.a,s.b,op);++counts["operands_"+cat];
                ++hist["pc_issues"][s.pc];++hist["pc_"+cat][s.pc];
                bool sign=op==4 || op==6;
                if(cat!="existing_zero" && cat!="existing_overflow")
                    ++hist["non_special_abs_dividend_leading_zeros"][clz(magnitude(s.a,sign))];
            }
        }
    }
    void write(std::ostream& out) const {
        out<<"{\n\"scope\":\"Read-only accepted DIV/REM issues, possibly speculative. Disjoint operand categories in stated priority; not saved cycles. Paired latencies exclude flush/censored pairs.\",\n\"cycles\":"<<cycles<<",\n\"counts\":{";
        bool first=true;for(const auto& kv:counts){out<<(first?"":",")<<"\n\""<<kv.first<<"\":"<<kv.second;first=false;}
        out<<"\n},\n\"histograms\":{";first=true;
        for(const auto& kv:hist){out<<(first?"":",")<<"\n\""<<kv.first<<"\":{";first=false;bool inner=true;
            for(const auto& bin:kv.second){out<<(inner?"":",")<<"\""<<bin.first<<"\":"<<bin.second;inner=false;}out<<"}";}
        out<<"\n}\n}\n";
    }
};
}
#endif
