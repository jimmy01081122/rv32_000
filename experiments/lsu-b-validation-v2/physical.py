#!/usr/bin/env python3
"""Fresh native shared-FPU physical construction under a separate v2 contract."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from run_physical_job import execute, write_json

CONTRACT = Path(__file__).with_name('contract.json')
REL = Path('results/asap7/rv32_post_lsu_v1/base')
MANIFEST = ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
SDC = '''create_clock -name core_clk -period 14000 [get_ports clk]
set_clock_uncertainty -setup 50 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_transition 20 [all_inputs]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 1100 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compact_intermediate_databases(directory):
    rows = []
    for path in sorted((directory/REL).glob('*.odb')):
        if path.name in ('5_1_grt.odb', '5_0_grt_input.odb') or path.is_symlink():
            continue
        target = path.with_suffix('.odb.gz')
        require(not target.exists(), 'compression target already exists')
        raw = path.read_bytes()
        with gzip.GzipFile(filename=str(target), mode='wb', mtime=0) as stream:
            stream.write(raw)
        require(gzip.decompress(target.read_bytes()) == raw, 'compression roundtrip failed')
        rows.append(dict(source=str(path), gzip=str(target), sha256=sha(path), raw_bytes=len(raw), stored_bytes=target.stat().st_size))
        path.unlink()
    write_json(directory/'intermediate-compaction.json', dict(scope='completed intermediate OpenDB caches only; final route retained', records=rows))


def run_stage(out, stage, variant, contract, incoming=None):
    out.mkdir(parents=True)
    sdc = out/'constraint.sdc';sdc.write_text(SDC)
    netlist = ROOT/contract['variants'][variant]['netlist']
    cfg = ROOT/'physical/asap7/baseline/config.mk'
    makefile = '/workspace/physical/asap7/baseline/eco.mk' if incoming else '/orfs-source/flow/Makefile'
    command = ['make', '-f', makefile, 'FLOW_HOME=/orfs-source/flow',
               'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7',
               'PLATFORMS_DIR=/OpenROAD-flow-scripts/flow/platforms',
               'OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
               'YOSYS_EXE=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys',
               'RV32_ROOT=/workspace', 'RV32_SDC='+str(sdc), 'WORK_HOME='+str(out),
               'DESIGN_CONFIG='+str(cfg), 'NUM_CORES=2', 'GPL_RANDOM_SEED=',
               'CORNER=TC', 'CORNERS=typical', 'REPORT_CLOCK_SKEW=0',
               'OPT_POST_GRT_WNS=0', 'ADDER_MAP_FILE=', 'VERILOG_FILES='+str(netlist),
               'SYNTH_NETLIST_FILES='+str(netlist)]
    inputs = {str(p):sha(p) for p in [CONTRACT,Path(__file__),MANIFEST,netlist,
              ROOT/contract['shared_link_manifest']['path'],ROOT/'scripts/run_physical_job.py',
              sdc,*sorted((ROOT/'physical/asap7/baseline').glob('*'))] if p.is_file()}
    report = dict(scope='shared-FPU v2 research physical validation; not baseline promotion',
                  variant=variant,stage=stage,contract_sha256=sha(CONTRACT),
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  source_status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines(),
                  construction_timing_corners=['TT'],period_ps=14000,
                  rtl_files_sha256=contract['variants'][variant]['rtl_files_sha256'],
                  linked_netlist_sha256=sha(netlist),local_image_id=contract['physical']['image_id'],
                  orfs_commit=contract['physical']['orfs_commit'],sdc_sha256=sha(sdc),
                  config_sha256=sha(cfg),command=command,passed=False)
    if incoming:
        prior = json.loads((incoming/'run.json').read_text())
        require(prior['flow_completed'] and prior['returncode']==0 and prior['input_identities_unchanged'], 'incomplete incoming route')
        require(prior['variant']==variant and prior['contract_sha256']==sha(CONTRACT), 'wrong incoming identity')
        require(sha(incoming/'make.log')==prior['log_sha256'], 'incoming native log changed')
        target = out/REL;target.mkdir(parents=True)
        for suffix in ('.odb','.sdc'):
            source=incoming/REL/('5_1_grt'+suffix);destination=target/('5_0_grt_input'+suffix)
            shutil.copyfile(source,destination);inputs[str(destination)]=sha(destination)
        eco=contract['physical']['post_route_eco']
        command += ['SLEW_MARGIN='+str(eco['slew_margin_percent']),
                    'HOLD_SLACK_MARGIN='+str(eco['hold_margin_ps']),'baseline-grt-eco']
        report['post_route_eco']={**eco,'construction_corner':'TT',
                                'script_sha256':sha(ROOT/'physical/asap7/baseline/repair.tcl'),
                                'makefile_sha256':sha(ROOT/'physical/asap7/baseline/eco.mk')}
        report['incoming_route']=dict(directory=str(incoming),report_sha256=sha(incoming/'run.json'),
                                      odb_sha256=sha(incoming/REL/'5_1_grt.odb'),sdc_sha256=sha(incoming/REL/'5_1_grt.sdc'))
    else:
        command.append('grt')
    write_json(out/'run.json',report)
    write_json(out/'job.json',dict(cwd=str(ROOT),command=command,report=str(out/'run.json'),log=str(out/'make.log'),inputs=inputs))
    require(execute(out/'job.json')==0, 'native '+stage+' failed; preserve this attempt')
    if incoming:
        text=(out/'make.log').read_text()
        require('RV32_GRT_FULL_ROUTE_COMPLETE' in text and 'RV32_GRT_ECO_COMPLETE' in text, 'missing full route/repair completion')
    compact_intermediate_databases(out)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=('baseline','B'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    require(ROOT==Path('/workspace'),'run inside the pinned runtime')
    require(out.is_relative_to(ROOT/'build') and not out.exists(),'fresh output under build required')
    contract=json.loads(CONTRACT.read_text())
    require(subprocess.check_output(['git','-C','/orfs-source','rev-parse','HEAD'],text=True).strip()==contract['physical']['orfs_commit'],'ORFS revision changed')
    require(not subprocess.check_output(['git','-C','/orfs-source','status','--porcelain']),'dirty ORFS')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'commit flow before physical qualification')
    for name,h in contract['unchanged_rtl'].items():require(sha(ROOT/name)==h,'B RTL changed: '+name)
    for row in contract['variants'].values():require(sha(ROOT/row['netlist'])==row['netlist_sha256'],'linked netlist changed')
    require(sha(ROOT/contract['shared_link_manifest']['path'])==contract['shared_link_manifest']['sha256'],'link proof changed')
    subprocess.run(['sha256sum','--strict','--quiet','-c',str(MANIFEST)],check=True)
    out.mkdir(parents=True)
    state=dict(variant=args.variant,contract_sha256=sha(CONTRACT),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stages=[],complete=False)
    write_json(out/'pipeline.json',state)
    for stage in ('grt','eco'):
        print('START',args.variant,stage,flush=True)
        run_stage(out/stage,stage,args.variant,contract,out/'grt' if stage=='eco' else None)
        state['stages'].append(stage);write_json(out/'pipeline.json',state)
        print('DONE',args.variant,stage,flush=True)
    subprocess.run(['sha256sum','--strict','--quiet','-c',str(MANIFEST)],check=True)
    state.update(complete=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(out/'pipeline.json',state)


if __name__=='__main__':main()
