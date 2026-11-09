#!/usr/bin/env python3
"""Compare the measured AB cycles to independently qualified A/B references."""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/optimization-135-v1'))
import analyze_bottlenecks as references
from review_measurement import review
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh comparison required')
    refs=references.analyze();candidate=review(ROOT/'build/experiments/lsu-ab-v1/measurement-10000ps-v1')
    lookup={(r['variant'],r['family'],r['name']):r for r in refs['records']}
    rows=[]
    for r in candidate['records']:
        parents={v:lookup[v,r['family'],r['name']]['cycles'] for v in ['A','B']}
        rows.append(dict(**r,parent_cycles=parents,AB_vs_A=parents['A']/r['candidate_cycles'],AB_vs_B=parents['B']/r['candidate_cycles']))
    summary={}
    for parent in ['A','B']:
        field='AB_vs_'+parent
        summary[parent]=dict(embench_geomean=references.geomean([r[field] for r in rows if r['family']=='embench']),
             fp32_geomean=references.geomean([r[field] for r in rows if r['family']=='fp32']),
             AB_faster=sum(r[field]>1 for r in rows),AB_slower=sum(r[field]<1 for r in rows),equal=sum(r[field]==1 for r in rows))
    result=dict(passed=True,scope='100 MHz functional/cycle comparison; AB physical qualification still pending',
        reference_analysis_sources_sha256=refs['sources_sha256'],candidate=candidate,relative_to_parents=summary,records=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
