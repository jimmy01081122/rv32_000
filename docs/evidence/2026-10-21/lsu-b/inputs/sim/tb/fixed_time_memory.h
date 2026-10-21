#ifndef RV32_FIXED_TIME_MEMORY_H
#define RV32_FIXED_TIME_MEMORY_H
#include <algorithm>
#include <cstdint>
#include <deque>
#include <limits>
#include <stdexcept>

// All timestamps are physical ps relative to reset release. Responses are
// observed on the first core sampling edge at or after their absolute deadline.
// Queue contents remain stable under response backpressure and across redirects.
class FixedTimePort {
public:
    struct Response { uint64_t accepted_ps, due_ps; uint32_t data; bool error; uint64_t first_valid_ps; };
    FixedTimePort(uint64_t latency_ps, uint64_t interval_ps, unsigned capacity)
        : latency_(latency_ps), interval_(interval_ps), capacity_(capacity) {
        if (!latency_ || !interval_ || !capacity_) throw std::invalid_argument("positive memory timing/capacity required");
    }
    bool empty() const { return queue_.empty(); }
    bool ready(uint64_t now) const { return queue_.size() < capacity_ && now >= next_request_; }
    bool valid(uint64_t now) {
        if (empty() || now < queue_.front().due_ps) return false;
        if (queue_.front().first_valid_ps == UINT64_MAX) queue_.front().first_valid_ps = now;
        return true;
    }
    const Response& front() const { return queue_.front(); }
    void accept(uint64_t now, uint32_t data, bool error = false) {
        if (!ready(now)) throw std::logic_error("memory request accepted without credit/time slot");
        if (now > std::numeric_limits<uint64_t>::max() - std::max(latency_, interval_))
            throw std::overflow_error("memory deadline overflow");
        queue_.push_back({now, now + latency_, data, error, UINT64_MAX});
        next_request_ = now + interval_;
        ++requests;
    }
    void consume(uint64_t now) {
        if (!valid(now)) throw std::logic_error("memory response consumed before deadline");
        // Service eligibility excludes extra delay from CPU response backpressure.
        uint64_t elapsed = front().first_valid_ps - front().accepted_ps;
        max_handoff_ps = std::max(max_handoff_ps, now - front().accepted_ps);
        min_response_ps = std::min(min_response_ps, elapsed);
        max_response_ps = std::max(max_response_ps, elapsed);
        queue_.pop_front();
        ++responses;
    }
    uint64_t requests = 0, responses = 0;
    uint64_t min_response_ps = std::numeric_limits<uint64_t>::max(), max_response_ps = 0, max_handoff_ps = 0;
private:
    uint64_t latency_, interval_, next_request_ = 0;
    unsigned capacity_;
    std::deque<Response> queue_;
};
#endif
