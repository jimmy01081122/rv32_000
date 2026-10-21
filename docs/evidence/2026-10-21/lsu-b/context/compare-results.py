import hashlib,json,math,sys
from pathlib import Path
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1'
sys.path.insert(0,str(ROOT/'scripts'))
from experiment_provenance import retired_work
baseline=json.loads((ROOT/'baselines/ap5b-post-lsu-v1/manifest.json').read_text())
ref=ROOT/baseline['measurement']['formal_evidence'];candidate=OUT/'measurement-10000ps-v1';a=ROOT/'build/experiments/lsu-a-v1/measurement-10000ps-v1'
summary=json.loads((candidate/'summary.json').read_text());assert summary['passed'] and len(summary['records'])==27
rows=[]
for item in baseline['workloads']:
 path=Path(item['family'])/item['name']/'profile.json'
 ps=[ref/path,a/path,candidate/path];old,pa,new=[json.loads(p.read_text()) for p in ps]
 assert retired_work(old)==retired_work(new) and old['retired_classes']==new['retired_classes']
 rows.append({'family':item['family'],'name':item['name'],'group':item.get('group'),
 'cycles':{'baseline':old['cycles'],'A':pa['cycles'],'B':new['cycles']},
 'B_common_clock_speedup':old['cycles']/new['cycles'],
 'cycle_partitions':{'baseline':old['cycle_partition'],'A':pa['cycle_partition'],'B':new['cycle_partition']},
 'store_wait_phases':{'baseline':old['store_ack_wait_phases'],'A':pa['store_ack_wait_phases'],'B':new['store_ack_wait_phases']},
 'load_wait_phases':{'baseline':old['load_head_wait_phases'],'A':pa['load_head_wait_phases'],'B':new['load_head_wait_phases']},
 'overlapping_events':{'baseline':old['overlapping_events'],'A':pa['overlapping_events'],'B':new['overlapping_events']},
 'per_pc_work_matches':True,'profile_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ps}})
def gm(x):return math.exp(sum(math.log(v) for v in x)/len(x))
groups={g:gm([r['B_common_clock_speedup'] for r in rows if r['group']==g]) for g in ['dsp','matrix_ml']}
r={'scope':'complete same-clock diagnostics pending matching physical qualification; overlapping events are not additive saved cycles',
 'measurement_summary_sha256':hashlib.sha256((candidate/'summary.json').read_bytes()).hexdigest(),
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'B_embench_common_clock_geomean':gm([r['B_common_clock_speedup'] for r in rows if r['family']=='embench']),
 'B_fp32_common_clock_geomean':math.sqrt(groups['dsp']*groups['matrix_ml']),
 'B_fp32_groups':groups,'records':rows,'per_pc_work_matches':True}
(OUT/'common-clock-diagnostics.json').write_text(json.dumps(r,indent=2)+'\n')
print('B common-clock diagnostics',r['B_embench_common_clock_geomean'],r['B_fp32_common_clock_geomean'],groups)
for row in rows:print(row['family'],row['name'],row['cycles'],row['B_common_clock_speedup'])
