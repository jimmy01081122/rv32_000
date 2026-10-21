from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1'
base='58a4159da0372b3286758be1e6c1b50f9f28cc27';candidate='95ac0dd6451a1799f9f3fe948c7b74c02f5fccd2';a='bf6702c6f4238aaf5f290356f3d0e0279f688f1e'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(commit,name):return subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)
parents=subprocess.check_output(['git','show','-s','--format=%P',candidate],cwd=ROOT,text=True).strip().split();assert parents==[base]
contract=json.loads((ROOT/'experiments/lsu-b-v1/manifest.json').read_text());rows=[];changed=[]
for group in ['candidate_rtl_files_sha256','simulation_inputs_sha256','physical_inputs_sha256']:
 for name,digest in contract[group].items():
  original=sha(blob(base,name));current=sha(blob(candidate,name));assert current==digest==sha((ROOT/name).read_bytes())
  if current!=original:
   assert group=='candidate_rtl_files_sha256';changed.append(name)
  rows.append({'group':group,'path':name,'baseline_sha256':original,'B_sha256':current,'A_sha256':sha(blob(a,name))})
assert changed==['rtl/lsu/rv32_ooo_lsu.sv']
assert len(set(next(r for r in rows if r['path']==changed[0])[key] for key in ['baseline_sha256','B_sha256','A_sha256']))==3
(OUT/'source-lineage.json').write_text(json.dumps({'scope':'B single-parent baseline ancestry and complete RTL/sim/physical file identity; A logic exclusion also checked dynamically in LSU tests','baseline_commit':base,'candidate_source_commit':candidate,'candidate_parents':parents,'shared_tooling_reference':a,'changed_RTL_from_baseline':changed,'records':rows,'script_sha256':sha(Path(__file__).read_bytes()),'passed':True},indent=2)+'\n')
print('source lineage PASS: B parent58; onlyLSU changed; all',len(rows),'RTL/sim/physical inputs bound to actual95ac Git blobs and live files')
