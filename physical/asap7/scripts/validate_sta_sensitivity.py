import subprocess
import re
import json
import os

periods_ns = [1.0, 2.0, 4.0, 8.0, 12.0]
results = []

target_from = "_387041_"
target_to = "_388327_"

orfs_tag = "836842-26Q1-2900-gdf79404cd8"

for T in periods_ns:
    period_ps = T * 1000.0
    tcl_content = f"""
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

create_clock -name core_clk -period {period_ps} -waveform [list 0 [expr {period_ps} / 2.0]] [get_ports clk]
set_clock_uncertainty -setup 50.0 [get_clocks core_clk]
set_clock_uncertainty -hold 25.0 [get_clocks core_clk]
set_input_transition 20.0 [get_ports clk]
set_propagated_clock [all_clocks]

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]
set_input_delay [expr 0.2 * {period_ps}] -clock core_clk $non_clock_inputs
set_output_delay [expr 0.2 * {period_ps}] -clock core_clk $all_outputs_list

puts "=== REPORTING PATH {target_from} -> {target_to} FOR T = {T} ns ==="
report_checks -from [get_pins {target_from}/CLK] -to [get_pins {target_to}/D] -path_delay max -format full_clock_expanded
exit
"""
    tcl_file = f"/home/a/ooo/physical/asap7/scripts/sens_{T}ns.tcl"
    with open(tcl_file, "w") as f:
        f.write(tcl_content)
    
    os.system(f"cp {tcl_file} /home/a/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo/sens_{T}ns.tcl")
    
    cmd = [
        "docker", "run", "--rm",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo:/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo",
        "-v", "/home/a/ooo/build/asap7/results:/OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base",
        "-w", "/OpenROAD-flow-scripts/flow",
        f"openroad/flow-ubuntu22.04-builder:{orfs_tag}",
        "bash", "-c",
        f"export PATH=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:$PATH && openroad -no_init /OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo/sens_{T}ns.tcl"
    ]
    
    print(f"Running STA for T = {T} ns...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = res.stdout
    
    arrival = None
    required = None
    slack = None
    
    for line in out.splitlines():
        if "data arrival time" in line:
            m = re.search(r"([-+]?\d+\.\d+)", line)
            if m: arrival = float(m.group(1))
        elif "data required time" in line:
            m = re.search(r"([-+]?\d+\.\d+)", line)
            if m: required = float(m.group(1))
        elif "slack (" in line:
            m = re.search(r"([-+]?\d+\.\d+)\s+slack", line)
            if m: slack = float(m.group(1))
            
    results.append({
        "period_ns": T,
        "period_ps": period_ps,
        "arrival_ps": arrival,
        "required_ps": required,
        "slack_ps": slack
    })
    print(f"  T = {T:4.1f} ns: Arrival = {arrival} ps, Required = {required} ps, Slack = {slack} ps")

out_file = "/home/a/ooo/build/asap7/reports/sta_sensitivity_validation.json"
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print("\n=== SENSITIVITY VALIDATION RESULTS ===")
prev_t = results[0]["period_ps"]
prev_req = results[0]["required_ps"]
prev_slack = results[0]["slack_ps"]

all_pass = True
for r in results[1:]:
    dt = r["period_ps"] - prev_t
    d_req = r["required_ps"] - prev_req
    d_slack = r["slack_ps"] - prev_slack
    req_diff = abs(d_req - dt)
    slack_diff = abs(d_slack - dt)
    passed = (req_diff < 0.1) and (slack_diff < 0.1)
    if not passed:
        all_pass = False
    print(f"ΔT = {dt:6.1f} ps | ΔRequired = {d_req:6.1f} ps (diff={req_diff:.2f} ps) | ΔSlack = {d_slack:6.1f} ps (diff={slack_diff:.2f} ps) | Valid: {passed}")
    prev_t = r["period_ps"]
    prev_req = r["required_ps"]
    prev_slack = r["slack_ps"]

status_str = "STA SWEEP = PASS (Single-cycle linearity verified)" if all_pass else "STA SWEEP = FAIL"
print(f"\nVerification Status: {status_str}")
