#!/usr/bin/env python3
"""Recheck all 27 workloads against both A+B and unrestricted first-bypass v1."""
import argparse,importlib.util,json,math,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from experiment_provenance import retired_work
def require(ok,msg):
    if not ok:raise ValueError(msg)
def review(experiment):
    p=ROOT/'experiments'/experiment/'review_measurement.py';spec=importlib.util.spec_from_file_location(experiment.replace('-','_'),p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    base=ROOT/'build/experiments'/experiment/'measurement-10000ps-v1';return base,m.review(base)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);out=ap.parse_args().output;require(not out.exists(),'fresh comparison required')
    data={k:review(v) for k,v in {'AB':'lsu-ab-v1','arb_v1':'lsu-load-arb-v1','candidate':'lsu-rob-room-v1'}.items()}
    inv=ROOT/'docs/evidence/2026-11-16/lsu-arbitration-functional/inventory.json';archive={r['path']:r['sha256'] for r in json.loads(inv.read_text())['records']}
    for v in ['AB','arb_v1']:
        base,_=data[v];require(sha(base/'summary.json')==archive[str((base/'summary.json').relative_to(ROOT))],'parent reference changed')
    records=[];sources={}
    for i,row in enumerate(data['candidate'][1]['records']):
        family,name=row['family'],row['name'];profiles={};cycles={}
        for v,(base,report) in data.items():
            expected=report['records'][i];require((expected['family'],expected['name'])==(family,name),'full ordered workload set differs')
            p=base/family/name/'profile.json';h=sha(p);sources[str(p.relative_to(ROOT))]=h
            if v!='candidate':require(archive[str(p.relative_to(ROOT))]==h,'archived parent profile changed')
            profile=json.loads(p.read_text());profiles[v]=profile;cycles[v]=profile['cycles']
            require(sum(profile['cycle_partition'].values())==profile['cycles'],'exclusive partition incomplete')
        require(retired_work(profiles['candidate'])==retired_work(profiles['AB'])==retired_work(profiles['arb_v1']),'retired work changed')
        delta={}
        for v in ['AB','arb_v1']:
            x,y=profiles[v]['cycle_partition'],profiles['candidate']['cycle_partition'];d={k:y.get(k,0)-x.get(k,0) for k in sorted(set(x)|set(y))};require(sum(d.values())==cycles['candidate']-cycles[v],'cycle delta does not reconcile');delta[v]={k:n for k,n in d.items() if n}
        records.append(dict(family=family,name=name,group=row['group'],cycles=cycles,baseline_speedup=row['time_speedup'],relative_speedup={v:cycles[v]/cycles['candidate'] for v in ['AB','arb_v1']},time_change_percent={v:100*(cycles['candidate']/cycles[v]-1) for v in ['AB','arb_v1']},changed_exclusive_buckets=delta))
    gm=lambda xs:math.exp(sum(math.log(x) for x in xs)/len(xs));relative={}
    for v in ['AB','arb_v1']:
        groups={g:gm([r['relative_speedup'][v] for r in records if r['group']==g]) for g in ['dsp','matrix_ml']}
        relative[v]=dict(embench=gm([r['relative_speedup'][v] for r in records if r['family']=='embench']),fp32=math.sqrt(math.prod(groups.values())),fp32_subgroups=groups,faster=sum(r['relative_speedup'][v]>1 for r in records),slower=sum(r['relative_speedup'][v]<1 for r in records),equal=sum(r['relative_speedup'][v]==1 for r in records))
    result=dict(passed=True,scope='All27 common-clock functional/cycle comparison; candidate PPA unmeasured',analyzer_sha256=sha(Path(__file__)),parent_inventory_sha256=sha(inv),reviews={v:d[1] for v,d in data.items()},relative_to=relative,source_sha256=sources,records=records)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(relative,indent=2))
if __name__=='__main__':main()
