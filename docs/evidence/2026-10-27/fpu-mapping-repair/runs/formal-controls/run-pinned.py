import subprocess,json,hashlib,os
from pathlib import Path
out=Path(__file__).parent
os.environ['PATH']='/OpenROAD-flow-scripts/tools/install/yosys/bin:'+os.environ['PATH']
rows=[]
for name in ('positive','negative'):
 cmd=['eqy','--yosys','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','--abc','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-j','1','-d',str(out/(name+'-pinned')),str(out/(name+'.eqy'))]
 with (out/(name+'-pinned.log')).open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(name=name,command=cmd,returncode=r.returncode,status=(out/(name+'-pinned')/'status').read_text().strip() if (out/(name+'-pinned')/'status').exists() else None))
(out/'result-pinned.json').write_text(json.dumps(rows,indent=2)+'\n')
