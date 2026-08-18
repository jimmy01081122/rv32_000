import sys

with open("build/sim_test.vcd", "r") as f:
    lines = f.readlines()

# Map var names to symbols
signals = {}
for line in lines:
    if line.startswith("$var"):
        parts = line.split()
        if len(parts) >= 5:
            sym = parts[3]
            name = parts[4]
            signals[sym] = name

print(f"Total signals found in VCD: {len(signals)}")
# Find key signals
key_syms = {}
for sym, name in signals.items():
    if any(k in name for k in ["imem_req", "imem_rsp", "dec_valid", "ren_valid", "int_disp", "issue_valid", "retire_valid", "current_state", "fetch_pc"]):
        key_syms[sym] = name
        print(f"  {name} -> {sym}")
