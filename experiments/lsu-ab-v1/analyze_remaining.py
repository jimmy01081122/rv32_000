#!/usr/bin/env python3
"""Locate remaining AB waits in reviewed profiles; no causal speedup forecast."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
sys.path.insert(0,str(ROOT/'experiments/lsu-ab-v1'))
from review_measurement import review
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('preserve earlier analysis')
    measurement=BASE/'measurement-10000ps-v1';verified=review(measurement);records=[];sources={}
    for row in verified['records']:
        path=measurement/row['family']/row['name']/'profile.json';d=json.loads(path.read_text());sources[str(path.relative_to(ROOT))]=sha(path)
        p=d['cycle_partition'];load=d['load_head_wait_phases'];store=d['store_ack_wait_phases'];integer={'div_rem':0,'multiply':0,'other':0};instructions=p['retired_body']+p.get('retired_marker',0)
        for pc in d['pcs']:
            if pc['kind']!='integer_other':continue
            insn=int(pc['insn'],16)
            kind=('div_rem' if (insn>>12)&7>=4 else 'multiply') if insn&127==0x33 and insn>>25==1 else 'other'
            integer[kind]+=pc['head_wait']
        if sum(p.values())!=d['cycles'] or sum(integer.values())!=p.get('head_wait_integer_other',0) or sum(load.values())!=p.get('head_wait_fp_load',0)+p.get('head_wait_int_load',0) or sum(store.values())!=p.get('store_ack_wait',0):raise ValueError('counter reconciliation failed')
        records.append(dict(family=row['family'],name=row['name'],group=row['group'],cycles=d['cycles'],retirement_ipc=instructions/d['cycles'],cycle_partition=p,load_head_wait_phases=load,store_ack_wait_phases=store,integer_waits=integer,own_response_buffer_percent=100*load.get('own_response_buffer',0)/d['cycles'],div_rem_wait_percent=100*integer['div_rem']/d['cycles'],overlapping_events=d['overlapping_events']))
    output=dict(passed=True,scope='remaining wait positions from complete AB common-clock measurement',analyzer_sha256=sha(Path(__file__)),measurement_summary_sha256=verified['measurement_summary_sha256'],sources_sha256=sources,profiles=27,records=records,interpretation=['Exclusive retirement wait position is not execution-unit latency or removable cycles.','Own response-buffer waits must be measured for the selected parent and can overlap effects of another architecture change.','Overlapping counters are not a cycle partition; integer-divider operand diagnosis was collected on B and is not relabelled as AB.'])
    a.output.write_text(json.dumps(output,indent=2)+'\n');print('All 27 AB wait profiles reconciled')
if __name__=='__main__':main()
