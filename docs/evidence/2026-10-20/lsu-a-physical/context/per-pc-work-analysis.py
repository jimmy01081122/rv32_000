import json,hashlib
from pathlib import Path
root=Path('/workspace/rv32_000');exp=root/'build/experiments/lsu-a-v1';measurement=exp/'measurement-10000ps-v1';base=root/'docs/evidence/2026-10-18/post-lsu-baseline/measurement'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def work(profile):
 rows=[p for p in profile['pcs'] if p['retired']]
 counts={(p['pc'],p['insn'],p['kind']):p['retired'] for p in rows}
 assert len(rows)==len(counts),'duplicate PC/instruction/kind entries'
 return counts
records=[]
for r in json.loads((measurement/'summary.json').read_text())['records']:
 old=base/r['family']/r['name']/'profile.json';new=measurement/r['family']/r['name']/'profile.json';a=json.loads(old.read_text());b=json.loads(new.read_text())
 records.append({'family':r['family'],'name':r['name'],'nonzero_retired_pc_count':len(work(b)),'per_pc_retired_work_matches':work(a)==work(b),'baseline_profile_sha256':sha(old),'candidate_profile_sha256':sha(new)})
result={'scope':'offline analysis of already completed common-clock raw profiles; PC/insn/kind retirement counts, not an ordered trace or full-ISA proof','script_sha256':sha(Path(__file__)),'measurement_summary_sha256':sha(measurement/'summary.json'),'records':records,'all_27_match':len(records)==27 and all(x['per_pc_retired_work_matches'] for x in records)}
(exp/'per-pc-work-identity.json').write_text(json.dumps(result,indent=2)+'\n');print('All 27 per-PC retired-work maps match:',result['all_27_match'])
