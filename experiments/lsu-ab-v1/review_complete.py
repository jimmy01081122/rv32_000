#!/usr/bin/env python3
"""Join independently reviewed AB physical and full-suite timing evidence."""
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
sys.path.insert(0,str(ROOT/'experiments/lsu-ab-v1'))
import review_physical as physical
import review_measurement as measurement
import diagnose_pid
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'fresh complete review required')
    native=physical.review(BASE/'native/physical-AB-v4/guard/independent-boundary-v1')
    retained=json.loads((BASE/'physical-review.json').read_text())
    require(native==retained,'independent physical review changed')
    fastest=native['AB_physical']['smallest_tested_passing_period_ps']
    scores={}
    for name,period in [('common_clock',10000),('fastest_tested',fastest)]:
        score=measurement.review(BASE/f'measurement-{period}ps-v1')
        require(score['period_ps']==period and period in native['AB_physical']['qualified_periods_ps'],'workload point lacks matching physical qualification')
        score['planning_targets']={
            'embench_geomean_ge_1_20':score['embench_time_geomean_speedup']>=1.20,
            'fp32_geomean_ge_1_20':score['fp32_time_geomean_speedup']>=1.20,
            'original_area_ratio_le_1_10':native['original_area_ratio']<=1.10}
        score['all_planning_targets_met']=all(score['planning_targets'].values())
        scores[name]=score
    parent=json.loads((BASE/'parent-comparison.json').read_text())
    require(parent['passed'] and parent['candidate']['measurement_summary_sha256']==scores['common_clock']['measurement_summary_sha256'],'parent comparison uses different AB measurement')
    for k in ['embench_time_geomean_speedup','fp32_time_geomean_speedup']:
        require(parent['candidate'][k]==scores['common_clock'][k],'parent comparison score differs')
    pid=json.loads((BASE/'pid-mechanism-review.json').read_text())
    require(pid['passed'] and pid['analyzer_sha256']==sha(Path(diagnose_pid.__file__)), 'PID reviewer changed')
    # Histogram keys are integers in memory and strings in the stored JSON.
    # Compare the same serialized representation while retaining every value.
    replay=json.loads(json.dumps({v:diagnose_pid.analyze(v) for v in ['A','AB']}))
    require(replay==pid['variants'], 'PID raw-signal reanalysis differs')
    result=dict(pid_mechanism_review_sha256=sha(BASE/'pid-mechanism-review.json'),passed=True,scope='AB isolated experiment qualified at global-route research boundary; no baseline promotion, tapeout signoff or full ISA/IEEE-754 claim',
                reviewer_sha256=sha(Path(__file__)),physical_review_sha256=sha(BASE/'physical-review.json'),
                physical=native,operating_points=scores,parent_comparison_sha256=sha(BASE/'parent-comparison.json'),
                common_clock_relative_to_parents=parent['relative_to_parents'],
                all_planning_targets_met_at_any_tested_point=any(s['all_planning_targets_met'] for s in scores.values()))
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,fastest_tested_period_ps=fastest,area_ratio=native['original_area_ratio'],scores={k:{q:v[q] for q in ['period_ps','embench_time_geomean_speedup','fp32_time_geomean_speedup','all_planning_targets_met']} for k,v in scores.items()}),indent=2))
if __name__=='__main__':main()
