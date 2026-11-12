#!/usr/bin/env python3
"""Reconcile measured A-to-AB changes without attributing causality to wait buckets."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
sys.path.insert(0,str(ROOT/'experiments/lsu-ab-v1'))
sys.path.insert(0,str(ROOT/'experiments/optimization-135-v1'))
import analyze_bottlenecks as refs
from review_measurement import review
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    require(not args.output.exists(),'preserve prior report')
    original=refs.analyze();candidate=review(ROOT/'build/experiments/lsu-ab-v1/measurement-10000ps-v1')
    paths={'A':ROOT/refs.retained.MEASUREMENTS['A'],'AB':ROOT/'build/experiments/lsu-ab-v1/measurement-10000ps-v1'}
    summaries={k:json.loads((p/'summary.json').read_text()) for k,p in paths.items()}
    source_hashes={str(p/'summary.json'):sha(p/'summary.json') for p in paths.values()}
    all_rows=[]
    for row in candidate['records']:
        name=row['name'];family=row['family'];profiles={}
        for v,p in paths.items():
            source=p/family/name/'profile.json';digest=sha(source)
            matched=[r for r in summaries[v]['records'] if (r['family'],r['name'])==(family,name)]
            require(len(matched)==1 and matched[0]['profile_sha256']==digest,'profile differs from reviewed measurement')
            source_hashes[str(source.relative_to(ROOT))]=digest;profiles[v]=json.loads(source.read_text())
        a,b=profiles['A'],profiles['AB'];pa,pb=a['cycle_partition'],b['cycle_partition']
        require(sum(pa.values())==a['cycles'] and sum(pb.values())==b['cycles'],'exclusive partition does not sum to ROI cycles')
        require(a['retired_classes']==b['retired_classes'],'instruction work changed')
        delta={key:pb.get(key,0)-pa.get(key,0) for key in sorted(set(pa)|set(pb))}
        require(sum(delta.values())==b['cycles']-a['cycles'],'partition delta does not reconcile')
        ap={p['pc']:p for p in a['pcs']};bp={p['pc']:p for p in b['pcs']}
        require(set(ap)==set(bp) and all((ap[p]['insn'],ap[p]['retired'])==(bp[p]['insn'],bp[p]['retired']) for p in ap),'per-PC retired work changed')
        pc_changes=[dict(pc=p,insn=ap[p]['insn'],kind=ap[p]['kind'],retired=ap[p]['retired'],A_head_wait=ap[p]['head_wait'],AB_head_wait=bp[p]['head_wait'],delta=bp[p]['head_wait']-ap[p]['head_wait']) for p in ap if bp[p]['head_wait']!=ap[p]['head_wait']]
        all_rows.append(dict(family=family,name=name,A_cycles=a['cycles'],AB_cycles=b['cycles'],cycle_delta=b['cycles']-a['cycles'],time_change_percent=100*(b['cycles']/a['cycles']-1),changed_exclusive_buckets={k:dict(A=pa.get(k,0),AB=pb.get(k,0),delta=v) for k,v in delta.items() if v},changed_pc_waits=sorted(pc_changes,key=lambda p:-abs(p['delta'])),overlapping_events={v:{k:p['overlapping_events'].get(k,0) for k in ['fp_ex0_blocked','heavy_completion_blocked','fp_iq_ready_downstream_blocked','fma_src2_only_entry_cycles']} for v,p in profiles.items()}))
    regressions=[r for r in all_rows if r['cycle_delta']>0]
    require({r['name'] for r in regressions}=={'pid','gemm','aha-mont64','nsichneu','qrduino'},'regression set changed')
    result=dict(passed=True,scope='read-only reconciliation of accepted fixed-100MHz A and AB profiles',analyzer_sha256=sha(Path(__file__)),source_sha256=source_hashes,profile_count=54,core_period_ps=10000,memory_period_ps=10000,interpretation=['Exclusive buckets identify observed blocked retirement positions; deltas sum to the measured cycle difference, not independently removable stalls.','Per-PC head waits have broader scope than the exclusive partition and must not be added to it.','Overlapping entry-cycle counters do not measure elapsed CPU cycles. No causal latency, scheduling fix or speedup is inferred.'],regressions=regressions,all_workloads=all_rows)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,regressions=[{k:r[k] for k in ['name','A_cycles','AB_cycles','cycle_delta','time_change_percent','changed_exclusive_buckets']} for r in regressions]),indent=2))
if __name__=='__main__':main()
