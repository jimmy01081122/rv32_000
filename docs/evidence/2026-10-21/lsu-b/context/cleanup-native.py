import datetime,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1';name='rv32-lsu-b-physical';receipt=OUT/'runtime-completion-cleanup.json';assert not receipt.exists()
def call(args):return subprocess.check_output(args,cwd=ROOT,text=True)
for label in ['physical-5500ps-synth-clean-v1','physical-14000ps-backend-clean-v1','physical-14000ps-eco-clean-v1']:
 r=json.loads((OUT/label/'run.json').read_text());assert r['job_state']=='finished' and r['returncode']==0 and r['flow_completed'] and r['input_identities_unchanged']
for label in ['initial-14000ps','diagnostic-boundary-v1']:
 r=json.loads((OUT/'physical-14000ps-eco-clean-v1'/label/'run.json').read_text());assert r['collection_completed'] and len(r['records'])==3 and all(x['returncode']==0 for x in r['records']) and r['platform_validation_after_returncode']==0
assert json.loads((OUT/'review-common-diagnostics-v1.json').read_text())['functional_measurement_passed']
assert json.loads((OUT/'physical-admission-results.json').read_text())['rejection_control_passed']
assert not call(['git','status','--porcelain'])
j=json.loads(call(['docker','inspect',name]))[0];assert j['Id']=='299987b95527443326077bd3bc65e8f3bf3bacc082ac8b6dfe24cd020a1b1381' and j['Image']=='sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33' and j['State']['Running']
top=call(['docker','top',name,'-eo','pid,comm,args']);lines=top.splitlines()[1:];assert len(lines)==1 and lines[0].split()[1]=='sleep',top
manifest='/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt';subprocess.run(['docker','exec',name,'sha256sum','--strict','--quiet','-c',manifest],check=True)
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'all B native jobs ended; timing rejection preserved; remove only idle owned runtime, preserve host bind outputs and pinned images','container_id':j['Id'],'image_id':j['Image'],'idle_processes':top,'platform204_final_check':True,'free_before_bytes':shutil.disk_usage(ROOT).free}
receipt.write_text(json.dumps(r,indent=2)+'\n')
r['stop_output']=call(['docker','stop',name]);r['remove_output']=call(['docker','rm',name]);r['free_after_bytes']=shutil.disk_usage(ROOT).free;r['pinned_images_retained']={tag:call(['docker','image','inspect',tag,'--format','{{.Id}}']).strip() for tag in ['rv32ooo-orfs:8359fde-flat','rv32ooo-fp:p1','rv32ooo-sim:g1','rv32ooo-syn:g1']};receipt.write_text(json.dumps(r,indent=2)+'\n');print('idle native runtime removed; freeGiB',round(r['free_after_bytes']/2**30,3))
