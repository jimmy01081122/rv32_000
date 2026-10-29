"""Actual evidence-corruption controls for the FPU admission reviewer."""
from pathlib import Path
import importlib.util,json,hashlib
root=Path.cwd();script=root/'experiments/lsu-b-validation-v2/review.py';spec=importlib.util.spec_from_file_location('review',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);original=m.BASE;out=original/'formal-admission-controls-v1';out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
positive=m.review_formal();assert positive['passed'];(out/'positive.json').write_text(json.dumps(positive,indent=2)+'\n')
for label in ['failed-formal-status','changed-RTL-input','forged-proof-success']:
 base=out/label;base.mkdir();directory=base/'fpu-state-relation-v1';directory.mkdir();source=original/'fpu-state-relation-v1';data=json.loads((source/'proof-summary.json').read_text())
 for p in source.iterdir():
  if p.name=='proof-summary.json':continue
  (directory/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
 if label=='failed-formal-status':data['passed']=False
 elif label=='changed-RTL-input':
  key=next(n for n in data['inputs'] if n.endswith('/fp-source.v'));data['inputs'][key]='0'*64
 else:
  log=directory/'step-output-proof.log';log.unlink();log.write_text('Networks are NOT EQUIVALENT\n');next(r for r in data['stages'] if r['stage']=='step-output-proof')['log_sha256']=sha(log)
 (directory/'proof-summary.json').write_text(json.dumps(data,indent=2)+'\n');m.BASE=base
 try:m.review_formal()
 except ValueError as e:records.append(dict(control=label,rejected=True,reason=str(e)))
 else:raise AssertionError('accepted '+label)
 finally:m.BASE=original
report=dict(passed=len(records)==3 and all(r['rejected'] for r in records),reviewer_sha256=sha(script),positive=positive,records=records);(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
