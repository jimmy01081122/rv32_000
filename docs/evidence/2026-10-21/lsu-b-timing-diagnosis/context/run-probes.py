"""Read-only replay of three original implementations and their mapped caches."""
from pathlib import Path
import datetime, gzip, hashlib, json, os, shutil, subprocess
root=Path('/workspace/rv32_000'); out=root/'build/experiments/lsu-b-diagnosis-v1'
container='rv32-lsu-b-diagnosis-v1'
docker=['docker','--host=unix:///var/run/docker.sock']
for key in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'): os.environ.pop(key,None)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def guest(p):return '/workspace/'+str(p.relative_to(root))
def read(p):return json.loads(p.read_text())
def restore(source,dest,expected=None):
 assert not dest.exists(),dest
 with gzip.open(source,'rb') as src,dest.open('xb') as target:shutil.copyfileobj(src,target)
 digest=sha(dest)
 if expected is not None:assert digest==expected,(source,digest,expected)
 return dict(source=str(source.relative_to(root)),source_sha256=sha(source),restored=str(dest.relative_to(root)),raw_sha256=digest,bytes=dest.stat().st_size,expected_original_sha256=expected)
assert not (out/'native-probes.json').exists()
replays=out/'replays';replays.mkdir()
restores=[];inputs={}
paths={
 'baseline':root/'build/baselines/ap5b-post-lsu-v1',
 'A':root/'build/experiments/lsu-a-v1',
 'B':root/'build/experiments/lsu-b-v1',
}
baseline_run=root/'docs/evidence/2026-10-18/post-lsu-baseline/physical/boundary-9900-10000ps/run.json'
baseline_odb=replays/'baseline-routed.odb'
restores.append(restore(root/'docs/evidence/2026-10-18/post-lsu-baseline/physical/5_1_grt.odb.gz',baseline_odb,read(baseline_run)['odb_sha256']))
for name in ('baseline','A','B'):
 base=paths[name]
 if name=='baseline':
  final=baseline_odb; final_meta=baseline_run
  synth=base/'physical-5500ps-abc-mapping-probe'
  original_final_run=base/'physical-14000ps-tt-abc-full-route-v6/run.json'
 else:
  final=base/'physical-14000ps-eco-clean-v1/results/asap7/rv32_post_lsu_v1/base/5_1_grt.odb'
  final_meta=base/'physical-14000ps-eco-clean-v1'/('boundary-v1' if name=='A' else 'diagnostic-boundary-v1')/'run.json'
  synth=base/'physical-5500ps-synth-clean-v1'
  original_final_run=base/'physical-14000ps-eco-clean-v1/run.json'
 assert sha(final)==read(final_meta)['odb_sha256']
 netlist=synth/'results/asap7/rv32_post_lsu_v1/base/1_2_yosys.v'
 # The exact mapping used in the original completed implementation.
 assert sha(netlist)==read(original_final_run)['cached_synthesis']['netlist_sha256']
 synth_odb=replays/f'{name}-synthesis.odb'
 restores.append(restore(synth/'results/asap7/rv32_post_lsu_v1/base/1_synth.odb.gz',synth_odb))
 inputs[name]=dict(routed=final,synthesis=synth_odb,netlist=netlist,final_metadata=final_meta,implementation=original_final_run)
(out/'replay-inputs.json').write_text(json.dumps(dict(restorations=restores,implementations={n:{k:dict(path=str(p.relative_to(root)),sha256=sha(p)) for k,p in v.items()} for n,v in inputs.items()},note='Synth ODBs are recovered completed caches; their exported connectivity is checked against the original recorded mapped netlist. Routed ODB hashes bind to the independently archived trial metadata.'),indent=2)+'\n')
platform=root/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
validate=docker+['exec',container,'sha256sum','--strict','--quiet','-c',guest(platform)]
subprocess.run(validate,check=True)
inspect=json.loads(subprocess.check_output(docker+['inspect',container],text=True))[0]
image='sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33'
assert inspect['State']['Running'] and inspect['Image']==image
assert {m['Destination']:m['Source'] for m in inspect['Mounts']}['/workspace']==str(root)
guard_paths=[out/'probe.tcl',root/'physical/asap7/baseline/timing_common.tcl',platform]
guard_paths += list((root/'rtl').rglob('*.sv'))+list((root/'physical/asap7/baseline').glob('*'))
guard_paths += [p for d in inputs.values() for p in d.values()]
guards={str(p.relative_to(root)):sha(p) for p in guard_paths if p.is_file()}
state=dict(scope='Read-only diagnostics; no acceptance policy, architecture, mapping or route changes',started_utc=now(),image_id=image,container_id=inspect['Id'],source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),input_sha256=guards,critical_hashes_before_returncode=0,jobs=[],complete=False)
def save():(out/'native-probes.json').write_text(json.dumps(state,indent=2)+'\n')
save()
jobs=[(n,'routed',c) for n in ('B','baseline','A') for c in ('SS','TT','FF')]+[(n,'synthesis','SS') for n in ('baseline','A','B')]
try:
 for name,view,corner in jobs:
  dest=out/'native'/name/view/corner
  dest.mkdir(parents=True,exist_ok=False)
  command=docker+['exec','--user','1000:1000','-w','/workspace','-e','RV32_CORNER='+corner,'-e','RV32_ODB='+guest(inputs[name][view]),'-e','RV32_VIEW='+view,'-e','RV32_OUT='+guest(dest),container,'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','-threads','2',guest(out/'probe.tcl')]
  row=dict(candidate=name,view=view,corner=corner,started_utc=now(),command=command,status='running');state['jobs'].append(row);save()
  print('START',name,view,corner,flush=True)
  with (dest/'sta.log').open('x') as log:rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
  row.update(returncode=rc,finished_utc=now(),outputs_sha256={p.name:sha(p) for p in sorted(dest.iterdir()) if p.is_file()})
  assert rc==0 and 'RV32_READ_ONLY_DIAGNOSTIC_COMPLETE' in (dest/'sta.log').read_text(),dest
  row.update(status='complete',metrics=read(dest/'metrics.json'));save()
  print('DONE',name,view,corner,row['metrics'],flush=True)
 assert all(sha(root/p)==h for p,h in guards.items())
 subprocess.run(validate,check=True)
 state.update(complete=True,finished_utc=now(),input_identities_unchanged=True,critical_hashes_after_returncode=0)
except BaseException as e:
 state.update(error=repr(e),failed_utc=now());save();raise
save()
