import subprocess
import os
import re
import sys
import json
import shutil

def run_physical_implementation(period_ns, build_tag="closable"):
    period_ps = period_ns * 1000.0
    print(f"\n==================================================================")
    print(f"  STARTING FRESH PHYSICAL IMPLEMENTATION FOR T = {period_ns:.2f} ns ({1000.0/period_ns:.2f} MHz)")
    print(f"==================================================================")
    
    # 1. Generate constraint.sdc
    sdc_content = f"""# RV32 OoO Core — ASAP7 Timing Constraints
set sdc_version 2.0
set clk_name core_clk
set clk_port_name clk
set clk_period {period_ps:.1f}

set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period -waveform [list 0 [expr $clk_period / 2.0]] $clk_port

set_clock_uncertainty -setup 50.0 [get_clocks $clk_name]
set_clock_uncertainty -hold  25.0 [get_clocks $clk_name]
set_input_transition 20.0 $clk_port

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]

set_input_delay [expr 0.20 * $clk_period] -clock $clk_name $non_clock_inputs
set_input_transition 20.0 $non_clock_inputs
set_output_delay [expr 0.20 * $clk_period] -clock $clk_name $all_outputs_list
set_load 2.0 $all_outputs_list

group_path -name in2reg  -from $non_clock_inputs -to [all_registers]
group_path -name reg2out -from [all_registers]   -to $all_outputs_list
group_path -name reg2reg -from [all_registers]   -to [all_registers]
group_path -name in2out  -from $non_clock_inputs -to $all_outputs_list
"""
    sdc_dest = "/home/a/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo/constraint.sdc"
    with open(sdc_dest, "w") as f:
        f.write(sdc_content)
        
    # Also update physical/asap7/constraint.sdc
    with open("/home/a/ooo/physical/asap7/constraint.sdc", "w") as f:
        f.write(sdc_content)
        
    # Create clean build dir
    build_dir = f"/home/a/ooo/build/asap7_{build_tag}_{period_ns}ns"
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(f"{build_dir}/results", exist_ok=True)
    os.makedirs(f"{build_dir}/logs", exist_ok=True)
    os.makedirs(f"{build_dir}/reports", exist_ok=True)
    os.makedirs(f"{build_dir}/objects", exist_ok=True)
    
    orfs_tag = "836842-26Q1-2900-gdf79404cd8"
    
    # 2. Run ORFS flow inside container
    cmd = [
        "docker", "run", "--rm",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo:/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/designs/src/rv32_ooo:/OpenROAD-flow-scripts/flow/designs/src/rv32_ooo",
        "-v", f"{build_dir}/results:/OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/logs:/OpenROAD-flow-scripts/flow/logs/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/reports:/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/objects:/OpenROAD-flow-scripts/flow/objects/asap7/rv32_ooo/base",
        "-w", "/OpenROAD-flow-scripts/flow",
        f"openroad/flow-ubuntu22.04-builder:{orfs_tag}",
        "bash", "-c",
        "make DESIGN_CONFIG=designs/asap7/rv32_ooo/config.mk finish"
    ]
    
    print(f"Executing: make DESIGN_CONFIG=designs/asap7/rv32_ooo/config.mk finish in Docker...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    report_file = f"{build_dir}/reports/6_finish.rpt"
    if not os.path.exists(report_file):
        print(f"ERROR: 6_finish.rpt not found! Build failed.")
        print("STDOUT tail:")
        print(res.stdout[-2000:])
        print("STDERR tail:")
        print(res.stderr[-2000:])
        return None
        
    with open(report_file) as f:
        rpt_text = f.read()
        
    metrics = {
        "period_ns": period_ns,
        "period_ps": period_ps,
        "freq_mhz": 1000.0 / period_ns,
        "build_dir": build_dir
    }
    
    m_wns = re.search(r"wns\s+([-+]?\d+\.\d+)", rpt_text)
    if m_wns: metrics["wns_ps"] = float(m_wns.group(1))
    
    m_tns = re.search(r"tns\s+([-+]?\d+\.\d+)", rpt_text)
    if m_tns: metrics["tns_ps"] = float(m_tns.group(1))
    
    m_hold = re.search(r"worst_slack\s+([-+]?\d+\.\d+)", rpt_text)
    if m_hold: metrics["worst_hold_slack_ps"] = float(m_hold.group(1))
    
    m_inst = re.search(r"instance count\s+(\d+)", rpt_text)
    if m_inst: metrics["total_instances"] = int(m_inst.group(1))
    
    m_area = re.search(r"stdcell_area\s+([\d\.]+)", rpt_text)
    if m_area: metrics["stdcell_area_um2"] = float(m_area.group(1))
    
    m_core = re.search(r"core_area\s+([\d\.]+)", rpt_text)
    if m_core: metrics["core_area_um2"] = float(m_core.group(1))
    
    m_util = re.search(r"utilization_pct\s+([\d\.]+)", rpt_text)
    if m_util: metrics["utilization_pct"] = float(m_util.group(1))
    
    m_pwr = re.search(r"total_power\s+([\d\.eE+-]+)", rpt_text)
    if m_pwr: metrics["total_power_w"] = float(m_pwr.group(1))
    
    print(f"\n==================================================================")
    print(f"RESULTS FOR T = {period_ns:.2f} ns ({metrics['freq_mhz']:.2f} MHz):")
    print(f"  Setup WNS:       {metrics.get('wns_ps')} ps")
    print(f"  Setup TNS:       {metrics.get('tns_ps')} ps")
    print(f"  Worst Hold Slack:{metrics.get('worst_hold_slack_ps')} ps")
    print(f"  Total Instances: {metrics.get('total_instances')}")
    print(f"  Stdcell Area:    {metrics.get('stdcell_area_um2')} um^2")
    pwr_mw = metrics.get('total_power_w', 0.0) * 1000.0 if metrics.get('total_power_w') else 0.0
    print(f"  Total Power:     {pwr_mw:.2f} mW")
    print(f"==================================================================")
    
    return metrics

if __name__ == "__main__":
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    run_physical_implementation(t)
