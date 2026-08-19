#include <iostream>
#include <iomanip>
#include <memory>
#include <string>
#include <fstream>
#include <verilated.h>
#include <verilated_vcd_c.h>

#include "Vrv32_ooo_core.h"
#include "sim_mem.h"

struct SimConfig {
    std::string elf_file;
    std::string vcd_file;
    std::string trace_file;
    uint64_t max_cycles = 1000000;
    uint64_t no_retire_limit = 10000;
    bool enable_vcd = false;
    bool enable_trace = false;
};

void parse_args(int argc, char** argv, SimConfig& config) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg.rfind("+elf=", 0) == 0 || arg.rfind("--elf=", 0) == 0) {
            config.elf_file = arg.substr(arg.find('=') + 1);
        } else if (arg.rfind("+vcd=", 0) == 0 || arg.rfind("--vcd=", 0) == 0) {
            config.vcd_file = arg.substr(arg.find('=') + 1);
            config.enable_vcd = true;
        } else if (arg.rfind("+trace=", 0) == 0 || arg.rfind("--trace=", 0) == 0) {
            config.trace_file = arg.substr(arg.find('=') + 1);
            config.enable_trace = true;
        } else if (arg.rfind("+max-cycles=", 0) == 0) {
            config.max_cycles = std::stoull(arg.substr(arg.find('=') + 1));
        } else if (arg.rfind("+no-retire-max=", 0) == 0) {
            config.no_retire_limit = std::stoull(arg.substr(arg.find('=') + 1));
        }
    }
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    SimConfig config;
    parse_args(argc, argv, config);

    if (config.elf_file.empty()) {
        std::cout << "Usage: " << argv[0] << " +elf=<path.elf> [+vcd=<path.vcd>] [+trace=<path.log>] [+max-cycles=N]" << std::endl;
        return 1;
    }

    SimMemory memory;
    uint32_t entry_pc = 0x80000000;
    if (!memory.load_elf(config.elf_file, entry_pc)) {
        std::cerr << "Failed to load ELF: " << config.elf_file << std::endl;
        return 1;
    }

    if (config.enable_vcd) {
        Verilated::traceEverOn(true);
    }

    auto top = std::make_unique<Vrv32_ooo_core>();

    std::unique_ptr<VerilatedVcdC> tfp;
    if (config.enable_vcd) {
        tfp = std::make_unique<VerilatedVcdC>();
        top->trace(tfp.get(), 99);
        tfp->open(config.vcd_file.c_str());
        std::cout << "[Simulator] VCD tracing enabled: " << config.vcd_file << std::endl;
    }

    std::ofstream trace_out;
    if (config.enable_trace) {
        trace_out.open(config.trace_file);
        std::cout << "[Simulator] Commit trace logging enabled: " << config.trace_file << std::endl;
    }

    uint64_t sim_time = 0;
    uint64_t cycles = 0;
    uint64_t retired_insns = 0;
    uint64_t last_retire_cycle = 0;

    // Reset sequence: initialize pins and hold rst=1 for 10 cycles
    top->clk = 0;
    top->rst = 1;
    top->imem_req_ready = 1;
    top->imem_rsp_valid = 0;
    top->imem_rsp_rdata = 0;
    top->imem_rsp_error = 0;
    top->dmem_req_ready = 1;
    top->dmem_rsp_valid = 0;
    top->dmem_rsp_rdata = 0;
    top->dmem_rsp_error = 0;

    for (int i = 0; i < 10; ++i) {
        top->clk = 0;
        top->eval();
        if (tfp) tfp->dump(sim_time++);
        top->clk = 1;
        top->eval();
        if (tfp) tfp->dump(sim_time++);
    }
    top->rst = 0;

    // Memory pipeline state (Synchronous 1-cycle latency SRAM model)
    bool imem_pipe_valid = false;
    uint32_t imem_pipe_data = 0;

    bool dmem_rsp_pending = false;
    uint32_t dmem_rsp_data = 0;

    bool exit_pending = false;
    int exit_drain_cycles = 0;

    std::cout << "[Simulator] Starting simulation run..." << std::endl;

    while (!Verilated::gotFinish() && cycles < config.max_cycles) {
        if (memory.has_exited()) {
            if (!exit_pending) {
                exit_pending = true;
                exit_drain_cycles = 50;
            } else if (exit_drain_cycles <= 0) {
                break;
            }
            exit_drain_cycles--;
        }

        // --- Falling Edge (Clock Low) ---
        top->clk = 0;

        // Drive response and ready to core
        top->imem_req_ready = 1;
        top->imem_rsp_valid = imem_pipe_valid ? 1 : 0;
        top->imem_rsp_rdata = imem_pipe_data;
        top->imem_rsp_error = 0;

        top->dmem_req_ready = !dmem_rsp_pending;
        top->dmem_rsp_valid = dmem_rsp_pending ? 1 : 0;
        top->dmem_rsp_rdata = dmem_rsp_data;
        top->dmem_rsp_error = 0;

        top->eval();
        if (tfp) tfp->dump(sim_time++);

        // Sample memory requests from core
        bool imem_accepted = (top->imem_req_valid && top->imem_req_ready);
        uint32_t next_imem_data = imem_accepted ? memory.read32(top->imem_req_addr) : 0;
        bool next_imem_valid = imem_accepted;

        bool dmem_accepted = (top->dmem_req_valid && top->dmem_req_ready && !dmem_rsp_pending);
        if (top->dmem_rsp_valid && top->dmem_rsp_ready) {
            dmem_rsp_pending = false;
        }
        if (dmem_accepted) {
            dmem_rsp_pending = true;
            if (top->dmem_req_wen) {
                memory.write32(top->dmem_req_addr, top->dmem_req_wdata, top->dmem_req_byte_en);
                dmem_rsp_data = 0;
            } else {
                dmem_rsp_data = memory.read32(top->dmem_req_addr);
            }
        }

        // --- Rising Edge (Clock High) ---
        top->clk = 1;
        top->eval();
        if (tfp) tfp->dump(sim_time++);

        imem_pipe_valid = next_imem_valid;
        imem_pipe_data  = next_imem_data;

        cycles++;

        // Commit trace inspection (commit_trace_t 344-bit layout, MSB-first)
        bool retire_valid = (top->commit_trace[10] >> 23) & 1;
        bool trap_valid   = (top->commit_trace[10] >> 22) & 1;

        if (retire_valid) {
            retired_insns++;
            last_retire_cycle = cycles;

            uint32_t commit_pc = ((top->commit_trace[8] & 0x3FFFFF) << 10) | ((top->commit_trace[7] >> 22) & 0x3FF);
            uint32_t commit_insn = ((top->commit_trace[7] & 0x3FFFFF) << 10) | ((top->commit_trace[6] >> 22) & 0x3FF);
            bool     int_dst_valid = (top->commit_trace[6] >> 21) & 1;
            uint32_t int_dst_arch  = (top->commit_trace[6] >> 16) & 0x1F;
            uint32_t int_dst_data  = ((top->commit_trace[6] & 0xFFFF) << 16) | ((top->commit_trace[5] >> 16) & 0xFFFF);
            bool     fp_dst_valid  = (top->commit_trace[5] >> 15) & 1;
            uint32_t fp_dst_arch   = (top->commit_trace[5] >> 10) & 0x1F;
            uint32_t fp_dst_data   = ((top->commit_trace[5] & 0x3FF) << 22) | ((top->commit_trace[4] >> 10) & 0x3FFFFF);
            bool     mem_valid     = (top->commit_trace[4] >> 9) & 1;
            uint32_t mem_addr      = ((top->commit_trace[4] & 0x1FF) << 23) | ((top->commit_trace[3] >> 9) & 0x7FFFFF);
            uint32_t mem_byte_mask = (top->commit_trace[3] >> 5) & 0xF;
            uint32_t mem_wdata     = ((top->commit_trace[3] & 0x1F) << 27) | ((top->commit_trace[2] >> 5) & 0x7FFFFFF);

            if (config.enable_trace && trace_out.is_open()) {
                trace_out << "core 0: 0x" << std::hex << std::setw(8) << std::setfill('0') << commit_pc
                          << " (0x" << std::setw(8) << std::setfill('0') << commit_insn << ")";
                if (int_dst_valid) {
                    trace_out << " x" << std::dec << int_dst_arch << "=0x" << std::hex << int_dst_data;
                }
                if (fp_dst_valid) {
                    trace_out << " f" << std::dec << fp_dst_arch << "=0x" << std::hex << fp_dst_data;
                }
                if (mem_valid) {
                    trace_out << " [mem=0x" << std::hex << mem_addr << " mask=0x" << mem_byte_mask << " data=0x" << mem_wdata << "]";
                }
                trace_out << std::dec << std::endl;
            }

            if (exit_pending && commit_insn == 0x10500073 /* wfi */) {
                break;
            }
        }

        if (trap_valid) {
            uint32_t trap_pc = ((top->commit_trace[8] & 0x3FFFFF) << 10) | ((top->commit_trace[7] >> 22) & 0x3FF);
            uint32_t trap_insn = ((top->commit_trace[7] & 0x3FFFFF) << 10) | ((top->commit_trace[6] >> 22) & 0x3FF);
            uint32_t trap_cause = ((top->commit_trace[2] & 0x1F) << 27) | ((top->commit_trace[1] >> 5) & 0x7FFFFFF);
            uint32_t trap_tval  = ((top->commit_trace[1] & 0x1F) << 27) | ((top->commit_trace[0] >> 5) & 0x7FFFFFF);
            std::cout << "[Simulator] TRAP encountered at cycle " << cycles << " PC=0x" << std::hex << trap_pc
                      << " insn=0x" << trap_insn << " cause=0x" << trap_cause << " tval=0x" << trap_tval << std::dec << std::endl;
            last_retire_cycle = cycles;
        }

        // Watchdog timeout check
        if (cycles - last_retire_cycle > config.no_retire_limit) {
            std::cerr << "\n[Simulator] ERROR: Watchdog timeout! No instruction retired for "
                      << config.no_retire_limit << " cycles. (Current cycle: " << cycles << ")" << std::endl;
            break;
        }
    }

    if (tfp) {
        tfp->close();
    }
    if (trace_out.is_open()) {
        trace_out.close();
    }

    double ipc = (cycles > 0) ? (static_cast<double>(retired_insns) / cycles) : 0.0;

    std::cout << "\n================ Simulation Summary ================" << std::endl;
    std::cout << "  ELF binary     : " << config.elf_file << std::endl;
    std::cout << "  Cycles         : " << cycles << std::endl;
    std::cout << "  Retired insns  : " << retired_insns << std::endl;
    std::cout << "  IPC            : " << std::fixed << std::setprecision(4) << ipc << std::endl;
    std::cout << "  Exit status    : " << (memory.has_exited() ? (memory.exit_code() == 0 ? "PASS (0)" : "FAIL") : "TIMEOUT / HALTED") << std::endl;
    std::cout << "====================================================\n" << std::endl;

    return memory.has_exited() ? memory.exit_code() : 1;
}
