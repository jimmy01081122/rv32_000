#ifndef CORE_ROI_PROFILE_H
#define CORE_ROI_PROFILE_H
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <map>
#include <string>
#include "fp_roi_profile.h"

// Read-only host instrumentation for pinned Verilator 4.038 / current packed
// layouts. ROB head: 245 bits; FP IQ entry: 309 bits, uop: 305 bits.
// sample() runs after low-edge combinational eval, before the rising edge.
// finish_cycle() cross-checks that head decode against the registered commit.
namespace CoreRoi {
inline uint32_t bits(const uint32_t* words, unsigned low, unsigned width) {
    uint64_t value = words[low / 32] >> (low % 32);
    if ((low % 32) + width > 32) value |= uint64_t(words[low / 32 + 1]) << (32 - low % 32);
    return uint32_t(value) & (width == 32 ? 0xffffffffu : ((1u << width) - 1));
}
inline bool marker(uint32_t insn) { return (insn & 0xfffff07fu) == 0xc0002073u; }
inline bool fma(uint32_t insn) {
    auto op = insn & 127u;
    return ((insn >> 25) & 3u) == 0 && (op == 0x43 || op == 0x47 || op == 0x4b || op == 0x4f);
}
inline std::string kind(uint32_t insn) {
    if (marker(insn)) return "marker";
    if (fma(insn)) return "fma";
    switch (insn & 127u) {
        case 0x07: return "fp_load";
        case 0x27: return "fp_store";
        case 0x03: return "int_load";
        case 0x23: return "int_store";
        case 0x63: return "branch";
        case 0x67: case 0x6f: return "jump";
        case 0x73: return "csr_system";
        case 0x53:
            switch (insn >> 25) {
                case 0: return "fadd";
                case 4: return "fsub";
                case 8: return "fmul";
                case 12: return "fdiv";
                case 44: return "fsqrt";
                default: return "fp_other";
            }
        default: return "integer_other";
    }
}
struct Snapshot {
    bool can_retire = false, completed = false, flush = false;
    bool store_ack_wait = false;
    unsigned store_phase = 0, load_phase = 0, layout_mismatches = 0;
    uint32_t pc = 0, insn = 0;
    unsigned rob_count = 0, state = 0, fp_iq_count = 0, fp_ready_mask = 0;
    bool fp_issue_ready = false, heavy_valid = false, heavy_ready = false;
    bool heavy_completion_blocked = false, fp_ex0_blocked = false;
    bool dmem_pending = false, dmem_read = false, dmem_write = false;
    bool rename_blocked = false, decode_empty = false;
    unsigned fma_src2_only_entries = 0, fma_src01_wait_entries = 0;
    // -1: ROB head not in FP IQ; otherwise readiness mask src0:bit2 .. src2:bit0.
    int head_fp_iq_ready = -1;
};
struct PcStats { uint32_t insn = 0; uint64_t retired = 0, head_wait = 0; };
struct Profile {
    std::map<std::string, uint64_t> partition, overlap, instructions;
    std::map<std::string, uint64_t> store_wait, load_wait;
    std::map<uint32_t, PcStats> pcs;
    uint64_t cycles = 0, trace_mismatches = 0, layout_mismatches = 0;
    Snapshot pending;
    bool pending_valid = false;

    void sample(const Snapshot& s) {
        pending = s; pending_valid = true; ++cycles;
        layout_mismatches += s.layout_mismatches;
        auto k = kind(s.insn);
        std::string bucket;
        if (s.can_retire) bucket = marker(s.insn) ? "retired_marker" : "retired_body";
        else if (s.state != 0) bucket = "recovery";
        else if (!s.rob_count) bucket = "rob_empty";
        else if (s.store_ack_wait) bucket = "store_ack_wait";
        else if (s.completed) bucket = "completed_head_other";
        else bucket = "head_wait_" + k;
        ++partition[bucket];
        if (bucket == "store_ack_wait") {
            const char* phases[] = {"other", "mark_pending", "other_inflight", "load_response_buffer", "request_ready", "response_pending"};
            ++store_wait[phases[s.store_phase]];
        }
        if (bucket == "head_wait_fp_load" || bucket == "head_wait_int_load") {
            const char* phases[] = {"before_external_request_or_forward", "own_external_inflight", "own_response_buffer", "own_forward_buffer"};
            ++load_wait[phases[s.load_phase]];
        }
        if (!s.can_retire && s.rob_count) {
            auto& p = pcs[s.pc]; p.insn = s.insn; ++p.head_wait;
            if (k == "fma" || k == "fadd" || k == "fmul" || k == "fsub" || k == "fp_other") {
                const auto r = s.head_fp_iq_ready;
                ++overlap[r < 0 ? "fp_head_wait_not_in_iq" :
                          (r & 6) != 6 ? "fp_head_wait_src01" :
                          !(r & 1) ? "fp_head_wait_src2_only" : "fp_head_wait_ready_in_iq"];
            }
        }
        overlap["rob_full"] += s.rob_count == 16;
        overlap["rename_blocked"] += s.rename_blocked;
        overlap["decode_empty"] += s.decode_empty;
        overlap["flush"] += s.flush;
        overlap["fp_iq_nonempty_no_ready"] += s.fp_iq_count && !s.fp_ready_mask;
        overlap["fp_iq_ready_downstream_blocked"] += s.fp_ready_mask && !s.fp_issue_ready;
        overlap["fp_iq_issue"] += s.fp_ready_mask && s.fp_issue_ready && !s.flush;
        overlap["heavy_issue"] += s.heavy_valid && s.heavy_ready && !s.flush;
        overlap["heavy_issue_blocked"] += s.heavy_valid && !s.heavy_ready && !s.flush;
        overlap["heavy_completion_blocked"] += s.heavy_completion_blocked;
        overlap["fp_ex0_blocked"] += s.fp_ex0_blocked;
        overlap["dmem_pending"] += s.dmem_pending;
        overlap["dmem_read_accepted"] += s.dmem_read;
        overlap["dmem_write_accepted"] += s.dmem_write;
        overlap["fma_src2_only_entry_cycles"] += s.fma_src2_only_entries;
        overlap["fma_src01_wait_entry_cycles"] += s.fma_src01_wait_entries;
    }
    void finish_cycle(bool retired, uint32_t pc, uint32_t insn) {
        if (!pending_valid) return;
        if (retired != pending.can_retire || (retired && (pc != pending.pc || insn != pending.insn))) ++trace_mismatches;
        if (retired && !marker(insn)) {
            ++instructions[kind(insn)];
            auto& p = pcs[pc]; p.insn = insn; ++p.retired;
        }
        pending_valid = false;
    }
    void write(std::ostream& out) const {
        out << "{\n  \"scope\": \"Commit-delimited ROI; opening marker excluded, closing marker included; overlapping events are not a causal cycle partition\",\n";
        out << "  \"cycles\": " << cycles << ",\n  \"trace_mismatches\": " << trace_mismatches
            << ",\n  \"layout_mismatches\": " << layout_mismatches;
        auto counts = [&](const char* name, const std::map<std::string, uint64_t>& values) {
            out << ",\n  \"" << name << "\": {";
            bool first = true;
            for (const auto& v : values) { out << (first ? "\n" : ",\n") << "    \"" << v.first << "\": " << v.second; first = false; }
            out << "\n  }";
        };
        counts("cycle_partition", partition); counts("overlapping_events", overlap); counts("retired_classes", instructions);
        counts("store_ack_wait_phases", store_wait); counts("load_head_wait_phases", load_wait);
        out << ",\n  \"pcs\": [";
        bool first = true;
        for (const auto& p : pcs) {
            out << (first ? "\n" : ",\n") << "    {\"pc\": \"" << std::hex << std::setw(8) << std::setfill('0') << p.first
                << "\", \"insn\": \"" << std::setw(8) << p.second.insn << "\", \"kind\": \"" << kind(p.second.insn)
                << "\", \"retired\": " << std::dec << p.second.retired << ", \"head_wait\": " << p.second.head_wait << "}";
            first = false;
        }
        out << "\n  ]\n}\n";
    }
};

// Verilator optimized member names are pinned to toolchain.lock. This adapter
// never drives the model; a packed-layout change must update/test these offsets.
template<class T> Snapshot read(const T& t) {
    Snapshot s;
    const auto* head = t.rv32_ooo_core__DOT__u_rob__DOT__head_entry;
    s.pc = bits(head, 195, 32); s.insn = bits(head, 163, 32);
    const auto tag = bits(head, 227, 16);
    s.can_retire = t.rv32_ooo_core__DOT__u_rob__DOT__can_retire;
    s.completed = t.rv32_ooo_core__DOT__u_rob__DOT__rob_head_completed;
    s.rob_count = t.rv32_ooo_core__DOT__u_rob__DOT__rob_count;
    s.state = t.rv32_ooo_core__DOT__u_rob__DOT__current_state;
    s.flush = t.rv32_ooo_core__DOT__flush_valid;
    s.store_ack_wait = t.rv32_ooo_core__DOT__sq_retire_valid && !t.rv32_ooo_core__DOT__sq_retire_ack;
    s.fp_iq_count = t.rv32_ooo_core__DOT__u_fp_iq__DOT__num_valid;
    s.fp_ready_mask = t.rv32_ooo_core__DOT__u_fp_iq__DOT__ready_mask;
    s.fp_issue_ready = t.rv32_ooo_core__DOT__fp_ex0_in_ready;
    s.heavy_valid = t.rv32_ooo_core__DOT__fp_heavy_issue_valid;
    s.heavy_ready = t.rv32_ooo_core__DOT__u_fp_execute__DOT__can_accept;
    s.heavy_completion_blocked = t.rv32_ooo_core__DOT__u_fp_execute__DOT__holding_valid && !t.rv32_ooo_core__DOT__fp_heavy_cmp_ready;
    s.fp_ex0_blocked = t.rv32_ooo_core__DOT__fp_ex0_valid_q && !t.rv32_ooo_core__DOT__fp_target_ready;
    s.dmem_pending = t.rv32_ooo_core__DOT__u_lsu__DOT__in_flight_valid;
    s.dmem_read = t.dmem_req_valid && t.dmem_req_ready && !t.dmem_req_wen;
    s.dmem_write = t.dmem_req_valid && t.dmem_req_ready && t.dmem_req_wen;
    s.rename_blocked = t.rv32_ooo_core__DOT__ren_valid && !t.rv32_ooo_core__DOT__ren_ready;
    s.decode_empty = !t.rv32_ooo_core__DOT__dec_valid && t.rv32_ooo_core__DOT__dec_ready;
    if (s.store_ack_wait && t.rv32_ooo_core__DOT__u_lsu__DOT__retire_sq_match) {
        const auto* slot = t.rv32_ooo_core__DOT__u_lsu__DOT__sq[t.rv32_ooo_core__DOT__u_lsu__DOT__retire_sq_idx];
        s.store_phase = !bits(slot, 2, 1) ? 1 : bits(slot, 1, 1) ? 5 :
                        s.dmem_pending ? 2 : t.rv32_ooo_core__DOT__u_lsu__DOT__rsp_buf_valid ? 3 :
                        s.dmem_write ? 4 : 0;
    }
    if (s.dmem_pending && !t.rv32_ooo_core__DOT__u_lsu__DOT__in_flight_is_store &&
            t.rv32_ooo_core__DOT__u_lsu__DOT__in_flight_rob_tag == tag) s.load_phase = 1;
    if (t.rv32_ooo_core__DOT__u_lsu__DOT__rsp_buf_valid &&
            t.rv32_ooo_core__DOT__u_lsu__DOT__rsp_buf_rob_tag == tag) s.load_phase = 2;
    if (t.rv32_ooo_core__DOT__u_lsu__DOT__fwd_reg_valid &&
            bits(t.rv32_ooo_core__DOT__u_lsu__DOT__fwd_reg_req, 284, 16) == tag) s.load_phase = 3;
    unsigned valid_entries = 0, expected_ready = 0;
    for (unsigned i = 0; i < 4; ++i) {
        const auto* e = t.rv32_ooo_core__DOT__u_fp_iq__DOT__entries[i];
        if (!bits(e, 308, 1)) continue;
        ++valid_entries;
        const unsigned ready = bits(e, 0, 3);
        if (ready == 7 && s.state == 0) expected_ready |= 1u << i;
        const auto entry_tag = bits(e, 191, 16);
        const auto* owner = t.rv32_ooo_core__DOT__u_rob__DOT__entries[entry_tag & 15u];
        if (!bits(owner, 244, 1) || bits(owner, 227, 16) != entry_tag ||
                bits(owner, 195, 32) != bits(e, 276, 32) || bits(owner, 163, 32) != bits(e, 244, 32)) ++s.layout_mismatches;
        if (fma(bits(e, 244, 32))) {
            s.fma_src2_only_entries += (ready & 6) == 6 && !(ready & 1);
            s.fma_src01_wait_entries += (ready & 6) != 6;
        }
        if (bits(e, 191, 16) == tag) s.head_fp_iq_ready = int(ready);
    }
    s.layout_mismatches += valid_entries != s.fp_iq_count;
    s.layout_mismatches += expected_ready != s.fp_ready_mask;
    return s;
}
}
#endif
