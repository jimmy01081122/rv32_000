#!/usr/bin/env python3
"""Reconcile raw observations, calibrate against archived VCD, count lifecycles."""
import argparse, collections, gzip, hashlib, json, struct
from pathlib import Path
from run_observer import ROOT, HERE, CASES, EXPERIMENTS, require, sha, save, archived
ROW=struct.Struct('<88I')
def rows(path):
    with gzip.open(path,'rb') as stream:
        while block:=stream.read(ROW.size*4096):
            require(len(block)%ROW.size==0,'partial observation row')
            yield from ROW.iter_unpack(block)
def bits(r,base,low,width):
    i=base+low//32;n=low%32
    return ((r[i]>>n)|((r[i+1]<<(32-n)) if n+width>32 else 0))&((1<<width)-1)
def packed(r,a,b):return sum(v<<(32*i) for i,v in enumerate(r[a:b]))
def marker(i):return i&0xfffff07f==0xc0002073
def flags(r):return r[0]|r[1]<<32
def flag(f,n):return f>>n&1
def validate_row(r):
    require(r[62] in [0,1] and r[62]==(r[0]&1),'registered retirement flag differs')
    require(not r[62] or (r[63],r[64])==(bits(r,6,195,32),bits(r,6,163,32)),'registered retirement identity differs')
    require(r[87]==0 and not r[1]>>12,'unknown schema bits')
def calibrate(capture):
    source=ROOT/'build/experiments/lsu-ab-v1/pid-waveform-review-v2/AB/roi-signals.json.gz'
    inv=ROOT/'docs/evidence/2026-11-13/lsu-ab-complete/copy-inventory.json'
    expected={r['member']:r['sha256'] for r in json.loads(inv.read_text())['records']}
    require(sha(source)==expected[str(source.relative_to(ROOT))],'independent VCD extraction changed')
    signal=json.load(gzip.open(source,'rt'))['rows']
    selected={0:'can_retire',1:'completed',2:'flush',3:'store_retire',4:'store_ack',5:'mem_req',6:'mem_ready',7:'mem_write',8:'mem_rsp',9:'mem_rsp_ready',11:'agu_valid',12:'agu_misaligned',13:'effective_fwd_valid',14:'load_stall_unresolved',15:'load_stall_partial',16:'sq_has_send',18:'in_flight',20:'buffer_valid',21:'buffer_ack',22:'rsp_buf_error',29:'fp_dispatch_valid',30:'fp_dispatch_ready',36:'heavy_valid',37:'heavy_ready',43:'fp_issue_ready'}
    for i,(r,x) in enumerate(zip(rows(capture/'AB/pid/on/cycles.bin.gz'),signal,strict=True)):
        validate_row(r);s=x['signals'];f=flags(r)
        values={'head':packed(r,6,14),'agu_req':packed(r,14,27),'fp_issue':packed(r,42,52),'ld_cmp':packed(r,52,57),'fp_cmp':packed(r,66,71),'heavy_req':packed(r,71,84),'mem_addr':r[2],'agu_addr':r[3],'in_flight_tag':r[4]&65535,'buffer_tag':r[4]>>16,'rob_count':r[5]&255,'state':r[5]>>8&255,'iq_mask':r[65]>>8&255,'iq_count':r[65]>>16,**{name:flag(f,n) for n,name in selected.items()}}
        require(all(value==s[name] for name,value in values.items()),f'VCD mismatch cycle {i}')
    return dict(passed=True,cycles=len(signal),fields_per_cycle=len(values),vcd_extraction_sha256=sha(source),archive_inventory_sha256=sha(inv))
def analyze(case):
    comparison=json.loads((case/'comparison.json').read_text());require(comparison['passed'],'capture did not pass')
    for mode in ['off','on']:
        for name,h in comparison['modes'][mode]['outputs_sha256'].items():require(sha(case/mode/name)==h,'capture changed')
    profile=json.loads((case/'on/profile.json').read_text());known={int(p['pc'],16):p for p in profile['pcs']}
    partition=collections.Counter();pcs=collections.defaultdict(collections.Counter);events=collections.Counter();pc_load=collections.defaultdict(collections.Counter);pairs=collections.defaultdict(collections.Counter);hist=collections.Counter()
    retire_hash=hashlib.sha256();raw_hash=hashlib.sha256();size=0
    pending={};store=None;samples=[];sample_keys=collections.Counter();read_count=0;retire_loads=0;cycles=0
    def finish_load(d,outcome,cycle):
        pc_load[d['pc']][outcome]+=1;events['external_load_'+outcome]+=1
        if d.get('bypass'):
            pair=d['pair'];pairs[pair][outcome]+=1
            if sample_keys[pair]<3:
                samples.append(dict(**d,outcome=outcome,finish_cycle=cycle));sample_keys[pair]+=1
    for cycle,r in enumerate(rows(case/'on/cycles.bin.gz')):
        raw_hash.update(ROW.pack(*r));size+=ROW.size;cycles+=1;validate_row(r)
        f=flags(r);pc=bits(r,6,195,32);insn=bits(r,6,163,32);tag=bits(r,6,227,16);count=r[5]&255;state=r[5]>>8&255;retired=r[62]
        bucket=('retired_marker' if marker(insn) else 'retired_body') if retired else 'recovery' if state else 'rob_empty' if not count else 'store_ack_wait' if flag(f,3) and not flag(f,4) else 'completed_head_other' if flag(f,1) else 'head_wait_'+known[pc]['kind']
        partition[bucket]+=1
        if not retired and count:pcs[pc]['head_wait']+=1
        if count and insn&127 in [0x23,0x27] and (store is None or store['tag']!=tag):store=dict(tag=tag,pc=pc,first_head=cycle,mark=None,request=None,bypass=None)
        if store and store['tag']==tag and flag(f,3) and store['mark'] is None:store['mark']=cycle
        accepted=flag(f,5) and flag(f,6)
        if accepted:
            require(not flag(f,2),'memory request accepted during flush')
            if flag(f,7):
                events['store_request']+=1
                require(store is not None and bits(r,27,113,16)==tag and store['tag']==tag,'store request not associated with ROB head')
                require(store['request'] is None,'duplicate store request');store['request']=cycle
                if store['bypass'] is not None:
                    d=pending.get(store['bypass'])
                    if d is not None:d['store_request_cycle']=cycle
            else:
                events['load_request']+=1;read_count+=1
                lp=bits(r,14,369,32);li=bits(r,14,337,32);lt=bits(r,14,284,16)
                require(lt not in pending,'load tag reused without retirement/flush')
                require(li&127 in [3,7] and flag(f,11),'accepted read does not match AGU load')
                first=flag(f,16) and flag(f,17) and (r[5]>>16&15)==(r[5]>>20&15) and not bits(r,27,2,1)
                bypass=bool(flag(f,16))
                if bypass:require(first or flag(f,39),'unbounded head-store bypass')
                d=dict(pc=f'{lp:08x}',insn=f'{li:08x}',tag=lt,request_cycle=cycle,rob_count=count,bypass=bypass)
                if bypass:
                    require(store is not None and store['tag']==tag,'bypass without head store')
                    pair=f'{pc:08x}/{lp:08x}';d.update(pair=pair,store_pc=f'{pc:08x}',store_tag=tag,store_ordinal=events['store_retired']+1,age_distance=((lt>>4)-(tag>>4))&4095)
                    store['bypass']=lt;pairs[pair]['accepted']+=1;events['bypass']+=1
                    hist['bypass_rob_count_'+str(count)]+=1;hist['bypass_age_distance_'+str(d['age_distance'])]+=1
                pending[lt]=d;pc_load[d['pc']]['accepted']+=1
        if bits(r,52,154,1):
            lt=bits(r,52,138,16)
            if lt in pending:pending[lt]['completion_cycle']=cycle
        if retired:
            retire_hash.update(struct.pack('<II',pc,insn))
            if not marker(insn):pcs[pc]['retired']+=1
            if insn&127 in [3,7]:
                retire_loads+=1
                if tag in pending:
                    d=pending.pop(tag);require(d['pc']==f'{pc:08x}' and d['insn']==f'{insn:08x}','load retirement identity differs');finish_load(d,'retired',cycle)
                else:events['retired_load_without_roi_external_request']+=1
            elif insn&127 in [0x23,0x27]:
                require(store is not None and store['tag']==tag and store['request'] is not None and store['mark'] is not None,'incomplete retired store')
                events['store_retired']+=1;hist['store_mark_to_retire_'+str(cycle-store['mark'])]+=1
                if store['bypass'] is not None:
                    d=pending.get(store['bypass'])
                    require(d is not None,'younger bypass load retired before store')
                    d['store_retire_cycle']=cycle;d['store_mark_cycle']=store['mark'];d['store_head_cycle']=store['first_head']
                    pairs[d['pair']]['store_mark_to_retire_sum']+=cycle-store['mark']
                store=None
            else:require(tag not in pending,'external load retired as non-load')
        if flag(f,2):
            # This core rolls back at retirement. All remaining loads are younger.
            require(retired and insn&127 in [0x63,0x67,0x6f],'unsupported trap/non-control flush in diagnostic ROI')
            events['flush']+=1
            for d in pending.values():finish_load(d,'cancelled_at_retirement_flush',cycle)
            pending.clear();store=None
    for d in pending.values():finish_load(d,'censored_at_roi_end',cycles)
    require(cycles==profile['cycles'] and dict(partition)==profile['cycle_partition'],'exclusive cycle accounting differs')
    require({pc:dict(retired=v['retired'],head_wait=v['head_wait']) for pc,v in pcs.items()}=={pc:dict(retired=p['retired'],head_wait=p['head_wait']) for pc,p in known.items()},'per-PC accounting differs')
    expected=comparison['modes']['on'];require(size==expected['raw_bytes'] and raw_hash.hexdigest()==expected['raw_sha256'],'decoded stream identity differs')
    require(read_count==sum(events['external_load_'+k] for k in ['retired','cancelled_at_retirement_flush','censored_at_roi_end']),'load lifecycle denominator differs')
    require(retire_loads==events['external_load_retired']+events['retired_load_without_roi_external_request'],'retired load denominator differs')
    overlap=profile['overlapping_events'];require(events['load_request']==overlap['dmem_read_accepted'] and events['store_request']==overlap['dmem_write_accepted'] and events['flush']==overlap['flush'],'raw event counts differ')
    return dict(passed=True,cycles=cycles,ordered_retired_pc_insn_sha256=retire_hash.hexdigest(),partition=dict(partition),events=dict(events),histograms=dict(hist),loads_by_pc=dict(pc_load),bypass_pairs=dict(pairs),samples=samples,raw_sha256=raw_hash.hexdigest(),compressed_sha256=sha(case/'on/cycles.bin.gz'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();require(not a.output.exists(),'fresh review output required');a.output.mkdir(parents=True)
    require(json.loads((a.capture/'summary.json').read_text())['passed'],'incomplete capture')
    calibration=calibrate(a.capture);save(a.output/'calibration.json',calibration)
    records={}
    for v in EXPERIMENTS:
        records[v]={}
        for family,name in CASES:
            d=analyze(a.capture/v/name);records[v][name]=d;save(a.output/f'{v}-{name}.json',d);print(v,name,'raw review PASS',d['events'],flush=True)
    for _,name in CASES:require(records['AB'][name]['ordered_retired_pc_insn_sha256']==records['ARB'][name]['ordered_retired_pc_insn_sha256'],'retired instruction sequence differs')
    raw=list(rows(a.capture/'AB/pid/on/cycles.bin.gz'));original=next(r for r in raw if r[62]);bad=list(original);bad[63]^=4
    try:validate_row(bad)
    except ValueError:negative_commit=True
    else:raise ValueError('negative control corrupted commit accepted')
    truncated=a.output/'negative-truncated.bin.gz'
    with gzip.GzipFile(filename=str(truncated),mode='wb',mtime=0) as f:f.write(ROW.pack(*raw[0])[:-1])
    try:list(rows(truncated))
    except ValueError:negative_length=True
    else:raise ValueError('negative control truncated row accepted')
    summary=dict(passed=True,scope='Read-only diagnostic; no new RTL/PPA or family aggregate',reviewer_sha256=sha(Path(__file__)),capture_summary_sha256=sha(a.capture/'summary.json'),calibration=calibration,negative_controls=dict(corrupted_registered_pc_rejected=negative_commit,truncated_row_rejected=negative_length),review_files_sha256={p.name:sha(p) for p in a.output.iterdir()})
    save(a.output/'summary.json',summary)
if __name__=='__main__':main()
