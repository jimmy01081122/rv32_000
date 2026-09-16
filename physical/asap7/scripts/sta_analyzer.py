import subprocess
import os
import re
import sys
import json
import shutil

def run_sta_signoff(build_dir, period_ns, orfs_tag="836842-26Q1-2900-gdf79404cd8"):
    period_ps = period_ns * 1000.0
    odb_path = f"{build_dir}/results/6_final.odb"
    if not os.path.exists(odb_path):
        print(f"ERROR: {odb_path} does not exist!")
        return None

    tcl_content = f"""read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_db /OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base/6_final.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing

set period_ps {period_ps:.1f}
create_clock -name core_clk -period $period_ps -waveform [list 0 [expr $period_ps / 2.0]] [get_ports clk]
set_clock_uncertainty -setup 50.0 [get_clocks core_clk]
set_clock_uncertainty -hold 25.0 [get_clocks core_clk]
set_input_transition 20.0 [get_ports clk]
set_propagated_clock [all_clocks]

set non_clock_inputs [all_inputs -no_clocks]
set all_outputs_list [all_outputs]
set_input_delay [expr 0.20 * $period_ps] -clock core_clk $non_clock_inputs
set_input_transition 20.0 $non_clock_inputs
set_output_delay [expr 0.20 * $period_ps] -clock core_clk $all_outputs_list
set_load 2.0 $all_outputs_list

group_path -name in2reg  -from $non_clock_inputs -to [all_registers]
group_path -name reg2out -from [all_registers]   -to $all_outputs_list
group_path -name reg2reg -from [all_registers]   -to [all_registers]
group_path -name in2out  -from $non_clock_inputs -to $all_outputs_list

# AP5: Automated hold timing repair
repair_timing -hold -verbose
estimate_parasitics -global_routing

set rpt_dir "/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base"

puts "=================== TIMING SUMMARY AT T = {period_ns:.2f} ns ==================="
puts "Overall Setup WNS:  [sta::worst_slack -max]"
puts "Overall Setup TNS:  [sta::total_negative_slack -max]"
puts "Overall Hold Slack: [sta::worst_slack -min]"

puts "=================== POWER AT {period_ns:.2f} ns ==================="
report_power > "$rpt_dir/power_closable_{period_ns:.1f}ns.rpt"
report_power

puts "=================== PATH GROUP SLACKS ==================="
report_checks -group_path_count 10 -endpoint_path_count 1

puts "=================== TOP 50 REG2REG PATHS ==================="
report_checks -path_group reg2reg -path_delay max -endpoint_path_count 1 -group_path_count 50 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2reg.rpt"
report_checks -path_group reg2reg -path_delay max -endpoint_path_count 1 -group_path_count 50 -format summary > "$rpt_dir/reg2reg_summary.rpt"

puts "=================== TOP 10 IN2REG PATHS ==================="
report_checks -path_group in2reg -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_in2reg.rpt"

puts "=================== TOP 10 REG2OUT PATHS ==================="
report_checks -path_group reg2out -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_reg2out.rpt"

puts "=================== TOP 10 IN2OUT PATHS ==================="
report_checks -path_group in2out -path_delay max -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_timing_in2out.rpt"

puts "=================== TOP 10 HOLD REG2REG PATHS ==================="
report_checks -path_group reg2reg -path_delay min -endpoint_path_count 1 -group_path_count 10 -format full_clock_expanded > "$rpt_dir/closable_hold_reg2reg.rpt"

puts "=================== CELL USAGE & AREA ==================="
report_cell_usage > "$rpt_dir/cell_usage.rpt"
report_cell_usage
report_design_area > "$rpt_dir/design_area.rpt"
report_design_area

puts "STA signoff complete."
exit
"""

    tcl_file = f"{build_dir}/run_sta_signoff.tcl"
    with open(tcl_file, "w") as f:
        f.write(tcl_content)

    docker_bin = shutil.which("docker") or "/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker"
    cmd = [
        docker_bin, "run", "--rm",
        "-v", "/home/a/ooo:/home/a/ooo",
        "-v", "/home/a/OpenROAD-flow-scripts/flow:/OpenROAD-flow-scripts/flow",
        "-v", f"{build_dir}/results:/OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/reports:/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base",
        "-w", "/OpenROAD-flow-scripts/flow",
        f"openroad/flow-ubuntu22.04-builder:{orfs_tag}",
        "bash", "-c",
        f"export PATH=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:$PATH && openroad -exit -threads 1 {tcl_file}"
    ]

    print(f"Running STA signoff for T = {period_ns:.2f} ns...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    log_path = f"{build_dir}/reports/sta_signoff.log"
    with open(log_path, "w") as f:
        f.write(res.stdout + "\n" + res.stderr)

    return parse_sta_results(build_dir, period_ns)

def parse_sta_results(build_dir, period_ns):
    rpt_dir = f"{build_dir}/reports"
    period_ps = period_ns * 1000.0

    metrics = {
        "period_ns": period_ns,
        "period_ps": period_ps,
        "target_freq_mhz": 1000.0 / period_ns,
    }

    # Helper to extract slack from a report
    def extract_slack(filename):
        path = os.path.join(rpt_dir, filename)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            for line in f:
                m = re.search(r"^\s*([\d\.\-]+)\s+slack\s+\((MET|VIOLATED)\)", line)
                if m:
                    return float(m.group(1))
        return None

    metrics["reg2reg_wns_ps"] = extract_slack("closable_timing_reg2reg.rpt")
    metrics["in2reg_wns_ps"] = extract_slack("closable_timing_in2reg.rpt")
    metrics["reg2out_wns_ps"] = extract_slack("closable_timing_reg2out.rpt")
    metrics["in2out_wns_ps"] = extract_slack("closable_timing_in2out.rpt")
    metrics["hold_worst_slack_ps"] = extract_slack("closable_hold_reg2reg.rpt")

    # Read overall slacks from log
    log_file = os.path.join(rpt_dir, "sta_signoff.log")
    if os.path.exists(log_file):
        with open(log_file) as f:
            log_text = f.read()
            m_s_wns = re.search(r"Overall Setup WNS:\s+([-\d\.]+)", log_text)
            if m_s_wns: metrics["overall_setup_wns_ps"] = float(m_s_wns.group(1))
            m_s_tns = re.search(r"Overall Setup TNS:\s+([-\d\.]+)", log_text)
            if m_s_tns: metrics["overall_setup_tns_ps"] = float(m_s_tns.group(1))
            m_h_wns = re.search(r"Overall Hold Slack:\s+([-\d\.]+)", log_text)
            if m_h_wns: metrics["overall_hold_slack_ps"] = float(m_h_wns.group(1))

    # Calculate effective Fmax
    if metrics["reg2reg_wns_ps"] is not None:
        tmin_internal_ps = period_ps - metrics["reg2reg_wns_ps"]
        metrics["tmin_internal_ns"] = tmin_internal_ps / 1000.0
        metrics["fmax_internal_mhz"] = 1000.0 / (tmin_internal_ps / 1000.0)

    system_slacks = [s for s in [metrics["reg2reg_wns_ps"], metrics["in2reg_wns_ps"], metrics["reg2out_wns_ps"]] if s is not None]
    if system_slacks:
        worst_sys_slack = min(system_slacks)
        tmin_system_ps = period_ps - worst_sys_slack
        metrics["tmin_system_ns"] = tmin_system_ps / 1000.0
        metrics["fmax_system_mhz"] = 1000.0 / (tmin_system_ps / 1000.0)

    # Power
    pwr_file = os.path.join(rpt_dir, f"power_closable_{period_ns:.1f}ns.rpt")
    if not os.path.exists(pwr_file):
        pwr_file = os.path.join(rpt_dir, "power_closable_12ns.rpt")
    if os.path.exists(pwr_file):
        with open(pwr_file) as f:
            pwr_text = f.read()
            m_pwr = re.search(r"Total\s+[\d\.eE+-]+\s+[\d\.eE+-]+\s+[\d\.eE+-]+\s+([\d\.eE+-]+)", pwr_text)
            if m_pwr:
                metrics["total_power_w"] = float(m_pwr.group(1))
                metrics["total_power_mw"] = metrics["total_power_w"] * 1000.0

    # Cell usage & Area
    cell_rpt = os.path.join(rpt_dir, "cell_usage.rpt")
    if os.path.exists(cell_rpt):
        with open(cell_rpt) as f:
            txt = f.read()
            m_cnt = re.search(r"Total number of cells:\s+(\d+)", txt)
            if m_cnt: metrics["total_cells"] = int(m_cnt.group(1))
            # count buffers
            buf_count = 0
            for line in txt.splitlines():
                if re.search(r"\b(BUF|INV)", line):
                    m_b = re.search(r"^\s*\S+\s+(\d+)", line)
                    if m_b: buf_count += int(m_b.group(1))
            metrics["buffer_inverter_cells"] = buf_count

    area_rpt = os.path.join(rpt_dir, "design_area.rpt")
    if os.path.exists(area_rpt):
        with open(area_rpt) as f:
            txt = f.read()
            m_area = re.search(r"Design area\s+([\d\.]+)\s+u\^2", txt)
            if m_area: metrics["stdcell_area_um2"] = float(m_area.group(1))

    # Print summary
    print("\n==================================================================")
    print(f"  PHYSICAL METRICS SUMMARY FOR T = {period_ns:.2f} ns ({metrics['target_freq_mhz']:.2f} MHz)")
    print("==================================================================")
    print(f"  REG2REG Setup WNS:    {metrics.get('reg2reg_wns_ps')} ps")
    print(f"  IN2REG Setup WNS:     {metrics.get('in2reg_wns_ps')} ps")
    print(f"  REG2OUT Setup WNS:    {metrics.get('reg2out_wns_ps')} ps")
    print(f"  IN2OUT Setup WNS:     {metrics.get('in2out_wns_ps')} ps")
    print(f"  Worst Hold Slack:     {metrics.get('hold_worst_slack_ps')} ps")
    print(f"  Effective Tmin (int): {metrics.get('tmin_internal_ns'):.3f} ns")
    print(f"  Effective Fmax (int): {metrics.get('fmax_internal_mhz'):.2f} MHz")
    print(f"  Effective Fmax (sys): {metrics.get('fmax_system_mhz'):.2f} MHz")
    if 'total_cells' in metrics:
        print(f"  Total Cells:          {metrics.get('total_cells')}")
        print(f"  Buffer/Inverter Cells:{metrics.get('buffer_inverter_cells')}")
    if 'stdcell_area_um2' in metrics:
        print(f"  Stdcell Area:         {metrics.get('stdcell_area_um2')} um^2")
    if 'total_power_mw' in metrics:
        print(f"  Total Power:          {metrics.get('total_power_mw'):.2f} mW")
    print("==================================================================\n")

    # Save to metrics.json
    with open(f"{build_dir}/results/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics

if __name__ == "__main__":
    bdir = sys.argv[1] if len(sys.argv) > 1 else "/home/a/ooo/build/asap7_closable_12.0ns"
    t = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    parse_sta_results(bdir, t)
