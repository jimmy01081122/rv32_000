#!/usr/bin/env python3
"""Bind complete fixed-time measurements to actual candidate physical closure."""
import argparse
import json
import math
from pathlib import Path
import re
from baseline_contract import ROOT,sha
from experiment_contract import load_experiment
from check_physical_closure import review_collection
from measure_post_lsu_baseline import check_result


def geomean(values):
    if not values or any(not math.isfinite(v) or v<=0 for v in values):raise ValueError('invalid speedup denominator')
    return math.exp(sum(math.log(v) for v in values)/len(values))


def review(experiment_path,measurement,analysis):
    experiment,baseline=load_experiment(experiment_path)
    report=json.loads((measurement/'summary.json').read_text())
    physical=review_collection(analysis)
    collection=json.loads((analysis/'run.json').read_text())
    implementation=json.loads((analysis.parent/'run.json').read_text())
    digest=sha(experiment_path)
    if (report['experiment_manifest_sha256']!=digest or collection.get('experiment_manifest_sha256')!=digest
            or implementation.get('experiment_manifest_sha256')!=digest
            or implementation['rtl_files_sha256']!=experiment['candidate_rtl_files_sha256']):
        raise ValueError('measurement/physical/candidate identities differ')
    period=physical['smallest_tested_passing_period_ps']
    if not physical['passed'] or period!=report['core_period_ps']:
        raise ValueError('remeasure at the actual smallest tested passing candidate period')
    if any(p%100 for p in collection['clock_trials_ps']):raise ValueError('physical clock grid changed')
    if (period-baseline['physical']['period_grid_ps']) not in collection['clock_trials_ps']:
        raise ValueError('adjacent lower actual timing trial required')
    if report['memory_ps']!=10000 or not report['passed'] or report['start']!=report['end'] or report['start']['status']:
        raise ValueError('clean-source complete fixed-memory measurement required')
    if sha(ROOT/'scripts/measure_post_lsu_baseline.py')!=report['result_checker_sha256']:
        raise ValueError('measurement checker changed')
    eco=implementation.get('post_route_eco',{})
    required={'NUM_CORES=2','CORNER=TC','CORNERS=typical','GPL_RANDOM_SEED=',
              'REPORT_CLOCK_SKEW=0','OPT_POST_GRT_WNS=0','ADDER_MAP_FILE=',
              'SLEW_MARGIN=45','HOLD_SLACK_MARGIN=50'}
    if not required.issubset(implementation.get('worker_command',[])):
        raise ValueError('resolved physical command differs from baseline policy')
    if (eco.get('slew_margin_percent')!=45 or eco.get('hold_margin_ps')!=50 or
            not eco.get('final_full_route_recheck') or implementation['period_ps']!=14000 or
            implementation.get('cached_synthesis',{}).get('mapping_period_ps')!=5500 or
            implementation['synthesis_adder_mapping']!='abc'):
        raise ValueError('candidate physical flow differs from frozen comparison policy')
    text=(analysis.parent/'make.log').read_text()
    if 'RV32_GRT_FINAL_FULL_ROUTE_BEGIN' not in text or '[ERROR ' in text:raise ValueError('whole-route log incomplete')
    final=text.split('RV32_GRT_FINAL_FULL_ROUTE_BEGIN')[-1]
    total=re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)',final,re.M)
    if not total or total[-1][3:]!=('0','0','0'):raise ValueError('whole-design global-route overflow')
    failures=re.findall(r'Total Placement Failures:\s+(\d+)',text)
    if failures!=['0','0']:raise ValueError('both ECO placement passes must complete without failures')
    reference=ROOT/baseline['measurement']['formal_evidence']
    if sha(reference/'summary.json')!=report['baseline_summary_sha256']:raise ValueError('baseline summary changed')
    old={(r['family'],r['name']):r for r in json.loads((reference/'summary.json').read_text())['records']}
    rows=baseline['workloads'];records=report['records']
    if len(records)!=27 or [(r['family'],r['name']) for r in records]!=[(r['family'],r['name']) for r in rows]:
        raise ValueError('complete ordered 27-case denominator required')
    results=[];checked=0
    for row,record in zip(rows,records):
        directory=measurement/row['family']/row['name'];profile=directory/'profile.json';audit=directory/'memory.json'
        if (not record['passed'] or record['execution']['returncode']!=0 or sha(directory/'input.elf')!=row['elf_sha256']
                or sha(directory/'dut.log')!=record['execution']['log_sha256'] or sha(profile)!=record['profile_sha256']
                or sha(audit)!=record['memory_audit_sha256']):raise ValueError('measurement raw evidence changed')
        counters=json.loads(profile.read_text())
        result=check_result(row,(directory/'dut.log').read_text(),json.loads(audit.read_text()),period,10000,
                            directory/'input.elf',counters,require_reference_cycles=False)
        previous=reference/row['family']/row['name']/'profile.json'
        if sha(previous)!=old[row['family'],row['name']]['profile_sha256']:raise ValueError('reference profile changed')
        if result['problems'] or counters['retired_classes']!=json.loads(previous.read_text())['retired_classes']:
            raise ValueError('candidate numerical/memory/work equivalence failed')
        if result['numeric']:checked+=result['numeric']['checked_values']
        before=row['reference_cycles']*10000;after=result['cycles']*period
        results.append({'family':row['family'],'name':row['name'],'group':row.get('group'),
                        'baseline_cycles':row['reference_cycles'],'candidate_cycles':result['cycles'],
                        'baseline_time_ps':before,'candidate_time_ps':after,
                        'time_speedup':before/after,'cycle_speedup':row['reference_cycles']/result['cycles']})
    if checked!=3629:raise ValueError('FP32 numerical denominator changed')
    embedded=geomean([r['time_speedup'] for r in results if r['family']=='embench'])
    groups={g:geomean([r['time_speedup'] for r in results if r['group']==g]) for g in ['dsp','matrix_ml']}
    fp=math.sqrt(groups['dsp']*groups['matrix_ml'])
    area=physical['standard_cell_area_um2'];ratio=area/baseline['physical']['standard_cell_area_um2']
    targets={'embench_geomean_ge_1_20':embedded>=1.20,'fp32_geomean_ge_1_20':fp>=1.20,'area_ratio_le_1_10':ratio<=1.10}
    return {'scope':'qualified isolated CPU experiment at global-route research boundary; no detailed-route or full-ISA signoff',
            'experiment_id':experiment['experiment_id'],'experiment_manifest_sha256':digest,
            'measurement_summary_sha256':sha(measurement/'summary.json'),'physical_review':physical,
            'reviewer_sha256':sha(Path(__file__)),'core_period_ps':period,'memory_ps':10000,
            'standard_cell_area_um2':area,'area_ratio':ratio,'embench_time_geomean_speedup':embedded,
            'fp32_time_geomean_speedup':fp,'fp32_subgroup_speedup':groups,'planning_targets':targets,
            'all_planning_targets_met':all(targets.values()),'records':results,'passed':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--measurement',type=Path,required=True)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():p.error('fresh output under build required')
    try:result=review(args.experiment,args.measurement.resolve(),args.analysis.resolve())
    except (ValueError,KeyError,OSError,TypeError) as error:result={'passed':False,'error':str(error)}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['records','physical_review']},indent=2),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
