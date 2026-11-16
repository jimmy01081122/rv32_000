#!/usr/bin/env python3
"""Align retired stores by program order; report cost and observational guards."""
import argparse, collections, json
from pathlib import Path
from review_observer import rows,bits,flags,flag
from run_observer import CASES,require,sha,save
def stores(path):
    current=None;ordinal=0
    for cycle,r in enumerate(rows(path)):
        f=flags(r);pc=bits(r,6,195,32);tag=bits(r,6,227,16);insn=bits(r,6,163,32)
        if r[5]&255 and insn&127 in [0x23,0x27] and (current is None or current['tag']!=tag):
            current=dict(pc=f'{pc:08x}',tag=tag,first_head=cycle,mark=None,request=None,retire=None,bypass=False)
        if current and current['tag']==tag:
            if flag(f,3) and current['mark'] is None:current['mark']=cycle
            if flag(f,5) and flag(f,6):
                if flag(f,7):current['request']=cycle
                elif flag(f,16):current.update(bypass=True,load_pc=f'{bits(r,14,369,32):08x}',load_request=cycle,rob_count=r[5]&255,age_distance=((bits(r,14,284,16)>>4)-(tag>>4))&4095)
        if r[62] and insn&127 in [0x23,0x27]:
            ordinal+=1;require(current is not None and current['tag']==tag,'store association failed')
            current.update(retire=cycle,ordinal=ordinal);yield current;current=None
        if flag(f,2):current=None
def coverage(path):
    pending={};result={k:collections.Counter() for k in ['all','rob_free_at_least_2','age_at_most_4']}
    def finish(d,outcome):
        for key,accept in d.items():
            if accept:result[key][outcome]+=1
    for r in rows(path):
        f=flags(r)
        if flag(f,5) and flag(f,6) and not flag(f,7) and flag(f,16):
            lt=bits(r,14,284,16);ht=bits(r,6,227,16)
            d=dict(all=True,rob_free_at_least_2=(r[5]&255)<=14,age_at_most_4=(((lt>>4)-(ht>>4))&4095)<=4)
            require(lt not in pending,'duplicate bypass load');pending[lt]=d;finish(d,'accepted')
        if r[62]:
            tag=bits(r,6,227,16)
            if tag in pending:finish(pending.pop(tag),'retired')
        if flag(f,2):
            for d in pending.values():finish(d,'cancelled')
            pending.clear()
    for d in pending.values():finish(d,'censored')
    for c in result.values():require(c['accepted']==c['retired']+c['cancelled']+c['censored'],'guard coverage denominator differs')
    return result
def window(path,start,end):
    selected=[]
    for cycle,r in enumerate(rows(path)):
        if cycle<start:continue
        if cycle>end:break
        f=flags(r);pc=bits(r,6,195,32);insn=bits(r,6,163,32)
        row=dict(cycle=cycle,head_pc=f'{pc:08x}',head_insn=f'{insn:08x}',rob_count=r[5]&255,rename_blocked=bool(flag(f,23) and not flag(f,24)),retired=bool(r[62]),flush=bool(flag(f,2)))
        if flag(f,5) and flag(f,6):row['memory_request']=dict(kind='store' if flag(f,7) else 'load',pc=f'{pc if flag(f,7) else bits(r,14,369,32):08x}',address=f'{r[2]:08x}')
        if bits(r,52,154,1):row['load_completion_tag']=bits(r,52,138,16)
        for key,base,ready in [('int_issue',32,bool(r[65]&255) and flag(f,31)),('fp_issue',42,bool(r[65]>>8&255) and flag(f,43))]:
            if ready and not flag(f,2):row[key]=dict(pc=f'{bits(r,base,273,32):08x}',insn=f'{bits(r,base,241,32):08x}',tag=bits(r,base,188,16))
        selected.append(row)
    return selected
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',type=Path,required=True);ap.add_argument('--review',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();require(not a.output.exists(),'fresh result required')
    manifest=json.loads((a.review/'summary.json').read_text());require(manifest['passed'],'raw review required')
    for p,h in manifest['review_files_sha256'].items():require(sha(a.review/p)==h,'raw review changed')
    reports={};targets={'pid':'80000204/800001e8','fft':'80001274/800012ac','statemate':'80001dc4/80001914'}
    for _,name in CASES:
        ar=json.loads((a.review/f'ARB-{name}.json').read_text());ab=json.loads((a.review/f'AB-{name}.json').read_text())
        require(ar['ordered_retired_pc_insn_sha256']==ab['ordered_retired_pc_insn_sha256'],'instruction sequence changed')
        sources={v:a.capture/v/name/'on/cycles.bin.gz' for v in ['AB','ARB']}
        for v,p in sources.items():require(sha(p)==(ab if v=='AB' else ar)['compressed_sha256'],'raw source changed')
        sample=next(d for d in ar['samples'] if d['pair']==targets[name]);chosen=sample['store_ordinal']
        cohort=collections.defaultdict(collections.Counter);sums=collections.Counter();counts=0;selected=None
        for old,new in zip(stores(sources['AB']),stores(sources['ARB']),strict=True):
            require((old['ordinal'],old['pc'])==(new['ordinal'],new['pc']),'retired store order differs');counts+=1
            x=old['retire']-old['mark'];y=new['retire']-new['mark'];sums['AB']+=x;sums['ARB']+=y
            key='bypassed' if new['bypass'] else 'other';cohort[key]['stores']+=1;cohort[key]['ack_wait_delta']+=y-x;cohort[key][f'{x}_to_{y}_cycles']+=1
            if new['ordinal']==chosen:selected=dict(AB=old,ARB=new,load_lifecycle=sample)
        for v,d in [('AB',ab),('ARB',ar)]:require(sums[v]==d['partition']['store_ack_wait'],'store durations do not reconcile exclusive ack waits')
        require(counts==ar['events']['store_retired'] and cohort['bypassed']['stores']==ar['events']['bypass'],'paired store set differs')
        require(selected is not None,'missing representative store')
        for v,p in sources.items():selected[v]['window']=window(p,max(0,selected[v]['mark']-4),selected[v]['retire']+16)
        guards=coverage(sources['ARB']);require(guards['all']['accepted']==ar['events']['bypass'],'guard coverage set differs')
        reports[name]=dict(paired_stores=counts,ack_wait_totals=dict(sums),cohorts=dict(cohort),guard_coverage=guards,representative_store=selected,cycles_delta=ar['cycles']-ab['cycles'],extra_cancelled_external_reads=ar['events']['external_load_cancelled_at_retirement_flush']-ab['events']['external_load_cancelled_at_retirement_flush'])
        print(name,dict(cohort),dict(guards),flush=True)
    save(a.output,dict(passed=True,scope='Observed scheduling costs and eligibility coverage, not counterfactual speedup predictions',analyzer_sha256=sha(Path(__file__)),review_summary_sha256=sha(a.review/'summary.json'),records=reports))
if __name__=='__main__':main()
