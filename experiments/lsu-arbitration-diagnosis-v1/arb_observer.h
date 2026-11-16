#ifndef ARB_OBSERVER_H
#define ARB_OBSERVER_H
#include <array>
#include <algorithm>
#include <fstream>
#include <stdexcept>
#include "core_roi_profile.h"

// Read-only low-edge snapshots plus the actual registered retirement.
// Packed fields are retained un-decoded for independent review. Little-endian
// uint32 words, 88 words per ROI cycle; schema.json defines every offset.
namespace ArbObserve {
struct Profile {
    std::ofstream out;
    std::array<uint32_t,88> row{};
    bool pending=false;
    explicit Profile(const std::string& path) {
        if(!path.empty()) {
            out.open(path,std::ios::binary);
            if(!out)throw std::runtime_error("Cannot open arbitration observation");
        }
    }
    template<class T> void sample(const T& t,bool active) {
        if(!out.is_open() || !active)return;
        row.fill(0);pending=true;
        auto flag=[&](unsigned bit,bool value) {row[bit/32]|=uint32_t(value)<<(bit%32);};
#define CORE(name) t.rv32_ooo_core__DOT__##name
#define LSU(name) t.rv32_ooo_core__DOT__u_lsu__DOT__##name
        flag(0,CORE(u_rob__DOT__can_retire));flag(1,CORE(u_rob__DOT__rob_head_completed));
        flag(2,CORE(flush_valid));flag(3,CORE(sq_retire_valid));flag(4,CORE(sq_retire_ack));
        flag(5,t.dmem_req_valid);flag(6,t.dmem_req_ready);flag(7,t.dmem_req_wen);
        flag(8,t.dmem_rsp_valid);flag(9,t.dmem_rsp_ready);flag(10,t.dmem_rsp_error);
        flag(11,CORE(agu_valid));flag(12,LSU(agu_misaligned));flag(13,LSU(effective_fwd_valid));
        flag(14,LSU(load_stall_unresolved));flag(15,LSU(load_stall_partial));
        flag(16,LSU(sq_has_send));flag(17,LSU(head_store_send));
        flag(18,LSU(in_flight_valid));flag(19,LSU(in_flight_is_store));
        flag(20,LSU(rsp_buf_valid));flag(21,LSU(rsp_buf_ack));flag(22,LSU(rsp_buf_error));
        flag(23,CORE(ren_valid));flag(24,CORE(ren_ready));flag(25,CORE(dec_valid));flag(26,CORE(dec_ready));
        flag(27,CORE(int_disp_valid));flag(28,CORE(int_disp_ready));
        flag(29,CORE(fp_disp_valid));flag(30,CORE(fp_disp_ready));flag(31,CORE(ex0_in_ready));
        flag(32,CORE(int_ex0_valid_q));flag(33,CORE(ex0_out_valid));flag(34,CORE(fp_ex0_valid_q));
        flag(35,CORE(fp_target_ready));flag(36,CORE(fp_heavy_issue_valid));flag(37,CORE(u_fp_execute__DOT__can_accept));
        flag(38,CORE(fp_heavy_cmp_ready));
#if OBSERVER_ARB
        flag(39,LSU(load_request_held));
#endif
        flag(40,LSU(retire_sq_match));flag(41,CORE(rob_alloc_valid));flag(42,CORE(rob_alloc_ready));
        flag(43,CORE(fp_ex0_in_ready));
        row[2]=t.dmem_req_addr;row[3]=CORE(agu_addr);
        row[4]=uint32_t(LSU(in_flight_rob_tag))|(uint32_t(LSU(rsp_buf_rob_tag))<<16);
        row[5]=uint32_t(CORE(u_rob__DOT__rob_count))|(uint32_t(CORE(u_rob__DOT__current_state))<<8)|
            (uint32_t(LSU(send_sq_idx))<<16)|(uint32_t(LSU(retire_sq_idx))<<20);
        std::copy_n(CORE(u_rob__DOT__head_entry),8,row.begin()+6);
        std::copy_n(CORE(int_ex0_req_q),13,row.begin()+14);
        std::copy_n(LSU(sq)[LSU(send_sq_idx)],5,row.begin()+27);
        std::copy_n(CORE(int_issue_uop),10,row.begin()+32);
        std::copy_n(CORE(fp_issue_uop),10,row.begin()+42);
        std::copy_n(CORE(ld_cmp),5,row.begin()+52);
        std::copy_n(CORE(int_cmp),5,row.begin()+57);
        row[65]=uint32_t(CORE(u_int_iq__DOT__ready_mask))|
            (uint32_t(CORE(u_fp_iq__DOT__ready_mask))<<8)|(uint32_t(CORE(u_fp_iq__DOT__num_valid))<<16);
        std::copy_n(CORE(fp_cmp_q),5,row.begin()+66);
        std::copy_n(CORE(fp_ex0_req_q),13,row.begin()+71);
        row[84]=t.dmem_req_wdata;row[85]=t.dmem_req_byte_en;row[86]=t.dmem_rsp_rdata;
#undef CORE
#undef LSU
    }
    void finish(bool retired,uint32_t pc,uint32_t insn) {
        if(!pending)return;
        if(retired!=bool(row[0]&1) || (retired &&
           (pc!=CoreRoi::bits(row.data()+6,195,32) || insn!=CoreRoi::bits(row.data()+6,163,32))))
            throw std::runtime_error("Arbitration observation/registered commit mismatch");
        row[62]=retired;row[63]=pc;row[64]=insn;
        out.write(reinterpret_cast<const char*>(row.data()),row.size()*sizeof(uint32_t));
        if(!out)throw std::runtime_error("Arbitration observation write failed");
        pending=false;
    }
};
}
#endif
