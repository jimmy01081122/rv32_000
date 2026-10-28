from pathlib import Path
import subprocess,json,datetime
out=Path(__file__).parent;rows=[]
for n in ('gold','gate'):
 cmd=['/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/(n+'.ys'))]
 with (out/(n+'.log')).open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(stage=n,command=cmd,returncode=r.returncode));assert r.returncode==0
cmd=['/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-c','cec '+str(out/'gold.blif')+' '+str(out/'gate.blif')]
r=dict(stage='cec',command=cmd,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='running');rows.append(r);(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
with (out/'cec.log').open('x') as log:
 try:
  result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=900);r.update(state='finished',returncode=result.returncode)
 except subprocess.TimeoutExpired:r.update(state='timeout')
r['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['equivalent']='Networks are equivalent' in (out/'cec.log').read_text();(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
