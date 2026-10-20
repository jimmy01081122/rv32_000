"""Remove only the verified idle experiment container; preserve pinned images."""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import subprocess

ROOT=Path('/workspace/rv32_000')
EXP=ROOT/'build/experiments/lsu-a-v1'
NAME='rv32-lsu-a-physical'
EXPECTED_ID='054ebe72b3728686b6e7edd14f5daf63972b4037af3afd74ed069c3848949ab0'
IMAGE='sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33'
OUT=EXP/'runtime-completion-cleanup.json'
assert not OUT.exists()
worker=json.loads((EXP/'measurement-9900ps-relaunch-v2/run.json').read_text())
supervisor=json.loads((EXP/'measurement-review-supervisor.json').read_text())
assert worker['flow_completed'] and worker['input_identities_unchanged'] and worker['returncode']==0
assert supervisor['complete'] and not supervisor.get('error')
for name in ['review-common-clock-v1.json','review-fastest-v1.json']:
    assert json.loads((EXP/name).read_text())['passed']
identity=subprocess.check_output(['docker','inspect','--format','{{.Id}}|{{.Image}}|{{.State.Status}}',NAME],text=True).strip().split('|')
assert identity==[EXPECTED_ID,IMAGE,'running'],identity
rows=subprocess.check_output(['docker','top',NAME,'-eo','pid,comm'],text=True).splitlines()[1:]
commands=[row.strip().split(None,1)[1] for row in rows]
assert [x.strip() for x in commands]==['sleep'],commands
record={'scope':'Completed measurement and independent reviews; remove only the verified idle owned container. No images or source/result files deleted.',
        'started_utc':datetime.now(timezone.utc).isoformat(),'container_name':NAME,'container_id':EXPECTED_ID,
        'image_id':IMAGE,'idle_process_rows':rows,'idle_process_commands':commands,'measurement_returncode':0,
        'measurement_inputs_unchanged':True,'both_operating_point_reviews_passed':True,
        'free_before_bytes':shutil.disk_usage(ROOT).free,'commands':[]}
for command in [['docker','stop','--time','10',NAME],['docker','rm',EXPECTED_ID]]:
    result=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    record['commands'].append({'command':command,'returncode':result.returncode,'output':result.stdout})
    OUT.write_text(json.dumps(record,indent=2)+'\n')
    assert result.returncode==0,result.stdout
assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],text=True).strip()==IMAGE
record.update(image_retained=True,free_after_bytes=shutil.disk_usage(ROOT).free,
              finished_utc=datetime.now(timezone.utc).isoformat(),completed=True)
OUT.write_text(json.dumps(record,indent=2)+'\n')
print('Idle owned runtime removed; pinned image retained; reclaimed bytes',record['free_after_bytes']-record['free_before_bytes'])
