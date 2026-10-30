#include "fp_observer.h"
#include <cassert>
#include <iostream>
// Deliberately independent fake signal packet, not a live CPU model. Negative
// controls ensure a wrong packed offset/class/owner is rejected, not zeroed.
struct Mock {
    bool rv32_ooo_core__DOT__flush_valid=false;
    bool rv32_ooo_core__DOT__fp_ex0_valid_q=true;
    bool rv32_ooo_core__DOT__fp_target_ready=true;
    bool rv32_ooo_core__DOT__fp_ex0_in_ready=true;
    bool rv32_ooo_core__DOT__u_fp_simple__DOT__can_accept=true;
    bool rv32_ooo_core__DOT__u_fp_execute__DOT__can_accept=true;
    bool rv32_ooo_core__DOT__fp_divsqrt_issue_ready=true;
    bool rv32_ooo_core__DOT__u_fp_simple__DOT__holding_valid=false;
    bool rv32_ooo_core__DOT__u_fp_execute__DOT__holding_valid=false;
    bool rv32_ooo_core__DOT__fp_divsqrt_cmp_valid=false;
    bool rv32_ooo_core__DOT__fp_simple_cmp_ready=false;
    bool rv32_ooo_core__DOT__fp_heavy_cmp_ready=false;
    bool rv32_ooo_core__DOT__fp_divsqrt_cmp_ready=false;
    unsigned rv32_ooo_core__DOT__u_fp_iq__DOT__ready_mask=1;
    unsigned rv32_ooo_core__DOT__u_rob__DOT__current_state=0;
    uint32_t rv32_ooo_core__DOT__u_fp_simple__DOT__holding_data[5]={};
    uint32_t rv32_ooo_core__DOT__u_fp_execute__DOT__holding_data[5]={};
    uint32_t rv32_ooo_core__DOT__fp_divsqrt_cmp_data[5]={};
    uint32_t rv32_ooo_core__DOT__fp_ex0_req_q[13]={};
    uint32_t rv32_ooo_core__DOT__u_fp_iq__DOT__entries[4][10]={};
    uint32_t rv32_ooo_core__DOT__u_rob__DOT__entries[16][8]={};
};
void put(uint32_t* p,unsigned offset,unsigned width,uint32_t value){
    for(unsigned i=0;i<width;++i){auto bit=offset+i;p[bit/32]=(p[bit/32]&~(1u<<(bit%32)))|(((value>>i)&1u)<<(bit%32));}
}
template<class F> void rejects(F f){bool rejected=false;try{f();}catch(const std::runtime_error&){rejected=true;}assert(rejected);}
int main(){
    Mock m;const unsigned tag=0x31, insn=0xd0000053; // FCVT.S.W is arithmetic.
    auto* ex=m.rv32_ooo_core__DOT__fp_ex0_req_q;
    put(ex,272,4,11);put(ex,284,16,tag);put(ex,337,32,insn);
    auto* iq=m.rv32_ooo_core__DOT__u_fp_iq__DOT__entries[0];
    put(iq,308,1,1);put(iq,179,4,11);put(iq,191,16,tag);put(iq,244,32,insn);put(iq,0,3,7);
    auto* owner=m.rv32_ooo_core__DOT__u_rob__DOT__entries[tag&15];
    put(owner,244,1,1);put(owner,227,16,tag);put(owner,163,32,insn);
    auto s=FpObserve::read(m);assert(s.ex_unit==1&&s.iq_units[0]==1&&s.iq_mask==1);
    put(iq,179,4,10);rejects([&]{FpObserve::read(m);});put(iq,179,4,11);
    put(owner,227,16,tag^16);rejects([&]{FpObserve::read(m);});put(owner,227,16,tag);
    m.rv32_ooo_core__DOT__fp_target_ready=false;rejects([&]{FpObserve::read(m);});m.rv32_ooo_core__DOT__fp_target_ready=true;
    m.rv32_ooo_core__DOT__u_fp_iq__DOT__ready_mask=0;rejects([&]{FpObserve::read(m);});m.rv32_ooo_core__DOT__u_fp_iq__DOT__ready_mask=1;
    rejects([]{FpObserve::unit(0);});
    FpObserve::Profile p;
    FpObserve::Snapshot bad;bad.valid[2]=true;bad.tags[2]=tag;
    rejects([&]{p.sample(bad,true);});
    assert(FpObserve::instruction_unit(0xe0000053)==0); // FMV.X.W
    assert(FpObserve::instruction_unit(0x18000053)==2); // FDIV.S
    assert(FpObserve::instruction_unit(0x00000043)==1); // FMADD.S
    std::cout<<"adapter positive + 6 negative controls PASS\n";
}
