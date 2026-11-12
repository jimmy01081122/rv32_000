#!/usr/bin/env python3
"""Extract every PID ROI cycle from actual VCD and cross-check retirement accounting."""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
CORE='TOP.rv32_ooo_core.'
FIELDS={
 **{name:(CORE+'u_lsu.'+name,1) for name in ['agu_valid','agu_misaligned','effective_fwd_valid','load_stall_unresolved','load_stall_partial','sq_has_send','can_issue_store','can_issue_load','rsp_buf_error']},
 'agu_req':(CORE+'u_lsu.agu_req',401),'agu_addr':(CORE+'u_lsu.agu_addr',32),
 'clk':('TOP.clk',1),'commit':('TOP.commit_trace',344),
 'head':(CORE+'u_rob.head_entry',245),'can_retire':(CORE+'u_rob.can_retire',1),
 'completed':(CORE+'u_rob.rob_head_completed',1),'rob_count':(CORE+'u_rob.rob_count',5),
 'state':(CORE+'u_rob.current_state',3),'flush':(CORE+'flush_valid',1),
 'store_retire':(CORE+'sq_retire_valid',1),'store_ack':(CORE+'sq_retire_ack',1),
 'fp_dispatch_valid':(CORE+'fp_disp_valid',1),'fp_dispatch_ready':(CORE+'fp_disp_ready',1),'fp_dispatch':(CORE+'fp_disp_uop',305),
 'fp_issue_valid':(CORE+'fp_issue_valid',1),'fp_issue_ready':(CORE+'fp_issue_ready',1),'fp_issue':(CORE+'fp_issue_uop',305),
 'heavy_valid':(CORE+'fp_heavy_issue_valid',1),'heavy_ready':(CORE+'fp_heavy_issue_ready',1),'heavy_req':(CORE+'fp_ex0_req_q',401),
 'fp_cmp':(CORE+'fp_cmp_q',155),'fp_cmp_ready':(CORE+'fp_cmp_ready',1),
 'ld_cmp':(CORE+'ld_cmp',155),
 'iq_mask':(CORE+'u_fp_iq.ready_mask',4),'iq_count':(CORE+'u_fp_iq.num_valid',3),
 **{f'iq{i}':(CORE+f'u_fp_iq.entries({i})',309) for i in range(4)},
 'mem_req':('TOP.dmem_req_valid',1),'mem_ready':('TOP.dmem_req_ready',1),'mem_write':('TOP.dmem_req_wen',1),'mem_addr':('TOP.dmem_req_addr',32),
 'mem_rsp':('TOP.dmem_rsp_valid',1),'mem_rsp_ready':('TOP.dmem_rsp_ready',1),
 'buffer_valid':(CORE+'u_lsu.rsp_buf_valid',1),'buffer_ack':(CORE+'u_lsu.rsp_buf_ack',1),'buffer_tag':(CORE+'u_lsu.rsp_buf_rob_tag',16),
 'in_flight':(CORE+'u_lsu.in_flight_valid',1),'in_flight_tag':(CORE+'u_lsu.in_flight_rob_tag',16)}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def marker(i):return i&0xfffff07f==0xc0002073
def uop(v):return dict(pc=f'{v>>273&0xffffffff:08x}',insn=f'{v>>241&0xffffffff:08x}',tag=v>>188&65535)
def extract(path,profile,out):
 scope=[];names={};ids={};values={};active=False;closed=False;rows=[];time=None;pending=None;markers=0;partition=collections.Counter();pcs=collections.defaultdict(lambda:dict(retired=0,head_wait=0));events=[]
 known={int(p['pc'],16):p for p in profile['pcs']}
 def frame():
  nonlocal active,closed,pending,markers
  if time is None:return
  data={name:int(values[code],2) for name,code in ids.items()}
  if data['clk']==0:
   if active:pending=dict(time=time,signals=data)
   return
  trace=data['commit'];retired=(trace>>343)&1;pc=(trace>>246)&0xffffffff;insn=(trace>>214)&0xffffffff
  if active:
   require(pending is not None,'missing low-edge snapshot');d=pending['signals'];h=d['head'];hp=(h>>195)&0xffffffff;hi=(h>>163)&0xffffffff
   require(d['can_retire']==retired and (not retired or (hp,hi)==(pc,insn)),'low-edge head disagrees with registered commit')
   kind='marker' if marker(hi) else known.get(hp,{}).get('kind','unknown')
   bucket=('retired_marker' if marker(hi) else 'retired_body') if retired else 'recovery' if d['state'] else 'rob_empty' if not d['rob_count'] else 'store_ack_wait' if d['store_retire'] and not d['store_ack'] else 'completed_head_other' if d['completed'] else 'head_wait_'+kind
   partition[bucket]+=1
   if not retired and d['rob_count']:pcs[hp]['head_wait']+=1
   if retired and not marker(insn):pcs[pc]['retired']+=1
   require(d['iq_count']==sum((d[f'iq{i}']>>308)&1 for i in range(4)),'IQ valid count differs')
   ready=sum((1<<i) for i in range(4) if d[f'iq{i}']>>308 and d[f'iq{i}']&7==7 and d['state']==0)
   require(ready==d['iq_mask'],'IQ readiness decoding differs')
   cycle=len(rows)
   for prefix in ['fp_dispatch','fp_issue']:
    if d[prefix+'_valid'] and d[prefix+'_ready'] and not d['flush']:events.append(dict(cycle=cycle,event=prefix,**uop(d[prefix])))
   if d['heavy_valid'] and d['heavy_ready'] and not d['flush']:events.append(dict(cycle=cycle,event='heavy_accept',**uop(d['heavy_req']>>96)))
   if d['fp_cmp']>>154 and d['fp_cmp_ready']:events.append(dict(cycle=cycle,event='fp_completion',tag=(d['fp_cmp']>>138)&65535))
   if retired:events.append(dict(cycle=cycle,event='retire',pc=f'{pc:08x}',insn=f'{insn:08x}',tag=(h>>227)&65535))
   if d['mem_req'] and d['mem_ready']:events.append(dict(cycle=cycle,event='store_request' if d['mem_write'] else 'load_request',address=f'{d["mem_addr"]:08x}'))
   pending.update(roi_cycle=cycle,registered_commit=trace,bucket=bucket);rows.append(pending);pending=None
  if retired and marker(insn):
   markers+=1
   if not active:active=True
   else:active=False;closed=True
 with gzip.open(path,'rt') as stream:
  for line in stream:
   w=line.split()
   if not w:continue
   if w[0]=='$scope':scope.append(w[2])
   elif w[0]=='$upscope':scope.pop()
   elif w[0]=='$var':names['.'.join(scope+[w[4]])]=(w[3],int(w[2]))
   elif w[0]=='$enddefinitions':
    for field,(name,width) in FIELDS.items():
     require(name in names and names[name][1]==width,'missing/changed waveform field '+name);ids[field]=names[name][0]
    selected=set(ids.values());break
  for line in stream:
   if line.startswith('#'):
    frame()
    if closed:break
    time=int(line[1:])
   elif line.startswith('b'):
    v,code=line[1:].split()
    if code in selected:
     require(not set(v)-{'0','1'},'undefined selected waveform value');values[code]=v
   elif line[:1] in '01xXzZ':
    code=line[1:].strip()
    if code in selected:
     require(line[0] in '01','undefined selected scalar');values[code]=line[0]
  if not closed:frame()
 require(closed and markers==2 and len(rows)==profile['cycles'],'incomplete ROI')
 require(dict(partition)==profile['cycle_partition'],'waveform partition differs from accepted profile')
 require(all(pcs[pc]==dict(retired=row['retired'],head_wait=row['head_wait']) for pc,row in known.items()) and set(pcs)==set(known),'waveform per-PC accounting differs')
 with gzip.GzipFile(filename=str(out/'roi-signals.json.gz'),mode='wb',compresslevel=6,mtime=0) as gz:
  gz.write((json.dumps(dict(scope='all selected low-edge signals and registered commit for every complete ROI cycle',fields=FIELDS,rows=rows),separators=(',',':'))+'\n').encode())
 (out/'roi-events.json').write_text(json.dumps(events,indent=2)+'\n')
 return dict(passed=True,cycles=len(rows),partition=dict(partition),event_count=len(events),vcd_sha256=sha(path),selected_roi_sha256=sha(out/'roi-signals.json.gz'),events_sha256=sha(out/'roi-events.json'))
def main():
 source=BASE/'pid-waveforms-v1';capture=json.loads((source/'summary.json').read_text());require(capture['passed'],'complete capture required');output=BASE/'pid-waveform-review-v2';output.mkdir();records=[]
 for record in capture['records']:
  variant=record['variant'];directory=source/variant;dest=output/variant;dest.mkdir()
  for name,digest in record['outputs_sha256'].items():require(sha(directory/name)==digest,'captured output changed')
  result=extract(directory/'wave.vcd.gz',json.loads((directory/'profile.json').read_text()),dest);records.append(dict(variant=variant,**result));print(variant,'full ROI waveform/profile reconciliation PASS',flush=True)
 (output/'summary.json').write_text(json.dumps(dict(passed=True,analyzer_sha256=sha(Path(__file__)),capture_summary_sha256=sha(source/'summary.json'),records=records,scope='raw selected waveform evidence; architectural scheduling interpretation requires separate review'),indent=2)+'\n')
if __name__=='__main__':main()
