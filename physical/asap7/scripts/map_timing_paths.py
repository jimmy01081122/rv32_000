#!/usr/bin/env python3
import re
import sys

def parse_yosys_dffs(yosys_file):
    dff_map = {}
    with open(yosys_file, "r") as f:
        content = f.read()
    
    # Match DFF instantiations: DFF... _XXXXX_ ( .CLK(...), .D(...), .QN(...) );
    pattern = re.compile(r'(DFF\w+)\s+(_\d+_)\s*\(\s*\.CLK\([^)]+\),\s*\.D\(([^)]+)\),\s*\.QN\(([^)]+)\)\s*\);')
    for m in pattern.finditer(content):
        cell_type = m.group(1)
        cell_name = m.group(2)
        d_pin = m.group(3).strip()
        qn_pin = m.group(4).strip()
        dff_map[cell_name] = {
            "type": cell_type,
            "d": d_pin,
            "qn": qn_pin
        }
    return dff_map

def analyze_paths(report_file, dff_map):
    with open(report_file, "r") as f:
        lines = f.readlines()
    
    paths = []
    curr_path = None
    in_path = False
    
    for line in lines:
        if line.startswith("Startpoint:"):
            m = re.search(r"Startpoint:\s*([^\s]+)", line)
            sp = m.group(1) if m else "unknown"
            curr_path = {"startpoint": sp, "endpoint": None, "slack": None, "delay": None}
        elif line.startswith("Endpoint:"):
            m = re.search(r"Endpoint:\s*([^\s]+)", line)
            if curr_path:
                curr_path["endpoint"] = m.group(1) if m else "unknown"
        elif "data arrival time" in line:
            m = re.search(r"([\d\.]+)\s+data arrival time", line)
            if curr_path and m:
                curr_path["delay"] = float(m.group(1))
        elif "slack (" in line:
            m = re.search(r"([-+]?[\d\.]+)\s+slack", line)
            if curr_path and m:
                curr_path["slack"] = float(m.group(1))
                paths.append(curr_path)
                curr_path = None
                
    print(f"Total paths parsed: {len(paths)}")
    
    seen = set()
    unique_paths = []
    for p in paths:
        pair = (p["startpoint"], p["endpoint"])
        if pair not in seen:
            seen.add(pair)
            unique_paths.append(p)
            
    print(f"\nUnique (Startpoint -> Endpoint) Paths: {len(unique_paths)}")
    for i, p in enumerate(unique_paths[:20]):
        sp = p["startpoint"]
        ep = p["endpoint"]
        sp_info = dff_map.get(sp, {"qn": "N/A"})
        ep_info = dff_map.get(ep, {"d": "N/A"})
        print(f"\n[Rank {i+1}] Slack: {p['slack']:+.2f} ps | Delay: {p['delay']:.2f} ps")
        print(f"  Startpoint: {sp} (QN: {sp_info['qn']})")
        print(f"  Endpoint:   {ep} (D:  {ep_info['d']})")

if __name__ == "__main__":
    yosys_v = sys.argv[1] if len(sys.argv) > 1 else "/home/a/ooo/build/asap7_closable_12.0ns/results/1_2_yosys.v"
    rpt_file = sys.argv[2] if len(sys.argv) > 2 else "/home/a/ooo/build/asap7_closable_12.0ns/reports/closable_timing_reg2reg.rpt"
    print("Building DFF map from 1_2_yosys.v...")
    dff_map = parse_yosys_dffs(yosys_v)
    print(f"Mapped {len(dff_map)} flip-flops.")
    analyze_paths(rpt_file, dff_map)
