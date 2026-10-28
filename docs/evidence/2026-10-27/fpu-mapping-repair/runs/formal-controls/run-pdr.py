import os,subprocess,json
from pathlib import Path
out=Path(__file__).parent;os.environ['PATH']='/OpenROAD-flow-scripts/tools/install/yosys/bin:'+os.environ['PATH'];rows=[]
for n in ('positive','negative'):
 cmd=['eqy','--yosys','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','--abc','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-j','1','-d',str(out/(n+'-pdr')),str(out/(n+'-pdr.eqy'))]
 with (out/(n+'-pdr.log')).open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(name=n,returncode=r.returncode,command=cmd,pass_marker=(out/(n+'-pdr/PASS')).exists(),fail_marker=(out/(n+'-pdr/FAIL')).exists()))
(out/'result-pdr.json').write_text(json.dumps(rows,indent=2)+'\n')
