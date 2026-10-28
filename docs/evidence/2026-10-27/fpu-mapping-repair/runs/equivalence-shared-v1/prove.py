import os,subprocess,json,datetime
from pathlib import Path
out=Path(__file__).parent
os.environ['PATH']='/OpenROAD-flow-scripts/tools/install/yosys/bin:'+os.environ['PATH']
cmd=['eqy','--yosys','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','--abc','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-j','1','-d',str(out/'work'),str(out/'proof.eqy')]
r=dict(command=cmd,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='running')
(out/'proof-result.json').write_text(json.dumps(r,indent=2)+'\n')
with (out/'prove.log').open('x') as log:
 try:
  result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
  r.update(returncode=result.returncode,state='finished')
 except subprocess.TimeoutExpired:r.update(state='timeout')
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
r['pass_marker']=(out/'work/PASS').exists()
(out/'proof-result.json').write_text(json.dumps(r,indent=2)+'\n')
