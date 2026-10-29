#!/usr/bin/env python3
"""Admit B only with reset/step FPU proof, same-flow physical and full27 evidence."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from check_physical_closure import review_collection
from experiment_contract import load_experiment
from experiment_provenance import review_provenance,measurement_command,retired_work
from measure_post_lsu_baseline import check_result
from review_cpu_experiment import geomean,qualified_period
CONTRACT=ROOT/'experiments/lsu-b-validation-v2/contract-hold40.json'
BASE=ROOT/'build/experiments/lsu-b-validation-v2'
REL=Path('results/asap7/rv32_post_lsu_v1/base')


def require(ok,message):
    if not ok:raise ValueError(message)


def guest_path(path):
    path=Path(path)
    return ROOT/path.relative_to('/workspace') if path.is_relative_to('/workspace') and not path.is_relative_to(ROOT) else path


def logical_sha(path):
    if path.is_file():return sha(path)
    zipped=Path(str(path)+'.gz')
    return hashlib.sha256(gzip.decompress(zipped.read_bytes())).hexdigest()


def review_formal():
    directory=BASE/'fpu-state-relation-v1';report=json.loads((directory/'proof-summary.json').read_text())
    require(report['passed'] and report['input_identities_unchanged'] and report['state']=='finished','incomplete FPU proof')
    for path,digest in report['inputs'].items():
        if path.startswith('/workspace/'):
            require(logical_sha(guest_path(path))==digest,'formal input changed: '+path)
    stages={r['stage']:r for r in report['stages']}
    expected={'reset-gold-proof':True,'reset-gate-proof':True,'step-output-proof':True,'negative-bit-proof':False}
    require(set(stages)==set(expected)|{'lower-'+n for n in ['reset-gold','reset-gold-zero','reset-gate','reset-gate-zero','step-gold','step-gate','step-mutant']},'incomplete formal obligation set')
    for label,equal in expected.items():
        row=stages[label];log=directory/(label+'.log');text=log.read_text()
        require(row['passed'] and row['returncode']==0 and row['expected_equivalent']==equal and sha(log)==row['log_sha256'],'formal native result changed')
        require(('Networks are equivalent' in text)==equal and ('Networks are NOT EQUIVALENT' in text)!=equal,'formal native proof marker differs')
    for label,row in stages.items():
        if not label.startswith('lower-'):continue
        name=label.removeprefix('lower-')
        require(row['returncode']==0 and row['no_remaining_state'] and sha(directory/(name+'.ys'))==row['script_sha256'] and sha(directory/(name+'.log'))==row['log_sha256'] and sha(directory/(name+'.blif'))==row['blif_sha256'],'formal lowering evidence changed')
    replay_dir=BASE/'fpu-frontend-replay-v1';replay=json.loads((replay_dir/'summary.json').read_text())
    require(replay['passed'] and replay['platform_before'] and replay['platform_after'] and replay['input_identities_unchanged'] and replay['proof_summary_sha256']==sha(directory/'proof-summary.json'),'native frontend reproduction missing')
    require(len(replay['records'])==2 and all(r['returncode']==0 and r['identical'] and r['fresh_sha256']==r['original_sha256'] for r in replay['records']),'frontend models differ')
    require(len(replay['regenerated_models'])==7 and all(logical_sha(directory/'models'/n)==h and logical_sha(replay_dir/'models'/n)==h for n,h in replay['regenerated_models'].items()),'FPU generated model reproduction failed')
    negative_dir=BASE/'fpu-negative-controls-v1';negative=json.loads((negative_dir/'summary.json').read_text())
    require(negative['passed'] and negative['input_identities_unchanged'] and len(negative['records'])==6 and all(r['rejected'] for r in negative['records']),'FPU RTL/shape negatives incomplete')
    for label in ('rtl-drop-valid','rtl-reset-high'):
        row=next(r for r in negative['records'] if r['label']==label);text=(negative_dir/label/'cec.log').read_text()
        require(sha(negative_dir/label/'mutant.v')==row['source_sha256'] and 'Networks are NOT EQUIVALENT' in text and 'Networks are equivalent' not in text,'actual RTL mutation was not rejected')
        require(sha(negative_dir/label/'cec.log')==row['commands'][-1]['log_sha256'],'RTL negative native log changed')
    return dict(passed=True,scope='complete two-state FPU implementation equivalence after one synchronous reset edge; no arithmetic cutpoints; not IEEE-754 conformance',original_state_bits=156,mapped_state_bits=100,obligations=expected,proof_summary_sha256=sha(directory/'proof-summary.json'),frontend_replay_sha256=sha(replay_dir/'summary.json'),negative_summary_sha256=sha(negative_dir/'summary.json'))


def review_physical(analysis,variant,contract):
    stage=analysis.parent;implementation=json.loads((stage/'run.json').read_text());collection=json.loads((analysis/'run.json').read_text())
    require(implementation['variant']==variant and collection['variant']==variant and implementation['contract_sha256']==sha(CONTRACT) and collection['contract_sha256']==sha(CONTRACT),'v2 physical variant/contract mismatch')
    expected=contract['variants'][variant]
    require(implementation['rtl_files_sha256']==expected['rtl_files_sha256'] and implementation['linked_netlist_sha256']==expected['netlist_sha256'] and sha(ROOT/expected['netlist'])==expected['netlist_sha256'],'physical RTL/netlist differs')
    pipeline=json.loads((stage.parent/'pipeline.json').read_text())
    require(pipeline['complete'] and pipeline['stages']==['grt-reused','eco'] and pipeline['contract_sha256']==sha(CONTRACT) and pipeline['variant']==variant,'incomplete physical pipeline')
    for name in ('grt','eco'):
        run=stage.parent/name;data=json.loads((run/'run.json').read_text());job=json.loads((run/'job.json').read_text())
        require(data['flow_completed'] and data['returncode']==0 and data['input_identities_unchanged'] and not data['source_status'] and data['construction_timing_corners']==['TT'],'unclean/incomplete native physical stage')
        expected_contract=contract['incoming_contract']['sha256'] if name=='grt' else sha(CONTRACT)
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
    require(physical['passed'],'no period passes all TT/SS/FF checks')
    periods=collection['clock_trials_ps'];fastest=physical['smallest_tested_passing_period_ps'];grid=contract['physical']['period_grid_ps']
    require(not any(p%grid for p in periods) and fastest-grid in periods,'missing actual adjacent faster clock failure')
    physical.update(variant=variant,contract_sha256=sha(CONTRACT),source_commit=implementation['source_commit'],upstream_source_commit=json.loads((incoming/'run.json').read_text())['source_commit'],whole_route_overflow=[0,0,0],antenna_net_pin_violations=[0,0])
    return physical


def review_measurement(measurement,physical,experiment,baseline,build,qualification,comparison):
    experiment_path=ROOT/'experiments/lsu-b-v1/manifest.json';report=json.loads((measurement/'summary.json').read_text());provenance,normal=review_provenance(experiment_path,experiment,report,build,qualification)
    period=report['core_period_ps'];require(report['passed'] and report['memory_ps']==10000 and report['start']==report['end'] and not report['start']['status'],'clean fixed-memory measurement required')
    require(period in physical['qualified_periods_ps'],'measurement clock not independently qualified')
    if comparison=='common-clock':require(period==10000,'common-clock must use frozen 10000 ps')
    elif comparison=='fastest':require(period==physical['smallest_tested_passing_period_ps'],'fastest comparison must use actual shortest qualified period')
    else:raise ValueError('unknown comparison point')
    require(report['experiment_manifest_sha256']==sha(experiment_path) and report['result_checker_sha256']==sha(ROOT/'scripts/measure_post_lsu_baseline.py'),'measurement contract/checker differs')
    reference=ROOT/baseline['measurement']['formal_evidence'];require(sha(reference/'summary.json')==report['baseline_summary_sha256']==baseline['measurement']['formal_summary_sha256'],'frozen baseline measurement changed')
    old={(r['family'],r['name']):r for r in json.loads((reference/'summary.json').read_text())['records']};records=report['records'];rows=baseline['workloads']
    require(len(records)==27 and [(r['family'],r['name']) for r in records]==[(r['family'],r['name']) for r in rows],'complete ordered 27 workloads required')
    results=[];checked=0
    for row,record in zip(rows,records):
        directory=measurement/row['family']/row['name'];profile=directory/'profile.json';audit=directory/'memory.json';measurement_command(record,normal,directory,period)
        require(record['passed'] and record['execution']['returncode']==0 and sha(directory/'input.elf')==row['elf_sha256'] and sha(directory/'dut.log')==record['execution']['log_sha256'] and sha(profile)==record['profile_sha256'] and sha(audit)==record['memory_audit_sha256'],'measurement raw evidence changed')
        counters=json.loads(profile.read_text());result=check_result(row,(directory/'dut.log').read_text(),json.loads(audit.read_text()),period,10000,directory/'input.elf',counters,require_reference_cycles=False)
        previous=reference/row['family']/row['name']/'profile.json';require(sha(previous)==old[row['family'],row['name']]['profile_sha256'],'baseline profile changed');original=json.loads(previous.read_text())
        require(not result['problems'] and counters['retired_classes']==original['retired_classes'] and retired_work(counters)==retired_work(original),'numerical/memory/per-PC work equivalence failed')
        if result['numeric']:checked+=result['numeric']['checked_values']
        before=row['reference_cycles']*10000;after=result['cycles']*period
        results.append(dict(family=row['family'],name=row['name'],group=row.get('group'),baseline_cycles=row['reference_cycles'],candidate_cycles=result['cycles'],baseline_time_ps=before,candidate_time_ps=after,time_speedup=before/after))
    require(checked==3629,'complete FP numerical denominator required')
    embedded=geomean([r['time_speedup'] for r in results if r['family']=='embench']);groups={g:geomean([r['time_speedup'] for r in results if r['group']==g]) for g in ['dsp','matrix_ml']};fp=math.sqrt(groups['dsp']*groups['matrix_ml'])
    return dict(passed=True,comparison_point=comparison,period_ps=period,memory_ps=10000,measurement_summary_sha256=sha(measurement/'summary.json'),functional_provenance=provenance,per_pc_work_matches=True,numerical_values_checked=checked,embench_time_geomean_speedup=embedded,fp32_time_geomean_speedup=fp,fp32_subgroup_speedup=groups,records=results)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('b-analysis','baseline-analysis','measurement','build-summary','qualification-summary','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--comparison',choices=['common-clock','fastest'],required=True);args=p.parse_args();require(not args.output.exists(),'fresh review output required')
    contract=json.loads(CONTRACT.read_text());experiment,baseline=load_experiment(ROOT/'experiments/lsu-b-v1/manifest.json')
    require(sha(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json')==contract['baseline_manifest_sha256'] and sha(ROOT/'experiments/lsu-b-v1/manifest.json')==contract['b_manifest_sha256'],'original frozen contracts changed')
    require(sha(ROOT/contract['shared_link_manifest']['path'])==contract['shared_link_manifest']['sha256'],'shared mapping link proof changed')
    require(sha(ROOT/contract['incoming_contract']['path'])==contract['incoming_contract']['sha256'],'upstream construction contract changed')
    formal=review_formal();control=review_physical(args.baseline_analysis.resolve(),'baseline',contract);candidate=review_physical(args.b_analysis.resolve(),'B',contract)
    require(control['source_commit']==candidate['source_commit'] and control['upstream_source_commit']==candidate['upstream_source_commit'],'baseline/B construction source differs')
    require(10000 in control['qualified_periods_ps'],'same-flow baseline lacks original reference clock qualification')
    score=review_measurement(args.measurement.resolve(),candidate,experiment,baseline,args.build_summary,args.qualification_summary,args.comparison)
    area=candidate['standard_cell_area_um2'];old_area=baseline['physical']['standard_cell_area_um2'];ratio=area/old_area;same_ratio=area/control['standard_cell_area_um2']
    targets=dict(embench_geomean_ge_1_20=score['embench_time_geomean_speedup']>=1.20,fp32_geomean_ge_1_20=score['fp32_time_geomean_speedup']>=1.20,original_area_ratio_le_1_10=ratio<=1.10,same_flow_area_ratio_le_1_10=same_ratio<=1.10)
    result=dict(scope='B experiment contract completed at global-route research boundary; not detailed-route/full-ISA/IEEE-754 specification signoff; frozen baseline not promoted',passed=True,reviewer_sha256=sha(Path(__file__)),contract_sha256=sha(CONTRACT),formal=formal,baseline_physical=control,B_physical=candidate,measurement=score,original_area_ratio=ratio,same_flow_area_ratio=same_ratio,planning_targets=targets,all_planning_targets_met=all(targets.values()))
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('formal','baseline_physical','B_physical','measurement')},indent=2))


if __name__=='__main__':main()
