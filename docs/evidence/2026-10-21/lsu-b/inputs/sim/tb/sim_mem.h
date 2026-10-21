#ifndef SIM_MEM_H
#define SIM_MEM_H

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <iostream>

class SimMemory {
public:
    static constexpr uint32_t RAM_BASE   = 0x80000000ULL;
    static constexpr uint32_t RAM_SIZE   = 1024 * 1024; // 1 MB
    static constexpr uint32_t SIM_PUTC   = 0x10000000ULL;
    static constexpr uint32_t SIM_EXIT   = 0x10000004ULL;
    static constexpr uint32_t SIM_STATUS = 0x10000008ULL;

    SimMemory();
    ~SimMemory() = default;

    bool load_elf(const std::string& filename, uint32_t& entry_pc);
    bool load_bin(const std::string& filename, uint32_t load_addr = RAM_BASE);

    uint32_t read32(uint32_t addr);
    void write32(uint32_t addr, uint32_t data, uint8_t byte_en = 0xF);

    uint8_t read8(uint32_t addr);
    void write8(uint32_t addr, uint8_t data);

    bool has_exited() const { return exited_; }
    int exit_code() const { return exit_code_; }
    uint32_t tohost_addr() const { return tohost_addr_; }

    void dump_ram(uint32_t start_addr, uint32_t bytes);

private:
    std::vector<uint8_t> ram_;
    bool exited_;
    int exit_code_;
    uint32_t tohost_addr_;
    uint32_t tohost_lo_;
};

#endif // SIM_MEM_H
