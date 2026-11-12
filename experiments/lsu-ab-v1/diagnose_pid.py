#!/usr/bin/env python3
"""Reconcile the entire PID regression with observed memory ordering and loop timing."""
import collections,gzip,hashlib,json
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1';SOURCE=BASE/'pid-waveform-review-v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def matching(events,retire,event,pc=None):
 candidates=[e for e in events if e['event']==event and e.get('tag')==retire['tag'] and e['cycle']<=retire['cycle'] and (pc is None or e.get('pc')==pc)]
 require(candidates,'no matching prior '+event);return max(candidates,key=lambda e:e['cycle'])
def hist(values):return dict(sorted(collections.Counter(values).items()))
def analyze(variant):
 source=SOURCE/variant;packet=json.loads(gzip.decompress((source/'roi-signals.json.gz').read_bytes()));rows=packet['rows'];events=json.loads((source/'roi-events.json').read_text());request_events=[];competition=[]
 for r in rows:
  s=r['signals'];headpc=s['head']>>195&0xffffffff;agupc=s['agu_req']>>369&0xffffffff;aguinsn=s['agu_req']>>337&0xffffffff
  if s['mem_req'] and s['mem_ready']:
   if s['mem_write'] and headpc==0x80000204:request_events.append(dict(event='loop_store',cycle=r['roi_cycle'],tag=s['head']>>227&65535,address=s['mem_addr']))
   elif not s['mem_write'] and agupc==0x800001e8:request_events.append(dict(event='loop_load',cycle=r['roi_cycle'],tag=s['agu_req']>>284&65535,address=s['mem_addr']))
  eligible=(s['agu_valid'] and aguinsn&127==7 and not any(s[k] for k in ['agu_misaligned','effective_fwd_valid','load_stall_unresolved','load_stall_partial','in_flight','flush']) and s['state']==0 and (not s['buffer_valid'] or s['buffer_ack'] and not s['rsp_buf_error']) and s['mem_ready'])
  if eligible and s['store_retire']:
   require(s['mem_req'],'eligible competition must issue a request')
   expected=variant=='AB'
   require(bool(s['sq_has_send'])==expected and bool(s['mem_write'])==expected and bool(s['can_issue_store'])==expected and bool(s['can_issue_load'])!=expected,'unexpected memory arbitration')
   require(s['agu_addr']!=s['mem_addr'] if expected else s['agu_addr']==s['mem_addr'],'wrong selected address')
   competition.append(dict(cycle=r['roi_cycle'],sq_has_send=s['sq_has_send'],request='store' if s['mem_write'] else 'load',pending_load_address=f'{s["agu_addr"]:08x}',request_address=f'{s["mem_addr"]:08x}'))
 loop_pcs={'load':'800001e8','multiply':'800001e4','fma1':'800001f4','fma2':'800001f8','add':'80000200','store':'80000204'}
 commits={kind:[e for e in events if e['event']=='retire' and e['pc']==pc] for kind,pc in loop_pcs.items()}
 require(all(len(v)==512 for v in commits.values()),'complete 512 retired loop iterations required')
 iterations=[];heavy_latency=[];consumed_requests=set()
 for index in range(512):
  load=matching(request_events,commits['load'][index],'loop_load');store=matching(request_events,commits['store'][index],'loop_store')
  consumed_requests.update([('loop_load',load['cycle']),('loop_store',store['cycle'])])
  row=dict(iteration=index,load_cycle=load['cycle'],load_address=f'{load["address"]:08x}',store_request_cycle=store['cycle'],store_address=f'{store["address"]:08x}',store_retire_cycle=commits['store'][index]['cycle'])
  for kind in ['multiply','fma1','fma2','add']:
   retired=commits[kind][index];issued=matching(events,retired,'fp_issue',loop_pcs[kind]);accepted=matching(events,retired,'heavy_accept',loop_pcs[kind]);completed=matching(events,retired,'fp_completion')
   require(issued['cycle']<accepted['cycle']<completed['cycle']<=retired['cycle'],'arithmetic life-cycle order mismatch')
   heavy_latency.append(completed['cycle']-accepted['cycle'])
   row[kind]=dict(issue=issued['cycle'],accept=accepted['cycle'],completion=completed['cycle'],retire=retired['cycle'])
  iterations.append(row)
 require(all(int(b['load_address'],16)==int(a['load_address'],16)+4 and int(b['store_address'],16)==int(a['store_address'],16)+4 for a,b in zip(iterations,iterations[1:])),'retired loop address progression differs')
 require(hist(heavy_latency)=={1:2048},'arithmetic latency changed')
 period=14 if variant=='A' else 16
 require(all(iterations[i+1]['store_retire_cycle']-iterations[i]['store_retire_cycle']==period for i in range(1,511)),'nonuniform steady loop period')
 order=[iterations[i+1]['load_cycle']-iterations[i]['store_request_cycle'] for i in range(1,511)]
 require(hist(order)==({-2:510} if variant=='A' else {2:510}),'memory request order differs from diagnosis')
 prefix=iterations[0]['store_retire_cycle']+1;transition=iterations[1]['store_retire_cycle']-iterations[0]['store_retire_cycle'];steady=sum(iterations[i+1]['store_retire_cycle']-iterations[i]['store_retire_cycle'] for i in range(1,511));tail=len(rows)-iterations[-1]['store_retire_cycle']-1
 require(prefix+transition+steady+tail==len(rows),'complete ROI decomposition differs')
 return dict(passed=True,cycles=len(rows),source_hashes={p.name:sha(p) for p in [source/'roi-signals.json.gz',source/'roi-events.json']},
             iteration_count=512,steady_intervals=510,steady_period_cycles=period,heavy_accept_to_completion_histogram=hist(heavy_latency),
             next_load_minus_current_store_cycles=hist(order),eligible_load_and_head_store_cases=len(competition),competition_cases=competition,
             loop_requests_without_corresponding_ROI_retirement=[e for e in request_events if (e['event'],e['cycle']) not in consumed_requests],
             cycle_decomposition=dict(prefix=prefix,first_transition=transition,steady_intervals=steady,tail=tail),iterations=iterations)
def main():
 summary=json.loads((SOURCE/'summary.json').read_text());require(summary['passed'],'waveform extraction incomplete')
 for r in summary['records']:
  require(sha(SOURCE/r['variant']/'roi-signals.json.gz')==r['selected_roi_sha256'] and sha(SOURCE/r['variant']/'roi-events.json')==r['events_sha256'],'selected signal evidence changed')
 result={v:analyze(v) for v in ['A','AB']}
 delta={k:result['AB']['cycle_decomposition'][k]-result['A']['cycle_decomposition'][k] for k in result['A']['cycle_decomposition']}
 require(sum(delta.values())==result['AB']['cycles']-result['A']['cycles']==1014,'whole regression does not reconcile')
 a=json.loads((ROOT/'experiments/lsu-a-v1/manifest.json').read_text());ab=json.loads((ROOT/'experiments/lsu-ab-v1/manifest.json').read_text())
 differences=[p for p,h in a['candidate_rtl_files_sha256'].items() if ab['candidate_rtl_files_sha256'].get(p)!=h]
 require(differences==['rtl/lsu/rv32_ooo_lsu.sv'],'A/AB comparison changed another RTL unit')
 output=BASE/'pid-mechanism-review.json';require(not output.exists(),'fresh diagnosis required')
 output.write_text(json.dumps(dict(passed=True,scope='observed mechanism in fixed PID workload; no arbitration RTL change or future speedup forecast',analyzer_sha256=sha(Path(__file__)),waveform_review_sha256=sha(SOURCE/'summary.json'),variants=result,cycle_delta=1014,cycle_delta_decomposition=delta,rtl_difference= differences,conclusion='Earlier head-store eligibility makes store priority win over an otherwise eligible nonaliasing next-iteration load on the single external port. The resulting steady loop is 16 instead of 14 cycles; 510 repeated intervals add 1020 cycles, offset by 6 cycles at the boundaries. All 2048 retired loop arithmetic operations per variant still complete one cycle after heavy-unit acceptance.',limitations=['Operand/arbitration changes have not been implemented; no improvement is forecast.','Wrong-path and boundary requests are listed separately and excluded from the retired-iteration comparison.','The published selected signals cover every ROI cycle. Full-program VCD captures are local optional artifacts, reproducible with the capture script.']),indent=2)+'\n')
 print(json.dumps(dict(passed=True,cycle_delta=1014,decomposition=delta,variants={v:{k:d[k] for k in ['cycles','steady_period_cycles','heavy_accept_to_completion_histogram','next_load_minus_current_store_cycles','eligible_load_and_head_store_cases']} for v,d in result.items()}),indent=2))
if __name__=='__main__':main()
