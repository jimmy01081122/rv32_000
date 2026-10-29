#!/usr/bin/env python3
"""Apply the same proven noninverting input delay guard to baseline and B."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from run_physical_job import execute,write_json
CONTRACT=Path(__file__).with_name('contract-ready-guard.json')
REL=Path('results/asap7/rv32_post_lsu_v1/base')
REPORTS=Path('reports/asap7/rv32_post_lsu_v1/base')
MANIFEST=ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--variant',choices=['baseline','B'],required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();out=args.output.resolve();variant=args.variant
    require(ROOT==Path('/workspace'),'run in pinned native runtime');require(out.is_relative_to(ROOT/'build') and not out.exists(),'fresh build output required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'clean committed guard source required')
    contract=json.loads(CONTRACT.read_text());row=contract['variants'][variant];parent=ROOT/row['incoming_physical']['directory'];prior=json.loads((parent/'run.json').read_text())
    require(prior['flow_completed'] and prior['returncode']==0 and prior['input_identities_unchanged'] and not prior['source_status'],'completed clean hold40 predecessor required')
    require(prior['contract_sha256']==contract['incoming_contract']['sha256'] and sha(ROOT/contract['incoming_contract']['path'])==contract['incoming_contract']['sha256'] and prior['variant']==variant,'wrong predecessor contract/core')
    require(prior['rtl_files_sha256']==row['rtl_files_sha256'] and prior['linked_netlist_sha256']==row['netlist_sha256'],'wrong predecessor RTL/mapping')
    require(sha(parent/'run.json')==row['incoming_physical']['report_sha256'] and sha(parent/'make.log')==prior['log_sha256'],'predecessor evidence changed')
    require(sha(parent/REL/'5_1_grt.odb')==row['incoming_physical']['odb_sha256'] and sha(parent/REL/'5_1_grt.sdc')==row['incoming_physical']['sdc_sha256'],'predecessor database/SDC changed')
    require(subprocess.check_output(['git','-C','/orfs-source','rev-parse','HEAD'],text=True).strip()==contract['physical']['orfs_commit'] and not subprocess.check_output(['git','-C','/orfs-source','status','--porcelain']),'ORFS revision/status changed')
    for name,h in contract['unchanged_rtl'].items():require(sha(ROOT/name)==h,'B RTL changed')
    require(sha(ROOT/row['netlist'])==row['netlist_sha256'] and sha(ROOT/contract['shared_link_manifest']['path'])==contract['shared_link_manifest']['sha256'],'linked mapping changed')
    model=ROOT/contract['guard_function_model']['path'];require(sha(model)==contract['guard_function_model']['sha256'],'guard model changed');design=json.loads(model.read_text());require(set(design['modules'])=={'BUFx2_ASAP7_75t_R'},'wrong buffer model');cell=design['modules']['BUFx2_ASAP7_75t_R'];require(not cell['cells'] and set(cell['ports'])=={'A','Y'} and cell['ports']['A']['direction']=='input' and cell['ports']['Y']['direction']=='output' and cell['ports']['A']['bits']==cell['ports']['Y']['bits'] and len(cell['ports']['A']['bits'])==1,'guard is not a pure noninverting wire')
    subprocess.run(['sha256sum','--strict','--quiet','-c',str(MANIFEST)],check=True)
    out.mkdir(parents=True);stage=out/'guard';stage.mkdir();(stage/REL).mkdir(parents=True)
    os.link(parent/REL/'5_1_grt.odb',stage/REL/'5_0_grt_input.odb');shutil.copyfile(parent/REL/'5_1_grt.sdc',stage/REL/'5_0_grt_input.sdc');shutil.copyfile(parent/'constraint.sdc',stage/'constraint.sdc')
    command=list(prior['command']);index=command.index('-f');command[index+1]='/workspace/experiments/lsu-b-validation-v2/ready_guard.mk'
    command=[('WORK_HOME='+str(stage)) if x.startswith('WORK_HOME=') else ('RV32_SDC='+str(stage/'constraint.sdc')) if x.startswith('RV32_SDC=') else 'ready-hold-guard' if x=='baseline-grt-eco' else x for x in command]
    files=[CONTRACT,Path(__file__),Path(__file__).with_suffix('.tcl'),Path(__file__).with_suffix('.mk'),ROOT/'scripts/run_physical_job.py',MANIFEST,model,ROOT/contract['incoming_contract']['path'],ROOT/row['netlist'],ROOT/contract['shared_link_manifest']['path'],parent/'run.json',parent/'make.log',parent/REL/'5_1_grt.odb',parent/REL/'5_1_grt.sdc',stage/'constraint.sdc',stage/REL/'5_0_grt_input.odb',stage/REL/'5_0_grt_input.sdc',*sorted((ROOT/'physical/asap7/baseline').glob('*'))]
    inputs={str(p):sha(p) for p in files if p.is_file()};state=dict(variant=variant,contract_sha256=sha(CONTRACT),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stages=[],complete=False);write_json(out/'pipeline.json',state)
    report=dict(scope='uniform ready input delay guard; physical acceptance pending independent corners',stage='guard',variant=variant,contract_sha256=sha(CONTRACT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_status=[],construction_timing_corners=['TT'],period_ps=14000,rtl_files_sha256=row['rtl_files_sha256'],linked_netlist_sha256=row['netlist_sha256'],local_image_id=contract['physical']['image_id'],orfs_commit=contract['physical']['orfs_commit'],sdc_sha256=sha(stage/'constraint.sdc'),config_sha256=sha(ROOT/'physical/asap7/baseline/config.mk'),command=command,uniform_input_guard=contract['physical']['uniform_input_guard'],guard_script_sha256=sha(Path(__file__).with_suffix('.tcl')),guard_makefile_sha256=sha(Path(__file__).with_suffix('.mk')),guard_function_model_sha256=sha(model),incoming_route=row['incoming_physical'],passed=False)
    write_json(stage/'run.json',report);write_json(stage/'job.json',dict(cwd=str(ROOT),command=command,report=str(stage/'run.json'),log=str(stage/'make.log'),inputs=inputs));print('START',variant,'uniform ready guard',flush=True)
    require(execute(stage/'job.json')==0,'native guard failed; preserve attempt')
    text=(stage/'make.log').read_text();require(all(t in text for t in ['RV32_GUARD_FULL_ROUTE_COMPLETE','RV32_GUARD_CONNECTIVITY_PASS','RV32_GUARD_COMPLETE']),'missing native guard proof/completion')
    audit=stage/REPORTS/'ready_guard_connectivity.json';data=json.loads(audit.read_text());require(data['passed'] and data['all_other_cells_masters_pins_ports_unchanged'] and data['final_cells']==data['original_cells']+1 and data['original_pins_checked']>0 and data['redirected_input_loads']>0,'incomplete original graph preservation')
    report=json.loads((stage/'run.json').read_text());report['connectivity_audit_sha256']=sha(audit);write_json(stage/'run.json',report)
    subprocess.run(['sha256sum','--strict','--quiet','-c',str(MANIFEST)],check=True);state.update(stages=['guard'],complete=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());write_json(out/'pipeline.json',state);print('DONE',variant,'uniform ready guard',flush=True)
if __name__=='__main__':main()
