"""Archive actual B evidence without rewriting original paths or raw bytes."""
from pathlib import Path
import datetime,gzip,hashlib,json,shutil,subprocess
ROOT=Path('/workspace/rv32_000');SRC=ROOT/'build/experiments/lsu-b-v1';DST=ROOT/'docs/evidence/2026-10-21/lsu-b'
assert not DST.exists();DST.mkdir(parents=True)
rows=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def copy(p,relative,compress=False):
 assert p.is_file(),p
 q=DST/relative;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists(),q
 original=sha(p);size=p.stat().st_size
 if compress:
  with p.open('rb') as f,q.open('wb') as raw:
   with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as z:shutil.copyfileobj(f,z)
  h=hashlib.sha256()
  with gzip.open(q,'rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert h.hexdigest()==original
 else:shutil.copyfile(p,q);assert sha(q)==original
 rows.append({'source':str(p.relative_to(ROOT)),'source_sha256':original,'source_bytes':size,'source_mode':oct(p.stat().st_mode & 0o777),'archive':str(q.relative_to(DST)),'archive_sha256':sha(q),'archive_bytes':q.stat().st_size,'gzip_roundtrip_verified':compress})
# Positive build/functional/unit/measurement provenance plus exact executable bytes.
for name in ['build-clean-v1','qualification-clean-v1','unit-clean-v1','unit-dev-v1','functional-worker-v1','admission-controls',*[p.name for p in sorted(SRC.glob('measurement-*ps-worker-v*'))]]:
 parent=SRC/name
 for p in sorted(parent.rglob('*')):
  if not p.is_file():continue
  relative=Path(name)/p.relative_to(parent)
  if name.startswith('unit-') and p.parent.name in ['baseline','candidate']:
   if p.name=='lsu_unit':copy(p,relative.with_name(p.name+'.gz'),True)
   elif p.name.endswith('__verFiles.dat'):copy(p,relative)
   continue
  if name=='build-clean-v1' and p.parent.name in ['sim-normal','sim-assert']:
   if p.name=='rv32_ooo_sim':copy(p,relative.with_name(p.name+'.gz'),True)
   elif p.name.endswith('__verFiles.dat'):copy(p,relative)
   continue
  copy(p,relative)
for parent in sorted(SRC.glob('measurement-*ps-v*')):
 if parent.is_dir():
  for p in sorted(parent.rglob('*')):
   if p.is_file():copy(p,Path(parent.name)/p.relative_to(parent))
# Native stage results: metadata/log/report/timing; large checkpoints compressed.
for parent in sorted(SRC.glob('physical-*ps-*-clean-v*')):
 for p in sorted(parent.rglob('*')):
  if not p.is_file():continue
  relative=Path('physical')/parent.name/p.relative_to(parent)
  if 'results' in p.relative_to(parent).parts:
   if p.name in ['1_2_yosys.v','5_1_grt.odb','5_1_grt.sdc','5_1_grt.guide']:
    copy(p,relative.with_name(p.name+'.gz'),True)
   continue
  copy(p,relative)
for p in sorted(SRC.iterdir()):
 if p.is_file() and p.suffix in ['.json','.jsonl','.py','.log','.v','.rpt']:
  copy(p,Path('context')/(p.name+'.gz' if p.suffix=='.v' else p.name),p.suffix=='.v')
# Exact live sources used in this experiment, beyond archived identity records.
manifest=json.loads((ROOT/'experiments/lsu-b-v1/manifest.json').read_text())
names=set(manifest['candidate_rtl_files_sha256'])|set(manifest['simulation_inputs_sha256'])|set(manifest['physical_inputs_sha256'])
names|={'experiments/lsu-b-v1/manifest.json','experiments/lsu-b-v1/README.md','scripts/build_experiment_sim.py','scripts/check_lsu_marking.py','scripts/experiment_contract.py','scripts/experiment_provenance.py','scripts/measure_cpu_experiment.py','scripts/measure_post_lsu_baseline.py','scripts/qualify_cpu_experiment.py','scripts/review_cpu_experiment.py','scripts/analyze_baseline_physical.py','scripts/run_baseline_physical.py','scripts/run_physical_job.py','scripts/check_physical_closure.py','scripts/lower_baseline_rtl.py','verification/unit/lsu_marking_top.sv','verification/unit/test_lsu_marking.cpp'}
for name in sorted(names):copy(ROOT/name,Path('inputs')/name)
(DST/'copy-inventory.json').write_text(json.dumps({'scope':'lossless raw B evidence copy; paths and hashes in originals are preserved','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':rows},indent=2)+'\n')
(DST/'.gitattributes').write_text('* -text\n')
print('Copied',len(rows),'files; write final README then SHA256SUMS')
