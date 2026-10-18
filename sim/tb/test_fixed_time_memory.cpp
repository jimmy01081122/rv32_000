#include "fixed_time_memory.h"
#include <cassert>
#include <limits>
int main() {
    FixedTimePort port(5500,5500,4);
    assert(port.ready(0));
    port.accept(0,0x12345678);
    assert(!port.valid(5499) && !port.ready(5499));
    // A faster 3000ps core samples the unchanged 5500ps service at 6000ps.
    assert(!port.valid(3000) && port.valid(6000));
    assert(port.front().due_ps==5500 && port.front().data==0x12345678);
    // Holding a response must not change its identity or grant extra credits.
    port.accept(6000,0x87654321,true);
    assert(port.front().data==0x12345678 && !port.front().error);
    port.consume(9000);
    assert(!port.valid(11499) && port.valid(12000));
    assert(port.front().error && port.front().data==0x87654321);
    port.consume(12000);
    assert(port.empty() && port.requests==2 && port.responses==2);
    assert(port.min_response_ps==6000 && port.max_response_ps==6000 && port.max_handoff_ps==9000);
    FixedTimePort single(100,100,1);
    single.accept(0,1);
    assert(!single.ready(200)); // response backpressure retains the only credit
    single.consume(200);assert(single.ready(200));
    bool threw=false;
    try { FixedTimePort bad(0,1,1); } catch(const std::invalid_argument&) { threw=true; }
    assert(threw);threw=false;
    try { single.consume(201); } catch(const std::logic_error&) { threw=true; }
    assert(threw);threw=false;
    try { single.accept(UINT64_MAX-10,1); } catch(const std::overflow_error&) { threw=true; }
    assert(threw);
}
