#include "Vtb_completion_collisions.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtb_completion_collisions* top = new Vtb_completion_collisions;
    top->clk = 0;
    while (!Verilated::gotFinish()) {
        top->clk = !top->clk;
        top->eval();
    }
    delete top;
    return 0;
}
