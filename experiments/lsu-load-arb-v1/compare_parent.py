#!/usr/bin/env python3
"""Revalidate parent/candidate full measurements and reconcile all cycle deltas."""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-load-arb-v1'
sys.path.insert(0,str(ROOT/'scripts'))
from experiment_provenance import retired_work
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def reviewer(experiment):
    path=ROOT/'experiments'/experiment/'review_measurement.py'
    spec=importlib.util.spec_from_file_location(experiment.replace('-','_'),path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);out=parser.parse_args().output
    require(not out.exists(),'preserve previous comparison')
    parent_path=ROOT/'build/experiments/lsu-ab-v1/measurement-10000ps-v1';candidate_path=BASE/'measurement-10000ps-v1'
    parent=reviewer('lsu-ab-v1').review(parent_path);candidate=reviewer('lsu-load-arb-v1').review(candidate_path)
    public=ROOT/'docs/evidence/2026-11-13/lsu-ab-complete';inventory=json.loads((public/'copy-inventory.json').read_text());archived={r['member']:r['sha256'] for r in inventory['records']}
    require(sha(parent_path/'summary.json')==archived[str((parent_path/'summary.json').relative_to(ROOT))],'parent summary differs from archive')
    accepted=json.loads((public/'complete-review.json').read_text())['operating_points']['common_clock']
    require(all(parent[k]==accepted[k] for k in parent),'fresh parent review differs from final accepted reference')
    require([(r['family'],r['name']) for r in parent['records']]==[(r['family'],r['name']) for r in candidate['records']],'ordered full set differs')
    summaries={name:json.loads((path/'summary.json').read_text()) for name,path in [('parent',parent_path),('candidate',candidate_path)]};records=[];sources={}
    for a,b in zip(parent['records'],candidate['records']):
        family,name=b['family'],b['name'];profiles={}
        for label,path in [('parent',parent_path),('candidate',candidate_path)]:
            f=path/family/name/'profile.json';h=sha(f);sources[str(f.relative_to(ROOT))]=h
            source=next(r for r in summaries[label]['records'] if (r['family'],r['name'])==(family,name));require(source['profile_sha256']==h,'raw profile changed')
            if label=='parent':require(archived[str(f.relative_to(ROOT))]==h,'parent profile differs from archive')
            profiles[label]=json.loads(f.read_text())
        x,y=profiles['parent'],profiles['candidate'];require(retired_work(x)==retired_work(y),'retired per-PC work changed')
        px,py=x['cycle_partition'],y['cycle_partition'];require(sum(px.values())==x['cycles'] and sum(py.values())==y['cycles'],'exclusive partition incomplete')
        delta={k:py.get(k,0)-px.get(k,0) for k in sorted(set(px)|set(py))};require(sum(delta.values())==y['cycles']-x['cycles'],'cycle difference does not reconcile')
        records.append(dict(family=family,name=name,group=b['group'],parent_cycles=a['candidate_cycles'],candidate_cycles=b['candidate_cycles'],parent_speedup=a['candidate_cycles']/b['candidate_cycles'],baseline_speedup=b['time_speedup'],time_change_percent=100*(b['candidate_cycles']/a['candidate_cycles']-1),cycle_delta=y['cycles']-x['cycles'],changed_exclusive_buckets={k:v for k,v in delta.items() if v}))
    gm=lambda values:math.exp(sum(math.log(v) for v in values)/len(values))
    groups={g:gm([r['parent_speedup'] for r in records if r['group']==g]) for g in ['dsp','matrix_ml']}
    relative=dict(embench=gm([r['parent_speedup'] for r in records if r['family']=='embench']),fp32=math.sqrt(math.prod(groups.values())),fp32_subgroups=groups,faster=sum(r['parent_speedup']>1 for r in records),slower=sum(r['parent_speedup']<1 for r in records),equal=sum(r['parent_speedup']==1 for r in records))
    result=dict(passed=True,scope='complete fixed-100MHz cycle comparison; new candidate timing/area is not qualified here',analyzer_sha256=sha(Path(__file__)),parent_archive_inventory_sha256=sha(public/'copy-inventory.json'),parent_review=parent,candidate_review=candidate,relative_to_parent=relative,source_sha256=sources,records=records,interpretation='Exclusive bucket differences reconcile observed wait positions; they are not independently removable cycles or proof of causal latency.')
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(relative,indent=2))
if __name__=='__main__':main()
