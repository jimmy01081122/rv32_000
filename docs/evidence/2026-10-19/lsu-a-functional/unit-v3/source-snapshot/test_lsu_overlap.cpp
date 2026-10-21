#include "Vlsu_overlap_top.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

static bool overlap;
static std::ofstream trace;
static std::string test_name;
static vluint64_t simulation_time = 0;
double sc_time_stamp() { return simulation_time; }
static void require(bool value, const std::string& why) {
    if (!value) throw std::runtime_error(test_name + ": " + why);
}
struct Fixture {
    Vlsu_overlap_top t;
    unsigned cycle = 0;
    std::map<unsigned,unsigned> completions;
    Fixture() {
        t.clk=0; t.rst=1; t.run=1; t.agu_valid=0; t.agu_store=0;
        t.agu_fp=0; t.agu_seq=0; t.agu_dst=0; t.agu_addr=0;
        t.agu_data=0; t.agu_size=2; t.agu_unsigned=0;
        t.retire_valid=0; t.retire_seq=0; t.flush_valid=0; t.flush_seq=0;
        t.req_ready=1; t.rsp_valid=0; t.rsp_error=0; t.rsp_data=0;
        tick(); tick(); t.rst=0; settle(); cycle=0;
    }
    ~Fixture() { t.final(); }
    void settle() { t.clk=0; t.eval(); }
    void tick() {
        settle();
        if (!t.rst) {
            trace << test_name << ',' << cycle << ',' << unsigned(t.req_valid)
                  << ',' << unsigned(t.req_ready) << ',' << unsigned(t.req_write)
                  << ',' << t.req_addr << ',' << unsigned(t.rsp_valid)
                  << ',' << unsigned(t.rsp_ready) << ',' << unsigned(t.cmp_valid)
                  << ',' << t.cmp_seq << ',' << t.cmp_data << ',' << unsigned(t.cmp_error)
                  << ',' << unsigned(t.buffer_valid) << ',' << unsigned(t.buffer_ack)
                  << ',' << unsigned(t.pending_valid) << ',' << t.pending_seq << '\n';
            if (t.cmp_valid) ++completions[t.cmp_seq];
        }
        ++simulation_time; t.clk=1; t.eval();
        ++simulation_time; t.clk=0; t.eval(); ++cycle;
    }
    void load(unsigned seq, unsigned addr=0x1000, bool fp=false, unsigned dst=7) {
        t.agu_valid=1; t.agu_store=0; t.agu_seq=seq; t.agu_addr=addr;
        t.agu_dst=dst; t.agu_fp=fp; t.agu_size=2; settle();
    }
    void store(unsigned seq, unsigned addr=0x2000, unsigned data=0x12345678) {
        t.agu_valid=1; t.agu_store=1; t.agu_seq=seq; t.agu_addr=addr;
        t.agu_data=data; t.agu_size=2; settle();
    }
    void response(unsigned data=0xa1b2c3d4, bool error=false) {
        t.rsp_valid=1; t.rsp_data=data; t.rsp_error=error; settle();
        require(t.rsp_ready, "response not accepted");
        tick(); t.rsp_valid=0; t.rsp_error=0; settle();
    }
    void buffered_load(unsigned seq=10, bool fp=false, bool error=false) {
        load(seq,0x1000,fp,7); require(t.req_valid && t.ready, "first load absent");
        tick(); t.agu_valid=0; settle();
        require(!t.cmp_valid, "external response register bypassed");
        response(0xa1b2c3d4,error);
        require(t.buffer_valid && t.cmp_valid && t.cmp_seq==seq,
                "registered load metadata missing");
    }
    void accepted(unsigned seq, bool store=false) {
        require(t.req_valid && t.req_ready, "request not accepted");
        tick(); t.agu_valid=0; settle();
        require(t.external_inflight && t.pending_valid && t.pending_seq==seq &&
                bool(t.pending_store)==store && !t.buffer_valid,
                "handoff pending ownership wrong");
    }
};
static void pass() { std::cout << "PASS " << test_name << '\n'; }

static void handoff(bool fp, bool wrap, bool blocked) {
    test_name=std::string("load-load-")+(fp?"fp":"int")+(wrap?"-wrap":"")+(blocked?"-backpressure":"");
    Fixture f; unsigned old=wrap?4095:10, next=wrap?0:11;
    f.buffered_load(old,fp); f.load(next,0x1004,!fp,19);
    f.t.req_ready=!blocked; f.settle();
    require(bool(f.t.req_valid)==overlap, "buffer-consume request availability differs");
    require(f.t.cmp_valid && f.t.cmp_seq==old && f.t.cmp_dst==7 &&
            f.t.cmp_data==0xa1b2c3d4 && bool(f.t.cmp_fp)==fp,
            "new request corrupted old completion");
    if (blocked) {
        require(!f.t.ready, "backpressured load consumed"); f.tick();
        require(f.t.req_valid && f.t.req_addr==0x1004, "blocked request lost");
        f.t.req_ready=1; f.settle();
    } else if (!overlap) { f.tick(); }
    f.accepted(next); f.response(0x10203040);
    require(f.t.cmp_valid && f.t.cmp_seq==next && f.t.cmp_dst==19 &&
            f.t.cmp_data==0x10203040 && bool(f.t.cmp_fp)!=fp, "new completion identity wrong");
    f.tick(); f.tick();
    require(f.completions[old]==1 && f.completions[next]==1, "completion duplicated/lost"); pass();
}
static void exclusion(const std::string& kind) {
    test_name=kind; Fixture f;
    f.buffered_load(10,false,kind=="load-error"); f.load(11,0x1004);
    if (kind=="flush") { f.t.flush_valid=1; f.t.flush_seq=9; }
    if (kind=="recovery") f.t.run=0;
    f.settle(); require(!f.t.req_valid, "request admitted on fault/flush/recovery");
    if (kind=="load-error") require(f.t.cmp_error && f.t.cmp_cause==5 && f.t.cmp_tval==0x1000,
                                   "load fault metadata lost");
    if (kind=="flush") require(!f.t.cmp_valid, "flushed completion visible");
    f.tick(); require(!f.t.external_inflight, "excluded request became in-flight"); pass();
}
static void store_marking_and_error() {
    test_name="store-marking-unchanged-and-error"; Fixture f;
    f.store(5); f.tick(); f.t.agu_valid=0; f.t.retire_valid=1; f.t.retire_seq=5; f.settle();
    require(!f.t.req_valid, "B marking bypass was accidentally implemented");
    f.tick(); require(f.t.req_write && f.t.req_data==0x12345678, "store payload wrong");
    f.accepted(5,true); f.t.rsp_valid=1; f.t.rsp_error=1; f.settle();
    require(!f.t.retire_ack, "faulting store retired"); f.response(0,true);
    f.load(6); require(!f.t.req_valid && f.t.cmp_valid && f.t.cmp_seq==5 &&
                      f.t.cmp_error && f.t.cmp_cause==7 && !f.t.cmp_result,
                      "store-fault buffer exclusion/metadata wrong");
    f.tick(); pass();
}
static void load_store_priority() {
    test_name="load-to-marked-store-priority"; Fixture f;
    f.store(5); f.tick(); f.load(10); require(f.t.req_valid && !f.t.req_write,"load not dispatched");
    f.tick(); f.t.agu_valid=0; f.t.retire_valid=1; f.t.retire_seq=5; f.response();
    f.load(11,0x1004); require(bool(f.t.req_valid)==overlap,"store handoff availability wrong");
    require(f.t.cmp_valid && f.t.cmp_seq==10,"old load completion wrong");
    if (!overlap) f.tick();
    require(f.t.req_write && f.t.req_addr==0x2000 && !f.t.ready,"store arbitration or AGU hold wrong");
    f.accepted(5,true); f.t.rsp_valid=1; f.t.rsp_error=0; f.settle();
    require(f.t.retire_ack,"successful store not acknowledged"); f.tick(); f.t.rsp_valid=0; f.settle();
    require(!f.t.cmp_valid,"successful store incorrectly generated load completion"); pass();
}
static void internal_completion(bool misalign) {
    test_name=misalign?"registered-misalign-priority":"registered-forwarding-priority"; Fixture f;
    if (!misalign) { f.store(5); f.tick(); f.t.agu_valid=0; }
    f.buffered_load(2); f.load(10,misalign?0x1001:0x2000);
    require(!f.t.req_valid && f.t.ready && f.t.cmp_seq==2,"internal path acceptance/old priority wrong");
    f.tick(); f.t.agu_valid=0; f.settle();
    require(f.t.cmp_valid && f.t.cmp_seq==10,"internal completion lost");
    if (misalign) require(f.t.cmp_error && f.t.cmp_cause==4 && f.t.cmp_tval==0x1001,"misalign wrong");
    else require(!f.t.cmp_error && f.t.cmp_data==0x12345678,"forwarding wrong");
    f.tick(); pass();
}
static void killed_inflight() {
    test_name="late-response-after-flush"; Fixture f; f.load(10); f.tick(); f.t.agu_valid=0;
    f.t.flush_valid=1; f.t.flush_seq=9; f.tick(); f.t.flush_valid=0; f.settle();
    require(f.t.external_inflight,"flush cancelled physical transaction");
    f.response(); require(!f.t.cmp_valid && !f.t.buffer_valid && !f.t.external_inflight,
                          "killed response escaped"); f.load(20); f.accepted(20); pass();
}
static uint32_t data_for(unsigned index) { return 0x9e3779b9U*(index+1); }
static void stream(bool random, unsigned seed) {
    test_name=random?"random-stream-"+std::to_string(seed):"ideal-stream-3-to-2";
    Fixture f; unsigned issued=0,completed=0,due=0,previous_request=0,pending_index=0;
    bool pending=false; uint32_t rng=seed; std::map<unsigned,unsigned> request_cycle;
    auto next_random=[&]() { rng^=rng<<13; rng^=rng>>17; rng^=rng<<5; return rng; };
    const unsigned count=random?128:16;
    for (unsigned c=0;c<4000 && completed<count;++c) {
        f.t.req_ready=!random || next_random()%4!=0;
        if (issued<count) f.load((4090+issued)&4095,0x1000+4*issued,issued%2,1+issued%47);
        else f.t.agu_valid=0;
        f.t.rsp_valid=pending && c>=due; f.t.rsp_data=data_for(pending_index); f.settle();
        bool receive=f.t.rsp_valid && f.t.rsp_ready, send=f.t.req_valid && f.t.req_ready;
        if (f.t.cmp_valid) {
            unsigned tag=(4090+completed)&4095;
            require(f.t.cmp_seq==tag && f.t.cmp_dst==1+completed%47 &&
                    bool(f.t.cmp_fp)==bool(completed%2) && !f.t.cmp_error &&
                    f.t.cmp_data==data_for(completed),"stream completion data/order/domain wrong");
            if (!random) require(c-request_cycle[tag]==2,"registered completion latency changed");
            ++completed;
        }
        if (receive) pending=false;
        if (send) {
            require(!pending,"more than one physical outstanding request");
            require(!f.t.req_write && f.t.req_addr==0x1000+4*issued,"stream request wrong");
            if (!random && issued) require(c-previous_request==(overlap?2U:3U),"request interval mismatch");
            request_cycle[(4090+issued)&4095]=c; previous_request=c;
            pending=true; pending_index=issued++; due=c+(random?1+next_random()%5:1);
        }
        f.tick();
    }
    require(issued==count && completed==count && !pending,"stream watchdog/loss");
    for (auto item:f.completions) require(item.second==1,"stream duplicate completion");
    std::cout << "STREAM requests=" << issued << " cycles=" << f.cycle
              << " expected_interval=" << (overlap?2:3) << '\n'; pass();
}
int main(int argc,char**argv) {
    Verilated::commandArgs(argc,argv); Verilated::assertOn(true);
    if (argc!=3) { std::cerr<<"usage: unit EXPECT_OVERLAP TRACE.csv\n"; return 2; }
    overlap=std::string(argv[1])=="1"; trace.open(argv[2]);
    trace<<"case,cycle,req_valid,req_ready,req_write,req_addr,rsp_valid,rsp_ready,cmp_valid,cmp_seq,cmp_data,cmp_error,buf_valid,buf_ack,pending_valid,pending_seq\n";
    try {
        for (bool fp:{false,true}) for (bool wrap:{false,true}) for (bool blocked:{false,true}) handoff(fp,wrap,blocked);
        for (auto name:{"load-error","flush","recovery"}) exclusion(name);
        store_marking_and_error(); load_store_priority(); internal_completion(false);
        internal_completion(true); killed_inflight(); stream(false,1);
        for (unsigned seed:{0x12345678U,0x000abcdeU,0xf00d1234U}) stream(true,seed);
        std::cout<<"ALL 20 LSU HANDOFF CASES PASS overlap="<<overlap<<'\n';
    } catch (const std::exception& e) { std::cerr<<"FAIL "<<e.what()<<'\n'; return 1; }
    return 0;
}
