import subprocess
import os
import re
import sys
import json
import shutil
from sta_analyzer import run_sta_signoff

def run_physical_implementation(period_ns, build_tag="closable", clean=True, reuse_synth=False, synth_base=None):
    period_ps = period_ns * 1000.0
    print(f"\n==================================================================")
    print(f"  STARTING PHYSICAL IMPLEMENTATION FOR T = {period_ns:.2f} ns ({1000.0/period_ns:.2f} MHz)")
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
        
    # Create build dir
    build_dir = f"/home/a/ooo/build/asap7_{build_tag}_{period_ns:.1f}ns"
    if clean:
        shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(f"{build_dir}/results", exist_ok=True)
    os.makedirs(f"{build_dir}/logs", exist_ok=True)
    os.makedirs(f"{build_dir}/reports", exist_ok=True)
    os.makedirs(f"{build_dir}/objects", exist_ok=True)
    
    # Optionally seed gate-level netlist if reuse_synth=True
    if reuse_synth:
        base_synth_v = synth_base or "/home/a/ooo/build/asap7_closable_5.0ns/results/1_2_yosys.v"
        if os.path.exists(base_synth_v):
            target_synth_v = f"{build_dir}/results/1_2_yosys.v"
            if not os.path.exists(target_synth_v):
                print(f"Reusing synthesized netlist: {base_synth_v} -> {target_synth_v}")
                shutil.copy(base_synth_v, target_synth_v)
                base_dir = os.path.dirname(os.path.dirname(base_synth_v))
                base_stat = os.path.join(base_dir, "reports/synth_stat.txt")
                if os.path.exists(base_stat):
                    shutil.copy(base_stat, f"{build_dir}/reports/synth_stat.txt")
            os.utime(target_synth_v, None)
    
    if not clean:
        for f in ["1_synth.odb", "1_synth.sdc", "1_2_yosys.v", "1_2_yosys.sdc"]:
            p = os.path.join(build_dir, "results", f)
            if os.path.exists(p):
                os.utime(p, None)
    
    orfs_tag = "836842-26Q1-2900-gdf79404cd8"
    docker_bin = shutil.which("docker") or "/mnt/wsl/docker-desktop/cli-tools/usr/bin/docker"
    
    # 2. Run ORFS flow inside container
    cmd = [
        docker_bin, "run", "--rm",
        "-v", "/home/a/ooo:/home/a/ooo",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo:/OpenROAD-flow-scripts/flow/designs/asap7/rv32_ooo",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/designs/src/rv32_ooo:/OpenROAD-flow-scripts/flow/designs/src/rv32_ooo",
        "-v", "/home/a/OpenROAD-flow-scripts/flow/scripts:/OpenROAD-flow-scripts/flow/scripts",
        "-v", f"{build_dir}/results:/OpenROAD-flow-scripts/flow/results/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/logs:/OpenROAD-flow-scripts/flow/logs/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/reports:/OpenROAD-flow-scripts/flow/reports/asap7/rv32_ooo/base",
        "-v", f"{build_dir}/objects:/OpenROAD-flow-scripts/flow/objects/asap7/rv32_ooo/base",
        "-w", "/OpenROAD-flow-scripts/flow",
        f"openroad/flow-ubuntu22.04-builder:{orfs_tag}",
        "bash", "-c",
        "make DESIGN_CONFIG=designs/asap7/rv32_ooo/config.mk NUM_CORES=1 finish"
    ]
    
    print(f"Executing ORFS physical flow for T = {period_ns:.2f} ns in Docker...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    with open(f"{build_dir}/logs/make_finish.log", "w") as f:
        f.write(res.stdout + "\n" + res.stderr)
        
    odb_file = f"{build_dir}/results/6_final.odb"
    if not os.path.exists(odb_file):
        print(f"ERROR: 6_final.odb not found! Physical flow failed.")
        print("STDOUT tail:")
        print(res.stdout[-2000:])
        print("STDERR tail:")
        print(res.stderr[-2000:])
        return None
        
    print(f"Physical implementation complete. 6_final.odb generated ({os.path.getsize(odb_file) / (1024*1024):.1f} MB).")
    
    # 3. Perform STA signoff with hold repair and extraction
    metrics = run_sta_signoff(build_dir, period_ns, orfs_tag=orfs_tag)
    return metrics

if __name__ == "__main__":
    t = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else 5.0
    clean = "resume" not in sys.argv
    reuse = "--reuse-synth" in sys.argv
    base = None
    for arg in sys.argv:
        if arg.startswith("--synth-base="):
            base = arg.split("=", 1)[1]
    run_physical_implementation(t, clean=clean, reuse_synth=reuse, synth_base=base)
