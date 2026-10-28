import os,subprocess,json,hashlib
from pathlib import Path
root=Path('/workspace');out=Path(__file__).parent
os.environ['PATH']='/OpenROAD-flow-scripts/tools/install/yosys/bin:'+os.environ['PATH']
cmd=['eqy','--yosys','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','--abc','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc','-m','-j','1','-d',str(out/'work'),str(out/'proof.eqy')]
with (out/'prepare.log').open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
(out/'prepare-result.json').write_text(json.dumps(dict(command=cmd,returncode=r.returncode),indent=2)+'\n')
