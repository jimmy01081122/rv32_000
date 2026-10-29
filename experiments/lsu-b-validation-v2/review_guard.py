#!/usr/bin/env python3
"""Final B admission with identical input guards and full native graph preservation."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review as previous
from review import ROOT,BASE,REL,sha,require,guest_path,logical_sha,review_formal,review_measurement,load_experiment,review_collection
PARENT_CONTRACT=Path(__file__).with_name('contract-hold40.json')
CONTRACT=Path(__file__).with_name('contract-ready-guard.json')

def review_parent(analysis,variant,contract):
    stage=analysis.parent;implementation=json.loads((stage/'run.json').read_text());collection=json.loads((analysis/'run.json').read_text())
    require(implementation['variant']==variant and collection['variant']==variant and implementation['contract_sha256']==sha(PARENT_CONTRACT) and collection['contract_sha256']==sha(PARENT_CONTRACT),'v2 physical variant/contract mismatch')
    expected=contract['variants'][variant]
    require(implementation['rtl_files_sha256']==expected['rtl_files_sha256'] and implementation['linked_netlist_sha256']==expected['netlist_sha256'] and sha(ROOT/expected['netlist'])==expected['netlist_sha256'],'physical RTL/netlist differs')
    pipeline=json.loads((stage.parent/'pipeline.json').read_text())
    require(pipeline['complete'] and pipeline['stages']==['grt-reused','eco'] and pipeline['contract_sha256']==sha(PARENT_CONTRACT) and pipeline['variant']==variant,'incomplete physical pipeline')
    for name in ('grt','eco'):
        run=stage.parent/name;data=json.loads((run/'run.json').read_text());job=json.loads((run/'job.json').read_text())
        require(data['flow_completed'] and data['returncode']==0 and data['input_identities_unchanged'] and not data['source_status'] and data['construction_timing_corners']==['TT'],'unclean/incomplete native physical stage')
        expected_contract=contract['incoming_contract']['sha256'] if name=='grt' else sha(PARENT_CONTRACT)
        require(data['contract_sha256']==expected_contract and data['variant']==variant,'physical stage identity mismatch')
        require(data['command']==job['command'] and sha(run/'make.log')==data['log_sha256'],'physical command/log changed')
        for path,digest in job['inputs'].items():require(logical_sha(guest_path(path))==digest,'physical input changed: '+path)
        require(data['local_image_id']==contract['physical']['image_id'] and data['orfs_commit']==contract['physical']['orfs_commit'] and data['period_ps']==14000,'physical tool/source/period mismatch')
    eco=contract['physical']['post_route_eco'];required={'NUM_CORES=2','CORNER=TC','CORNERS=typical','GPL_RANDOM_SEED=','REPORT_CLOCK_SKEW=0','OPT_POST_GRT_WNS=0','ADDER_MAP_FILE=','SLEW_MARGIN='+str(eco['slew_margin_percent']),'HOLD_SLACK_MARGIN='+str(eco['hold_margin_ps'])}
    require(required.issubset(implementation['command']) and all(implementation['post_route_eco'].get(k)==v for k,v in eco.items()),'v2 ECO construction differs')
    incoming=stage.parent/'grt';chain=implementation['incoming_route']
    require(sha(incoming/'run.json')==chain['report_sha256'] and sha(incoming/REL/'5_1_grt.odb')==chain['odb_sha256'] and sha(stage/REL/'5_0_grt_input.odb')==chain['odb_sha256'],'physical incoming-route chain differs')
    text=(stage/'make.log').read_text()
    require('RV32_GRT_FINAL_FULL_ROUTE_BEGIN' in text and 'RV32_GRT_FULL_ROUTE_COMPLETE' in text and 'RV32_GRT_ECO_COMPLETE' in text and '[ERROR ' not in text,'whole-route recheck incomplete')
    final=text.split('RV32_GRT_FINAL_FULL_ROUTE_BEGIN')[-1]
    total=re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)',final,re.M)
    require(total and total[-1][3:]==('0','0','0'),'nonzero global-route overflow')
    require(re.findall(r'Total Placement Failures:\s+(\d+)',text)==['0','0'],'ECO placement failures')
    for kind in ('net','pin'):
        require(re.findall(r'Found (\d+) '+kind+r' violations\.',final)==['0'],'antenna '+kind+' violations')
    physical=review_collection(analysis)
    physical.update(variant=variant,contract_sha256=sha(PARENT_CONTRACT),source_commit=implementation['source_commit'],upstream_source_commit=json.loads((incoming/'run.json').read_text())['source_commit'],whole_route_overflow=[0,0,0],antenna_net_pin_violations=[0,0])
    physical['scope']='predecessor construction and actual timing evidence only; failed predecessor clocks are not admitted'
    return physical


def review_guard(analysis,variant,contract):
    stage=analysis.parent;data=json.loads((stage/'run.json').read_text());job=json.loads((stage/'job.json').read_text());collection=json.loads((analysis/'run.json').read_text());policy=contract['variants'][variant]
    require(data['stage']=='guard' and data['variant']==variant and collection['variant']==variant and data['contract_sha256']==sha(CONTRACT) and collection['contract_sha256']==sha(CONTRACT),'guard variant/contract mismatch')
    require(data['uniform_input_guard']==contract['physical']['uniform_input_guard'] and data['incoming_route']==policy['incoming_physical'],'guard rule/predecessor mismatch')
    require(data['flow_completed'] and data['returncode']==0 and data['input_identities_unchanged'] and not data['source_status'] and data['construction_timing_corners']==['TT'],'incomplete/unclean native guard construction')
    require(data['rtl_files_sha256']==policy['rtl_files_sha256'] and data['linked_netlist_sha256']==policy['netlist_sha256'] and sha(ROOT/policy['netlist'])==policy['netlist_sha256'],'guard RTL or mapped input changed')
    require(data['local_image_id']==contract['physical']['image_id'] and data['orfs_commit']==contract['physical']['orfs_commit'] and data['period_ps']==14000,'guard tools/construction period changed')
    require(data['command']==job['command'] and sha(stage/'make.log')==data['log_sha256'],'guard command/log changed')
    required={'NUM_CORES=2','CORNER=TC','CORNERS=typical','GPL_RANDOM_SEED=','REPORT_CLOCK_SKEW=0','OPT_POST_GRT_WNS=0','ADDER_MAP_FILE=','ready-hold-guard'}
    require(required.issubset(data['command']) and data['command'][:3]==['timeout','--signal=TERM','3600'],'guard native execution policy changed')
    for name,h in job['inputs'].items():require(logical_sha(guest_path(name))==h,'guard input changed: '+name)
    for name,key in [('ready_guard.tcl','guard_script_sha256'),('ready_guard.mk','guard_makefile_sha256')]:require(sha(Path(__file__).with_name(name))==data[key],'guard source changed')
    pipeline=json.loads((stage.parent/'pipeline.json').read_text());require(pipeline['complete'] and pipeline['stages']==['guard'] and pipeline['variant']==variant and pipeline['contract_sha256']==sha(CONTRACT),'guard pipeline incomplete')
    parent=ROOT/policy['incoming_physical']['directory'];expected=policy['incoming_physical'];require(sha(parent/'run.json')==expected['report_sha256'] and sha(parent/REL/'5_1_grt.odb')==expected['odb_sha256'] and sha(parent/REL/'5_1_grt.sdc')==expected['sdc_sha256'],'guard predecessor checkpoint changed')
    parent_policy=json.loads(PARENT_CONTRACT.read_text());require(sha(PARENT_CONTRACT)==contract['incoming_contract']['sha256'],'parent hold40 contract changed')
    ancestor=review_parent(parent/'independent-sta-v1',variant,parent_policy)
    model_path=ROOT/contract['guard_function_model']['path'];require(sha(model_path)==contract['guard_function_model']['sha256']==data['guard_function_model_sha256'],'buffer function proof changed');model=json.loads(model_path.read_text())['modules'];require(set(model)=={'BUFx2_ASAP7_75t_R'},'wrong guard model');cell=model['BUFx2_ASAP7_75t_R'];require(not cell['cells'] and set(cell['ports'])=={'A','Y'} and cell['ports']['A']['direction']=='input' and cell['ports']['Y']['direction']=='output' and cell['ports']['A']['bits']==cell['ports']['Y']['bits'] and len(cell['ports']['A']['bits'])==1 and isinstance(cell['ports']['A']['bits'][0],int),'buffer does not implement Y=A')
    text=(stage/'make.log').read_text();require(all(t in text for t in ['RV32_GUARD_FULL_ROUTE_BEGIN','RV32_GUARD_FULL_ROUTE_COMPLETE','RV32_GUARD_CONNECTIVITY_PASS','RV32_GUARD_COMPLETE']) and '[ERROR ' not in text,'guard native proof incomplete')
    final=text.split('RV32_GUARD_FULL_ROUTE_BEGIN')[-1];total=re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)',final,re.M);require(total and total[-1][3:]==('0','0','0'),'guard full route overflow');require(re.findall(r'Total Placement Failures:\s+(\d+)',text)==['0'],'guard placement failures')
    for kind in ['net','pin']:require(re.findall(r'Found (\d+) '+kind+r' violations\.',final)==['0'],'guard antenna violation')
    audit_path=stage/'reports/asap7/rv32_post_lsu_v1/base/ready_guard_connectivity.json';require(sha(audit_path)==data['connectivity_audit_sha256'],'native topology proof changed');audit=json.loads(audit_path.read_text());require(audit['passed'] and audit['all_other_cells_masters_pins_ports_unchanged'] and audit['final_cells']==audit['original_cells']+1 and audit['original_pins_checked']>0 and audit['boundary_ports_checked']>0 and audit['redirected_input_loads']>0 and audit['master']=='BUFx2_ASAP7_75t_R','original graph preservation incomplete')
    physical=review_collection(analysis);require(physical['passed'],'guard has no fully qualified period');periods=collection['clock_trials_ps'];fastest=physical['smallest_tested_passing_period_ps'];require(all(p%100==0 for p in periods) and fastest-100 in periods,'actual adjacent faster failure required')
    old=ancestor['records'][0];new=physical['records'][0];require(audit['original_cells']==old['standard_cell_count'] and audit['final_cells']==new['standard_cell_count'] and new['register_count']==old['register_count'],'guard changed state or unexpected cell count');require(math.isclose(new['standard_cell_area_um2']-old['standard_cell_area_um2'],float(cell['attributes']['area']),abs_tol=1e-6),'area differs from exactly one guard buffer')
    physical.update(variant=variant,guard_source_commit=data['source_commit'],predecessor_source_commit=ancestor['source_commit'],predecessor_GRT_source_commit=ancestor['upstream_source_commit'],native_topology_audit=audit,predecessor_timing_passed=ancestor['passed'],predecessor_analysis_sha256=ancestor['analysis_report_sha256'],whole_route_overflow=[0,0,0],antenna_net_pin_violations=[0,0])
    return physical


def review_extra_formal(contract,formal):
    link_path=BASE/'formal-to-physical-link-review.json';link=json.loads(link_path.read_text());require(link['passed'] and link['proof_summary_sha256']==formal['proof_summary_sha256'] and link['shared_graph_sha256']==contract['shared_fpu_graph_sha256'] and link['contract_sha256']==sha(PARENT_CONTRACT),'full formal is not bound to common physical mapping')
    for name in ['baseline','B']:require(link['linked_cores'][name]['linked_netlist_sha256']==contract['variants'][name]['netlist_sha256'],'formal/physical linked core differs')
    for name in ['step-gold','step-gate','reset-gold','reset-gate']:
        path=BASE/'fpu-state-relation-v1'/(name+'-lowered.json');raw=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes());module=json.loads(raw)['modules']['rv32_ooo_fp_execute'];bits=[b for c in module['cells'].values() for v in c['connections'].values() for b in v]+[b for p in module['ports'].values() for b in p['bits']];require(all(isinstance(b,int) or b in ('0','1') for b in bits),'undefined bit in Boolean formal obligation')
    return dict(passed=True,formal_to_physical_link_review_sha256=sha(link_path),functional_proof_bits_defined=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ['b-analysis','baseline-analysis','measurement','build-summary','qualification-summary','output']:ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--comparison',choices=['common-clock','fastest'],required=True);args=ap.parse_args();require(not args.output.exists(),'fresh final review output required')
    contract=json.loads(CONTRACT.read_text());experiment,baseline=load_experiment(ROOT/'experiments/lsu-b-v1/manifest.json');require(sha(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json')==contract['baseline_manifest_sha256'] and sha(ROOT/'experiments/lsu-b-v1/manifest.json')==contract['b_manifest_sha256'],'frozen contracts changed');require(sha(ROOT/contract['shared_link_manifest']['path'])==contract['shared_link_manifest']['sha256'],'shared link proof changed')
    formal=review_formal();extra=review_extra_formal(contract,formal);control=review_guard(args.baseline_analysis.resolve(),'baseline',contract);candidate=review_guard(args.b_analysis.resolve(),'B',contract)
    for key in ['guard_source_commit','predecessor_source_commit','predecessor_GRT_source_commit']:require(control[key]==candidate[key],'baseline/B construction sources differ: '+key)
    require(10000 in control['qualified_periods_ps'],'same-flow baseline does not qualify original reference clock')
    score=review_measurement(args.measurement.resolve(),candidate,experiment,baseline,args.build_summary,args.qualification_summary,args.comparison);area=candidate['standard_cell_area_um2'];ratio=area/baseline['physical']['standard_cell_area_um2'];same=area/control['standard_cell_area_um2'];targets=dict(embench_geomean_ge_1_20=score['embench_time_geomean_speedup']>=1.20,fp32_geomean_ge_1_20=score['fp32_time_geomean_speedup']>=1.20,original_area_ratio_le_1_10=ratio<=1.10,same_flow_area_ratio_le_1_10=same<=1.10)
    result=dict(scope='B experiment contract completed with a common input guard at global-route research boundary; no baseline promotion or full ISA/IEEE-754/detailed-route signoff',passed=True,reviewer_sha256=sha(Path(__file__)),predecessor_reviewer_sha256=sha(Path(previous.__file__)),contract_sha256=sha(CONTRACT),formal=formal,extra_formal_binding=extra,baseline_physical=control,B_physical=candidate,measurement=score,original_area_ratio=ratio,same_flow_area_ratio=same,planning_targets=targets,all_planning_targets_met=all(targets.values()));args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['formal','extra_formal_binding','baseline_physical','B_physical','measurement']},indent=2))
if __name__=='__main__':main()
