import subprocess,json,hashlib
from pathlib import Path
out=Path(__file__).parent
rows=[]
for name in ('positive','negative'):
 cmd=['eqy','--yosys','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','--abc','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-j','1','-d',str(out/name),str(out/(name+'.eqy'))]
 with (out/(name+'.log')).open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(name=name,command=cmd,returncode=r.returncode,status=(out/name/'status').read_text().strip() if (out/name/'status').exists() else None))
(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
