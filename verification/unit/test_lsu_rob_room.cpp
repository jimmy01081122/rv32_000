#define LSU_ROB_ROOM_TEST
#define LSU_ARBITRATION_ENTRY retained_arbitration_main
#include "test_lsu_arbitration.cpp"

static bool room_policy;
static void allocate(Fixture& f) {
    require(f.t.room_alloc_ready,"ROB allocation blocked unexpectedly");
    f.t.room_alloc_valid=1; f.tick(); f.t.room_alloc_valid=0; f.settle();
}
static void fill(Fixture& f,unsigned count) {
    for(unsigned i=0;i<count;++i)allocate(f);
    require(f.t.room_count==count,"actual ROB occupancy differs");
}
static void retire_room_head(Fixture& f,unsigned tag=0) {
    unsigned before=f.t.room_count;
    f.t.room_complete_valid=1; f.t.room_complete_seq=tag; f.t.room_complete_idx=tag&15;
    f.tick(); f.t.room_complete_valid=0; f.tick();
    require(f.t.room_count==before-1,"ROB completion/retirement did not release one slot");
}
static void room_sweep() {
    test_name="real-ROB-threshold-sweep";Fixture f;
    for(unsigned i=0;i<=16;++i) {
        require(f.t.room_count==i && bool(f.t.room_available)==(i<=14),"ROB threshold differs");
        if(i<16)allocate(f);
    }
    for(unsigned i=0;i<16;++i) {
        retire_room_head(f,i);
        require(bool(f.t.room_available)==(f.t.room_count<=14),"ROB threshold differs after retirement");
    }
    fill(f,16); f.t.rst=1; f.tick();f.t.rst=0;f.settle();
    require(f.t.room_count==0 && f.t.room_available,"ROB reset retained pressure");pass();
}
static void simultaneous_room() {
    test_name="real-ROB-simultaneous-allocation-retirement";Fixture f;fill(f,14);
    f.t.room_complete_valid=1;f.t.room_complete_seq=0;f.t.room_complete_idx=0;f.tick();
    f.t.room_complete_valid=0;f.t.room_alloc_valid=1;f.tick();f.t.room_alloc_valid=0;f.settle();
    require(f.t.room_count==14 && f.t.room_available,"simultaneous ROB event changed threshold");pass();
}
static void pressure_competition(unsigned used,bool buffered,bool fp,bool wrap,bool blocked,bool load_error,bool store_error) {
    test_name="room-competition-"+std::to_string(used)+"-"+std::to_string(buffered)+std::to_string(fp)+std::to_string(wrap)+std::to_string(blocked)+std::to_string(load_error)+std::to_string(store_error);
    Fixture f;fill(f,used);unsigned old=wrap?4094:4,st=wrap?4095:5,ld=wrap?0:6;
    prepare(f,st);if(buffered)f.buffered_load(old,!fp);
    f.load(ld,0x3000,fp,19);f.t.req_ready=!blocked;head(f,st);
    bool choose=!room_policy || used<=14;
    require(f.t.req_valid && bool(f.t.req_write)==!choose,"ROB pressure decision differs");
    if(blocked) {
        for(unsigned i=0;i<5;++i) {
            require(f.t.req_valid && bool(f.t.req_write)==!choose && f.t.req_addr==(choose?0x3000U:0x2000U) && f.t.req_mask==15 && !f.t.ready && !f.t.retire_ack,"pressure request changed under backpressure");
            f.tick();
        }
        f.t.req_ready=1;f.settle();
    }
    auto load_response=[&]() {
        require(f.t.req_valid && !f.t.req_write && f.t.ready,"eligible pressure load missing");
        f.accepted(ld);f.response(0x2468ace0,load_error);
        require(f.t.cmp_valid && f.t.cmp_seq==ld && f.t.cmp_dst==19 && bool(f.t.cmp_fp)==fp && bool(f.t.cmp_error)==load_error,"pressure load completion differs");
        if(load_error) {
            require(f.t.cmp_cause==5 && f.t.cmp_tval==0x3000 && !f.t.req_valid,"fault bypassed pressure gate");f.tick();
        }
    };
    if(choose) {
        load_response();f.load((ld+1)&4095,0x3004,!fp,21);
        require(f.t.req_valid && f.t.req_write && !f.t.ready,"pressure marked store yielded twice");
        complete_store(f,st,store_error);
    } else {
        complete_store(f,st,store_error);f.load(ld,0x3000,fp,19);load_response();f.tick();
    }
    require(f.completions[ld]==1 && f.completions[st]==unsigned(store_error) && (!buffered || f.completions[old]==1),"pressure completion lost/duplicated");pass();
}
static void held_load_pressure_rises(unsigned target) {
    test_name="held-load-pressure-rises-to-"+std::to_string(target);Fixture f;fill(f,14);prepare(f,5);
    f.load(6,0x3000);f.t.req_ready=0;head(f,5);f.tick();
    for(unsigned i=14;i<target;++i) {
        allocate(f);require(f.t.req_valid && !f.t.req_write && f.t.req_addr==0x3000,"held load revoked when ROB filled");
    }
    f.t.req_ready=1;f.settle();f.accepted(6);f.response();complete_store(f,5,false);pass();
}
static void held_store_pressure_falls() {
    test_name="held-store-pressure-falls-to-14";Fixture f;fill(f,15);prepare(f,5);
    f.load(6,0x3000);f.t.req_ready=0;head(f,5);f.tick();retire_room_head(f);
    require(f.t.room_available && f.t.req_valid && bool(f.t.req_write)==room_policy && f.t.req_addr==(room_policy?0x2000U:0x3000U),"lower pressure replaced offered request");
    f.t.req_ready=1;f.settle();
    if(!room_policy){f.accepted(6);f.response();}
    complete_store(f,5,false);pass();
}
static void uncontended_pressure(unsigned used,bool late_store) {
    test_name="pressure-uncontended-"+std::to_string(used)+"-"+std::to_string(late_store);Fixture f;fill(f,used);
    if(late_store)prepare(f,5);
    f.load(6,0x3000);f.t.req_ready=0;f.settle();
    require(f.t.req_valid && !f.t.req_write,"pressure blocked uncontended load");f.tick();
    if(late_store)head(f,5);
    require(f.t.req_valid && !f.t.req_write,"late head store replaced held load at pressure");
    f.t.req_ready=1;f.settle();f.accepted(6);f.response();
    if(late_store)complete_store(f,5,false);pass();
}
static void pressure_recovery(const std::string& kind) {
    test_name="pressure-recovery-"+kind;Fixture f;fill(f,14);prepare(f,5);
    f.load(6,0x3000);f.t.req_ready=0;head(f,5);f.tick();allocate(f);
    if(kind=="reset")f.t.rst=1;
    else if(kind=="flush"){f.t.flush_valid=1;f.t.flush_seq=5;}
    else f.t.run=0;
    f.settle();require(!f.t.req_valid,"pressure recovery admitted request");f.tick();
    f.t.rst=0;f.t.flush_valid=0;f.t.run=1;f.t.agu_valid=0;f.t.req_ready=1;f.settle();
    if(kind=="reset")require(!f.t.req_valid && f.t.room_count==0,"pressure reset retained ownership");
    else complete_store(f,5,false);pass();
}
int main(int argc,char**argv) {
    if(argc!=3)return 2;
    room_policy=std::string(argv[1])=="1";
    char enabled[]="1";char* retained_args[]={argv[0],enabled,argv[2]};
    if(retained_arbitration_main(3,retained_args))return 1;
    trace.close();trace.open(argv[2],std::ios::app);
    try {
        room_sweep();simultaneous_room();
        for(unsigned used:{14U,15U,16U})for(bool buffered:{false,true})for(bool fp:{false,true})for(bool wrap:{false,true})
          for(bool blocked:{false,true})for(bool load_error:{false,true})for(bool store_error:{false,true})
            pressure_competition(used,buffered,fp,wrap,blocked,load_error,store_error);
        held_load_pressure_rises(15);held_load_pressure_rises(16);held_store_pressure_falls();
        for(unsigned used:{15U,16U})for(bool late_store:{false,true})uncontended_pressure(used,late_store);
        for(auto kind:{"reset","flush","recovery"})pressure_recovery(kind);
        require(pass_count==344,"complete room case count changed");
        std::cout<<"ALL 344 LSU ROB ROOM CASES PASS\n";
    }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}
    return 0;
}
