import json,subprocess,datetime,shutil,hashlib
from pathlib import Path
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-a-v1';record={}
def call(args):
 p=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(p.stdout,flush=True)
 if p.returncode:raise RuntimeError((args,p.returncode))
 return p.stdout

def inspect(name):
 j=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
 return {k:j[k] for k in ['Id','Image','State','Mounts']}|{'User':j['Config']['User']}
def save():
 (OUT/'runtime-transition.json').write_text(json.dumps(record,indent=2)+'\n')
# Read-only checks happen before any runtime change.
r=json.loads((OUT/'verification-run.json').read_text());assert r['job_state']=='finished' and r['returncode']==0 and r['flow_completed'] and r['input_identities_unchanged']
for path in ['build-clean-v1/summary.json','qualification-clean-v1/summary.json','measurement-10000ps-v1/summary.json']:
 j=json.loads((OUT/path).read_text());assert j['passed'];record[path]={'passed':True,'sha256':hashlib.sha256((OUT/path).read_bytes()).hexdigest()}
m=json.loads((OUT/'measurement-10000ps-v1/summary.json').read_text());assert len(m['records'])==27 and m['start']==m['end'] and not m['start']['status']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
v=inspect('rv32-lsu-a-verification');assert v['Id']=='8a5ce817dc80820a5c8eb2195793e9c6554e263b8e2a86e998c88c143e2de1cc' and v['Image']=='sha256:2140263677b3a378d5cab75a3d0d4fd285ddb38a1a5a1f81f5cf97db024a02d5'
record.update(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verification_container={k:v[k] for k in ['Id','Image','State','User']},finished_verification_processes=call(['docker','top','rv32-lsu-a-verification','-eo','pid,comm,args']))
save();call(['docker','stop','rv32-lsu-a-verification']);call(['docker','rm','rv32-lsu-a-verification']);record['verification_removed']=True;save()
image=json.loads(subprocess.check_output(['docker','image','inspect','rv32ooo-orfs:8359fde-flat','--format','{{json .}}'],text=True))
assert image['Id']=='sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33'
free=shutil.disk_usage(ROOT).free;record['free_before_physical_bytes']=free;record['image_size_bytes']=image['Size'];save()
assert free>image['Size']*2+512*2**20,('insufficient space before VFS creation',free,image['Size'])
cid=call(['docker','run','-d','--name','rv32-lsu-a-physical','--user','1000:1000','-v',str(ROOT)+':/workspace','-v',str(ROOT/'build/baseline-setup/ORFS')+':/orfs-source:ro','-w','/workspace','--entrypoint','/bin/sleep','rv32ooo-orfs:8359fde-flat','infinity']).strip()
record['physical_container_id']=cid;save()
a=inspect('rv32-lsu-a-physical');assert a['Id']==cid and a['Image']==image['Id'] and a['State']['Running'];assert all(not x['Destination'].startswith('/OpenROAD-flow-scripts') for x in a['Mounts'])
manifest='/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
call(['docker','exec','rv32-lsu-a-physical','sha256sum','--strict','--quiet','-c',manifest]);record['platform204_before_prune']=True;save()
prune="""import pathlib,shutil,json
root=pathlib.Path('/OpenROAD-flow-scripts/flow');platforms=root/'platforms'
assert platforms.is_dir() and not platforms.is_symlink()
removed=[]
for p in sorted(platforms.iterdir()):
 if p.name not in ('asap7','common') and p.is_dir() and not p.is_symlink():
  shutil.rmtree(p);removed.append(str(p))
p=root/'designs'
if p.is_dir() and not p.is_symlink():shutil.rmtree(p);removed.append(str(p))
print(json.dumps({'removed_unused_private_image_directories':removed}))
"""
record['pruned_unused_private_image_directories']=json.loads(call(['docker','exec','--user','0:0','rv32-lsu-a-physical','python3','-c',prune]));save()
call(['docker','exec','rv32-lsu-a-physical','sha256sum','--strict','--quiet','-c',manifest]);record['platform204_after_prune']=True;record['free_after_physical_prune_bytes']=shutil.disk_usage(ROOT).free;save()
args=['python3','scripts/run_baseline_physical.py','--experiment','experiments/lsu-a-v1/manifest.json','--output-root','build/experiments/lsu-a-v1','--lowered-rtl','build/experiments/lsu-a-v1/rtl_lowered.v','--container','rv32-lsu-a-physical','--adder-mapping','abc','--jobs','2','--detached','--period-ps','5500','--stage','synthesis','--label','synth-clean-v1']
call(args);record['synthesis_launch_command']=args;record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
