// Reuse the original pin-driven fixture and unchanged A/B safety cases.
#define main retained_ab_main
#include "test_lsu_ab.cpp"
#undef main

static bool arbitration;

static void complete_store(Fixture& f, unsigned tag, bool error) {
    require(f.t.req_valid && f.t.req_write && !f.t.retire_ack,
            "store missing or retired before response");
    f.accepted(tag,true); f.t.rsp_valid=1; f.t.rsp_error=error; f.settle();
    require(bool(f.t.retire_ack)==!error,"store response/retirement order changed");
    f.response(0,error); f.t.retire_valid=0; f.settle();
    if(error) {
        require(f.t.cmp_valid && f.t.cmp_error && f.t.cmp_seq==tag &&
                f.t.cmp_cause==7 && !f.t.cmp_result && f.t.cmp_tval==0x2000,
                "store fault identity changed");
        f.tick();
    }
}

static void competition(bool buffered,bool fp,bool wrap,bool blocked,bool load_error,bool store_error) {
    test_name="competition-"+std::to_string(buffered)+std::to_string(fp)+
        std::to_string(wrap)+std::to_string(blocked)+std::to_string(load_error)+std::to_string(store_error);
    Fixture f; unsigned old=wrap?4094:4,st=wrap?4095:5,ld=wrap?0:6;
    prepare(f,st); if(buffered)f.buffered_load(old,!fp);
    f.load(ld,0x3000,fp,19); f.t.req_ready=!blocked; head(f,st);
    require(f.t.req_valid && bool(f.t.req_write)==!arbitration,
            "first eligible head arbitration differs");
    if(blocked) {
        for(unsigned i=0;i<5;++i) {
            require(f.t.req_valid && bool(f.t.req_write)==!arbitration &&
                    f.t.req_addr==(arbitration?0x3000U:0x2000U) &&
                    f.t.req_mask==15 && !f.t.ready && !f.t.retire_ack,
                    "offered request changed under backpressure");
            f.tick();
        }
        f.t.req_ready=1; f.settle();
    }
    auto load_response=[&]() {
        require(f.t.req_valid && !f.t.req_write && f.t.ready,"eligible load missing");
        f.accepted(ld); f.response(0x2468ace0,load_error);
        require(f.t.cmp_valid && f.t.cmp_seq==ld && f.t.cmp_dst==19 &&
                bool(f.t.cmp_fp)==fp && bool(f.t.cmp_error)==load_error,
                "load completion tag/domain/error changed");
        if(load_error) {
            require(f.t.cmp_cause==5 && f.t.cmp_tval==0x3000 && !f.t.req_valid,
                    "faulting load response was bypassed");
            f.tick();
        }
    };
    if(arbitration) {
        load_response();
        // Keep offering another safe load: the marked store must make progress.
        f.load((ld+1)&4095,0x3004,!fp,21);
        require(f.t.req_valid && f.t.req_write && !f.t.ready,
                "marked store yielded a second load");
        complete_store(f,st,store_error);
    } else {
        complete_store(f,st,store_error);
        f.load(ld,0x3000,fp,19); load_response(); f.tick();
    }
    require(f.completions[ld]==1 && f.completions[st]==unsigned(store_error) &&
            (!buffered || f.completions[old]==1),"competition lost or duplicated completion");
    pass();
}

static void safety_guard(const std::string& kind) {
    test_name="arbitration-safety-"+kind; Fixture f;
    prepare(f,5,0x2000,0x89abcdef,kind=="partial"?0:2);
    if(kind=="unresolved") {
        f.t.disp_valid=1; f.t.disp_seq=7; f.t.disp_idx=7;
        f.tick(); f.t.disp_valid=0;
    }
    f.load(9,(kind=="forward" || kind=="partial")?0x2000:kind=="misaligned"?0x3001:0x3000);
    if(kind=="no-load")f.t.agu_valid=0;
    head(f,5);
    require(f.t.req_valid && f.t.req_write && f.t.req_addr==0x2000,
            "unsafe or internal load preempted head store");
    if(kind=="unresolved" || kind=="partial")require(!f.t.ready,"dependent load was consumed");
    pass();
}

static void held_recovery(const std::string& kind) {
    test_name="arbitration-held-"+kind; Fixture f; prepare(f,5);
    f.load(6,0x3000); f.t.req_ready=0; head(f,5); f.tick();
    if(kind=="reset")f.t.rst=1;
    else if(kind=="flush") {f.t.flush_valid=1;f.t.flush_seq=5;}
    else f.t.run=0;
    f.settle(); require(!f.t.req_valid,"recovery admitted a request");f.tick();
    f.t.rst=0;f.t.flush_valid=0;f.t.run=1;f.t.agu_valid=0;f.t.req_ready=1;f.settle();
    if(kind=="reset")require(!f.t.req_valid && !f.t.pending_valid,"reset retained request ownership");
    else complete_store(f,5,false);
    pass();
}

static void late_competitor(bool load_first) {
    test_name=load_first?"held-load-before-head":"held-store-before-load";
    Fixture f;prepare(f,5);f.t.req_ready=0;
    if(load_first)f.load(6,0x3000);else head(f,5);
    f.tick();
    if(load_first)head(f,5);else f.load(6,0x3000);
    bool choose_load=load_first && arbitration;
    for(unsigned i=0;i<4;++i) {
        require(f.t.req_valid && bool(f.t.req_write)==!choose_load &&
                f.t.req_addr==(choose_load?0x3000U:0x2000U),"late competitor changed locked request");
        f.tick();
    }
    f.t.req_ready=1;f.settle();
    if(choose_load) {f.accepted(6);f.response();complete_store(f,5,false);}
    else complete_store(f,5,false);
    pass();
}

int main(int argc,char**argv) {
    Verilated::commandArgs(argc,argv);Verilated::assertOn(true);
    if(argc!=3) {std::cerr<<"usage: unit EXPECT_ARBITRATION TRACE.csv\n";return 2;}
    arbitration=std::string(argv[1])=="1";overlap=true;marking=true;trace.open(argv[2]);
    try {
        // 66 unchanged AB safety/ownership cases; arbitration-specific cases below
        // replace the original first-head store-priority expectations.
        for(bool fp:{false,true})for(bool wrap:{false,true})for(bool blocked:{false,true})handoff(fp,wrap,blocked);
        for(auto kind:{"load-error","flush","recovery"})exclusion(kind);
        store_marking_and_error();load_store_priority();internal_completion(false);internal_completion(true);
        killed_inflight();stream(false,1);
        for(unsigned seed:{0x12345678U,0x000abcdeU,0xf00d1234U})stream(true,seed);
        for(bool u:{false,true}) {
            for(unsigned o=0;o<4;++o)subword_handoff(0,o,u);
            for(unsigned o:{0U,2U})subword_handoff(1,o,u);
        }
        flush_after_handoff();fault_after_handoff();store_handoff_backpressure();
        for(bool fp:{false,true}) {
            for(unsigned o=0;o<4;++o)head_payload(0,o,fp);
            for(unsigned o:{0U,2U})head_payload(1,o,fp);
            head_payload(2,0,fp);
        }
        for(auto kind:{"no-valid","wrong-seq","wrong-idx","unresolved","misaligned","flush","recovery"})head_guard(kind);
        head_blocked_by_load();store_stream(false,1);
        for(unsigned seed:{0x12345678U,0x000abcdeU,0xf00d1234U})store_stream(true,seed);
        for(auto kind:{"load-error","flush","recovery","wrong-idx","wrong-seq"})simultaneous_guard(kind);
        require(pass_count==66,"retained AB case count changed");
        for(bool buffered:{false,true})for(bool fp:{false,true})for(bool wrap:{false,true})
            for(bool blocked:{false,true})for(bool load_error:{false,true})for(bool store_error:{false,true})
                competition(buffered,fp,wrap,blocked,load_error,store_error);
        for(auto kind:{"no-load","forward","partial","unresolved","misaligned"})safety_guard(kind);
        for(auto kind:{"reset","flush","recovery"})held_recovery(kind);
        late_competitor(false);late_competitor(true);
        require(pass_count==140,"complete arbitration case count changed");
        std::cout<<"ALL 140 LSU ARBITRATION CASES PASS\n";
    } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
    return 0;
}
