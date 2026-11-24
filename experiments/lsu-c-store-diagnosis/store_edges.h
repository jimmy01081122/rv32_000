// Passive edge observer for the generated C model. All timestamps use the
// low-phase sample immediately before the rising edge which performs the event.
#pragma once
#include "core_roi_profile.h"
#include <array>
#include <cstdlib>
#include <fstream>
#include <map>
#include <stdexcept>

namespace StoreEdges {
using CoreRoi::bits;
using Tick = int64_t;

struct Store {
    unsigned tag = 0;
    uint32_t insn = 0, pc = 0, addr = 0, data = 0, mask = 0;
    Tick base = -1, value = -1, agu = -1, head = -1, eligible = -1, request = -1, response = -1;
    bool error = false;
};

inline bool store_op(uint32_t insn) {
    return (insn & 127) == 0x23 || (insn & 127) == 0x27;
}

class Observer {
    std::array<Store,16> slots{};
    std::map<std::string, uint64_t> counts;
    std::map<std::string, unsigned> examples;
    std::ofstream samples;
    std::string path;
    bool whole, active = false, head_store = false, ack = false;
    unsigned head_tag = 0;
    Tick tick = 0;

    void require(bool ok, const char* msg) const {
        if (!ok) throw std::runtime_error(std::string(msg) + " at cycle " + std::to_string(tick));
    }
    Store& get(unsigned tag) {
        auto& s = slots[tag & 15];
        require(s.tag == tag && store_op(s.insn), "store tag does not match dispatch");
        return s;
    }
    void count(const std::string& name) { if (active) ++counts[name]; }
    void gap(const char* name, Tick start, Tick end) {
        require(start >= 0 && end >= start, name);
        if (active) counts[name] += end - start;
    }
    void example(const Store& s, const std::string& kind) {
        if (active && examples[kind]++ < 3)
            samples << kind << ',' << s.pc << ',' << s.tag << ',' << s.base << ',' << s.value
                    << ',' << s.agu << ',' << s.head << ',' << s.eligible << ',' << s.request
                    << ',' << s.response << ',' << tick << ',' << s.addr << ',' << s.data
                    << ',' << s.mask << '\n';
    }
public:
    explicit Observer(const char* output) : path(output ? output : ""), whole(std::getenv("STORE_EDGES_WHOLE") != nullptr) {
        if (!path.empty()) {
            samples.open(path + "/examples.csv");
            samples.exceptions(std::ios::badbit | std::ios::failbit);
            samples << "kind,pc,tag,base_operand_ready,data_operand_ready,agu_capture,first_head,"
                       "first_authorized,request,response,retire_or_trap,addr,data,mask\n";
        }
    }

    template<class T> void sample(const T& t, bool roi, Tick now) {
        if (path.empty()) return;
        tick = now;
        active = whole || roi;
        count("cycles");
#define CORE(name) t.rv32_ooo_core__DOT__##name
#define LSU(name) t.rv32_ooo_core__DOT__u_lsu__DOT__##name
        if (CORE(rob_alloc_valid) && CORE(rob_alloc_ready) && !CORE(flush_valid)) {
            unsigned tag = CORE(rob_alloc_tag);
            auto& s = slots[tag & 15];
            s = Store{};
            s.tag = tag;
            if (CORE(int_disp_valid)) {
                s.insn = bits(CORE(int_disp_uop), 241, 32);
                s.pc = bits(CORE(int_disp_uop), 273, 32);
            }
        }
        const auto* h = CORE(u_rob__DOT__head_entry);
        head_tag = bits(h, 227, 16);
        head_store = CORE(u_rob__DOT__rob_head_valid) && !CORE(u_rob__DOT__current_state) &&
                     store_op(bits(h, 163, 32));
        ack = CORE(sq_retire_ack);
        int head_iq_ready = -1;
        for (const auto& entry : CORE(u_int_iq__DOT__entries)) {
            if (!bits(entry, 307, 1) || !store_op(bits(entry, 243, 32))) continue;
            auto& s = get(bits(entry, 190, 16));
            require(s.insn == bits(entry, 243, 32) && s.pc == bits(entry, 275, 32), "issue queue identity");
            unsigned ready = bits(entry, 0, 2);
            if ((ready & 2) && s.base < 0) s.base = tick;
            if ((ready & 1) && s.value < 0) s.value = tick;
            if (head_store && s.tag == head_tag) head_iq_ready = int(ready);
        }
        const auto* agu = CORE(int_ex0_req_q);
        if (CORE(agu_valid) && store_op(bits(agu, 337, 32)) && !CORE(flush_valid) &&
            (LSU(sq_matched) || LSU(sq_has_free))) {
            auto& s = get(bits(agu, 284, 16));
            require(s.base >= 0 && s.value >= 0 && s.pc == bits(agu,369,32), "AGU before both operands");
            if (s.agu < 0) s.agu = tick;
            s.addr = CORE(agu_addr);
            unsigned bytes = 1u << ((s.insn >> 12) & 3);
            unsigned offset = s.addr & 3;
            s.mask = (((1u << bytes) - 1) << offset) & 15;
            uint32_t raw = bits(agu,32,32);
            s.data = bytes == 4 ? raw : (raw & (bytes == 2 ? 65535u : 255u)) << (8 * offset);
        }
        if (head_store) {
            auto& s = get(head_tag);
            require(s.insn == bits(h,163,32) && s.pc == bits(h,195,32), "ROB head identity");
            if (s.head < 0) s.head = tick;
            if (!CORE(u_rob__DOT__rob_head_completed)) {
                if (s.agu == tick && s.tag == bits(agu,284,16) && CORE(agu_valid) &&
                    !LSU(agu_misaligned) && LSU(sq_matched) && !CORE(flush_valid) &&
                    !t.dmem_req_valid && t.dmem_req_ready && !LSU(in_flight_valid) &&
                    LSU(response_slot_available)) count("head_capture_port_free");
                static const char* const reason[] = {"pre_both_missing","pre_base_missing","pre_data_missing","pre_iq_ready"};
                count(head_iq_ready >= 0 ? reason[head_iq_ready] :
                      s.agu == tick ? "pre_agu_capture" : "pre_outside_iq");
            }
        }
        const bool read = t.dmem_req_valid && t.dmem_req_ready && !t.dmem_req_wen;
        const bool write = t.dmem_req_valid && t.dmem_req_ready && t.dmem_req_wen;
        const bool rsp = t.dmem_rsp_valid && t.dmem_rsp_ready;
        if (LSU(head_store_send)) {
            auto& s = get(head_tag);
            require(head_store && s.agu >= 0 && s.agu < tick, "authorization before SQ capture");
            if (s.eligible < 0) s.eligible = tick;
        }
        if (CORE(sq_retire_valid) && !ack) {
            require(head_store, "store wait outside head");
            const char* reason;
            if (write) reason = "issue_write";
            else if (read) reason = LSU(load_request_held) ? "yield_held_read" : "yield_new_read";
            else if (LSU(in_flight_valid) && LSU(in_flight_is_store)) reason = "pending_store";
            else if (LSU(in_flight_valid)) reason = rsp ? "load_response_edge" : "pending_load";
            else if (t.dmem_req_valid && !t.dmem_req_ready) reason = "request_backpressure";
            else reason = "other";
            count(std::string("wait_") + reason);
            if (LSU(retire_sq_match) && !bits(LSU(sq)[LSU(retire_sq_idx)],2,1))
                count(std::string("unmarked_") + reason);
        }
        if (write) {
            const auto* sq = LSU(sq)[LSU(send_sq_idx)];
            auto& s = get(bits(sq,113,16));
            require(head_store && head_tag == s.tag && s.eligible >= 0 && s.request < 0 &&
                    bits(sq,112,1) && t.dmem_req_addr == (s.addr & ~3u) &&
                    t.dmem_req_byte_en == s.mask && t.dmem_req_wdata == s.data, "store request or payload");
            s.request = tick;
            count("write");
        }
        if (rsp && LSU(in_flight_valid) && LSU(in_flight_is_store)) {
            auto& s = get(LSU(in_flight_rob_tag));
            require(s.request >= 0 && s.response < 0 && s.request < tick && head_store &&
                    s.tag == head_tag && bool(t.dmem_rsp_error) != ack, "store response or acknowledgement");
            s.response = tick;
            s.error = t.dmem_rsp_error;
            count(s.error ? "response_error" : "response_ok");
        }
#undef CORE
#undef LSU
    }

    template<class T> void finish(const T& t, bool retired, bool trapped, uint32_t pc, uint32_t insn) {
        if (path.empty() || !(retired || trapped) || !store_op(insn)) return;
        auto& s = get(head_tag);
        require(head_store && pc == s.pc && insn == s.insn && !(retired && trapped), "registered event identity");
        if (trapped) {
            require(!bits(t.commit_trace,137,1), "fault committed a memory write");
            if (s.error) {
                require(bits(t.commit_trace,37,32) == 7 && bits(t.commit_trace,5,32) == s.addr, "store fault cause/tval");
                gap("fault_response_to_trap_cycles", s.response, tick);
                count("fault_traps");
                example(s,"access_fault");
            } else {
                require(s.request < 0, "trap with unaccounted write");
                count("local_traps");
            }
            return;
        }
        require(ack && !s.error && bits(t.commit_trace,137,1) &&
                bits(t.commit_trace,105,32) == s.addr && bits(t.commit_trace,101,4) == s.mask &&
                bits(t.commit_trace,69,32) == s.data, "registered store commit payload");
        gap("operands_to_agu_cycles", std::max(s.base,s.value), s.agu);
        gap("head_to_authorized_cycles", s.head, s.eligible);
        gap("authorized_to_request_cycles", s.eligible, s.request);
        gap("request_to_response_cycles", s.request, s.response);
        gap("response_to_retire_cycles", s.response, tick);
        if (active) {
            counts["base_lead_cycles"] += std::max<Tick>(0, s.value - s.base);
            counts["data_lead_cycles"] += std::max<Tick>(0, s.base - s.value);
        }
        count("stores");
        count(s.base < s.value ? "base_first" : s.base > s.value ? "data_first" : "operands_together");
        count(s.request == s.eligible ? "first_edge_request" : "delayed_request");
        example(s, s.request == s.eligible ? "first_edge" : "delayed");
    }
    void save() {
        if (path.empty()) return;
        std::ofstream output(path + "/counts.csv");
        output.exceptions(std::ios::badbit | std::ios::failbit);
        output << "name,count\n";
        for (const auto& row : counts) output << row.first << ',' << row.second << '\n';
        samples.close();
    }
};
}
