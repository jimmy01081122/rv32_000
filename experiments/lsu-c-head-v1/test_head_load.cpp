#include "Vhead_load_top.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

static unsigned long ticks = 0;
double sc_time_stamp() { return double(ticks); }

static void check(bool ok, const char* label) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", label); std::exit(1); }
}
struct Fixture {
    Vhead_load_top top;
    void tick() {
        ++ticks; top.clk = 0; top.eval(); top.clk = 1; top.eval(); top.clk = 0; top.eval();
    }
    void reset() {
        top.alloc = top.preview = top.completion = top.fault = 0;
        top.store_ack = top.store_op = 0;
        top.rst = 1; tick(); top.rst = 0; top.eval();
    }
    unsigned allocate(bool load, bool fp, bool dest, bool store = false) {
        top.load_op = load; top.fp_dest = fp; top.dst_valid = dest; top.store_op = store;
        top.alloc = 1; top.eval(); check(top.ready, "allocation refused");
        unsigned tag = top.next_tag; tick(); top.alloc = 0; top.eval(); return tag;
    }
    void response(unsigned tag, bool preview, bool fault = false) {
        top.tag = tag; top.data = 0xc37a80f1U ^ tag;
        top.completion = 1; top.preview = preview; top.fault = fault; top.eval();
    }
    void idle() { top.completion = top.preview = top.fault = 0; top.eval(); }

    void exercise(bool early) {
        for (int mode = 0; mode < 3; ++mode) {
            reset();
            auto tag = allocate(true, mode == 1, mode != 2);
            response(tag ^ 16, true); check(!top.retiring, "stale sequence"); tick();
            response(tag ^ 1, true); check(!top.retiring, "wrong slot"); tick();
            response(tag, true); check(bool(top.retiring) == early, "head response timing");
            tick(); idle();
            if (!early) { check(top.retiring && !top.trace_retire, "parent completion timing"); tick(); }
            check(top.trace_retire && !top.trace_trap && top.event_order == 0, "single ordered retirement");
            check(top.trace_int == (mode == 0) && top.trace_fp == (mode == 1), "destination domain/x0");
            if (mode != 2) check(top.trace_data == (0xc37a80f1U ^ tag), "trace data");
            response(tag, true); tick(); check(!top.trace_retire && !top.retiring, "duplicate response");
        }
        reset();
        auto head = allocate(true, false, true);
        auto younger = allocate(true, true, true);
        response(younger, true); check(!top.retiring, "younger response skipped head"); tick();
        response(head, false); check(!top.retiring, "non-buffered completion retired early"); tick(); idle();
        check(top.retiring, "registered completion missing"); tick();
        check(top.trace_int && top.event_order == 0 && top.retiring, "older completion order"); tick();
        check(top.trace_fp && top.trace_data == (0xc37a80f1U ^ younger) && top.event_order == 1, "younger completion order");

        reset(); head = allocate(true, false, true); younger = allocate(true, true, true);
        response(head, false, true); check(!top.retiring && !top.trapping, "fault response edge"); tick();
        response(younger, true); check(top.trapping && !top.retiring, "older fault takes priority"); tick();
        check(top.trace_trap && !top.trace_retire && top.trace_cause == 5 && top.trace_tval == 0x40001234, "precise trap trace");
        check(!top.retiring && !top.ready, "recovery"); tick();
        check(!top.trace_retire && !top.retiring, "flushed younger response");

        reset();
        unsigned tags[16];
        for (unsigned i = 0; i < 16; ++i) tags[i] = allocate(true, false, true);
        check(!top.ready, "full ROB accepted another allocation");
        for (unsigned i = 0; i < 16; ++i) {
            response(tags[i], true);
            check(bool(top.retiring) == early, "head response timing in full-turn traversal");
            tick(); idle();
            if (!early) tick();
            check(top.trace_retire && top.event_order == i, "ring retirement order");
        }
        head = allocate(true, false, true);
        check((head & 15) == (tags[0] & 15) && head != tags[0], "slot reuse setup");
        response(tags[0], true); tick();
        check(!top.trace_retire && !top.retiring, "stale completion after slot reuse");
        response(head, true); tick(); idle();
        if (!early) tick();
        check(top.trace_retire && top.event_order == 16, "reused slot retirement");

        reset(); head = allocate(false, false, false, true);
        response(head, true); check(!top.retiring, "store entered early path"); tick(); idle();
        check(!top.retiring, "unacknowledged store"); top.store_ack = 1; top.eval();
        check(top.retiring, "acknowledged store"); tick();
        reset(); head = allocate(true, false, true); response(head, true); top.rst = 1; top.eval();
        check(!top.retiring, "reset preview"); tick(); check(!top.trace_retire, "reset trace");
        std::puts("PASS head-load timing, tags, destination, order, store, fault, recovery and reset");
    }
};

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    Verilated::commandArgs(argc, argv);
    Fixture fixture;
    fixture.exercise(std::strcmp(argv[1], "candidate") == 0);
    return 0;
}
