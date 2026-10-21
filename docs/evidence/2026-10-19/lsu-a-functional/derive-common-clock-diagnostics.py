import json,math,hashlib
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-a-v1';measurement=out/'measurement-10000ps-v1';base=root/'docs/evidence/2026-10-18/post-lsu-baseline/measurement'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((measurement/'summary.json').read_text());b=json.loads((root/'baselines/ap5b-post-lsu-v1/manifest.json').read_text())
assert m['passed'] and len(m['records'])==27 and m['core_period_ps']==10000 and m['memory_ps']==10000
rows=[]
for r,w in zip(m['records'],b['workloads']):
 assert r['passed'] and (r['family'],r['name'])==(w['family'],w['name'])
 a=measurement/r['family']/r['name']/'profile.json';p=base/r['family']/r['name']/'profile.json';old=json.loads(p.read_text());new=json.loads(a.read_text());assert old['retired_classes']==new['retired_classes']
 row={k:w.get(k) for k in ['family','name','group']};row.update(baseline_cycles=w['reference_cycles'],candidate_cycles=r['cycles'],cycle_speedup=w['reference_cycles']/r['cycles'],baseline_profile_sha256=sha(p),candidate_profile_sha256=sha(a),cycle_partition={k:{'baseline':old['cycle_partition'].get(k,0),'candidate':new['cycle_partition'].get(k,0),'delta':new['cycle_partition'].get(k,0)-old['cycle_partition'].get(k,0)} for k in sorted(set(old['cycle_partition'])|set(new['cycle_partition']))},store_ack_wait_phases={'baseline':old['store_ack_wait_phases'],'candidate':new['store_ack_wait_phases']},load_head_wait_phases={'baseline':old['load_head_wait_phases'],'candidate':new['load_head_wait_phases']});rows.append(row)
gm=lambda values:math.exp(sum(map(math.log,values))/len(values))
report={'scope':'complete common-100MHz cycle/mechanism diagnosis; physical qualification pending; not an operating-point decision','measurement_summary_sha256':sha(measurement/'summary.json'),'baseline_manifest_sha256':sha(root/'baselines/ap5b-post-lsu-v1/manifest.json'),'script_sha256':sha(Path(__file__)),'core_period_ps':10000,'memory_ps':10000,'embench_cycle_geomean_speedup':gm([x['cycle_speedup'] for x in rows if x['family']=='embench']),'fp32_cycle_geomean_speedup':gm([x['cycle_speedup'] for x in rows if x['family']=='fp32']),'fp32_subgroup':{g:gm([x['cycle_speedup'] for x in rows if x['group']==g]) for g in ['dsp','matrix_ml']},'records':rows}
(out/'common-clock-diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
