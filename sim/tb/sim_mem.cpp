#include "sim_mem.h"
#include <fstream>
#include <cstring>
#include <cstdio>

// Minimal self-contained ELF32 reader
struct Elf32_Ehdr {
    uint8_t  e_ident[16];
    uint16_t e_type;
    uint16_t e_machine;
    uint32_t e_version;
    uint32_t e_entry;
    uint32_t e_phoff;
    uint32_t e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize;
    uint16_t e_phentsize;
    uint16_t e_phnum;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
};

struct Elf32_Phdr {
    uint32_t p_type;
    uint32_t p_offset;
    uint32_t p_vaddr;
    uint32_t p_paddr;
    uint32_t p_filesz;
    uint32_t p_memsz;
    uint32_t p_flags;
    uint32_t p_align;
};

constexpr uint32_t PT_LOAD = 1;

SimMemory::SimMemory() : ram_(RAM_SIZE, 0), exited_(false), exit_code_(0) {}

bool SimMemory::load_elf(const std::string& filename, uint32_t& entry_pc) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "[SimMemory] Error: Cannot open ELF file: " << filename << std::endl;
        return false;
    }

    Elf32_Ehdr ehdr;
    file.read(reinterpret_cast<char*>(&ehdr), sizeof(ehdr));
    if (!file) {
        std::cerr << "[SimMemory] Error: Failed to read ELF header" << std::endl;
        return false;
    }

    // Check ELF magic: 0x7F 'E' 'L' 'F'
    if (ehdr.e_ident[0] != 0x7F || ehdr.e_ident[1] != 'E' ||
        ehdr.e_ident[2] != 'L'  || ehdr.e_ident[3] != 'F') {
        std::cerr << "[SimMemory] Error: Not a valid ELF file: " << filename << std::endl;
        return false;
    }

    entry_pc = ehdr.e_entry;

    // Read Program Headers
    file.seekg(ehdr.e_phoff);
    std::vector<Elf32_Phdr> phdrs(ehdr.e_phnum);
    file.read(reinterpret_cast<char*>(phdrs.data()), ehdr.e_phnum * sizeof(Elf32_Phdr));

    for (const auto& ph : phdrs) {
        if (ph.p_type == PT_LOAD && ph.p_filesz > 0) {
            if (ph.p_paddr < RAM_BASE || ph.p_paddr + ph.p_memsz > RAM_BASE + RAM_SIZE) {
                std::cerr << "[SimMemory] Warning: Segment at 0x" << std::hex << ph.p_paddr
                          << " (size 0x" << ph.p_memsz << ") outside RAM bounds" << std::dec << std::endl;
                continue;
            }

            uint32_t ram_offset = ph.p_paddr - RAM_BASE;
            file.seekg(ph.p_offset);
            file.read(reinterpret_cast<char*>(&ram_[ram_offset]), ph.p_filesz);

            // Zero-fill remaining memsz (BSS segment)
            if (ph.p_memsz > ph.p_filesz) {
                std::memset(&ram_[ram_offset + ph.p_filesz], 0, ph.p_memsz - ph.p_filesz);
            }

            std::cout << "[SimMemory] Loaded segment to 0x" << std::hex << ph.p_paddr
                      << " (filesz: 0x" << ph.p_filesz << ", memsz: 0x" << ph.p_memsz << ")"
                      << std::dec << std::endl;
        }
    }

    std::cout << "[SimMemory] ELF loaded successfully. Entry PC = 0x" << std::hex << entry_pc << std::dec << std::endl;
    return true;
}

uint8_t SimMemory::read8(uint32_t addr) {
    if (addr >= RAM_BASE && addr < RAM_BASE + RAM_SIZE) {
        return ram_[addr - RAM_BASE];
    }
    return 0;
}

void SimMemory::write8(uint32_t addr, uint8_t data) {
    if (addr >= RAM_BASE && addr < RAM_BASE + RAM_SIZE) {
        ram_[addr - RAM_BASE] = data;
    } else if (addr == SIM_PUTC) {
        std::putchar(static_cast<char>(data));
        std::fflush(stdout);
    }
}

uint32_t SimMemory::read32(uint32_t addr) {
    if (addr >= RAM_BASE && addr + 3 < RAM_BASE + RAM_SIZE) {
        uint32_t offset = addr - RAM_BASE;
        return static_cast<uint32_t>(ram_[offset]) |
               (static_cast<uint32_t>(ram_[offset + 1]) << 8) |
               (static_cast<uint32_t>(ram_[offset + 2]) << 16) |
               (static_cast<uint32_t>(ram_[offset + 3]) << 24);
    }
    return 0;
}

void SimMemory::write32(uint32_t addr, uint32_t data, uint8_t byte_en) {
    if (addr >= RAM_BASE && addr + 3 < RAM_BASE + RAM_SIZE) {
        uint32_t offset = addr - RAM_BASE;
        if (byte_en & 0x1) ram_[offset + 0] = (data >> 0) & 0xFF;
        if (byte_en & 0x2) ram_[offset + 1] = (data >> 8) & 0xFF;
        if (byte_en & 0x4) ram_[offset + 2] = (data >> 16) & 0xFF;
        if (byte_en & 0x8) ram_[offset + 3] = (data >> 24) & 0xFF;
    } else if (addr == SIM_PUTC) {
        std::putchar(static_cast<char>(data & 0xFF));
        std::fflush(stdout);
    } else if (addr == SIM_EXIT) {
        exited_ = true;
        exit_code_ = static_cast<int>(data);
        std::cout << "\n[SimMemory] SIM_EXIT received with code: " << exit_code_
                  << (exit_code_ == 0 ? " (PASS)" : " (FAIL)") << std::endl;
    }
}
