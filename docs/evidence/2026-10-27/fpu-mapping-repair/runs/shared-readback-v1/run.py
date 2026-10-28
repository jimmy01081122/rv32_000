from pathlib import Path
import os,subprocess,json,hashlib,datetime
out=Path(__file__).parent;base=out.parent;rows=[]
for n in ('baseline','A','B'):
 with (out/(n+'-flatten.log')).open('x') as log:
  r=subprocess.run(['/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/(n+'.ys'))],stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(candidate=n,flatten_returncode=r.returncode));assert r.returncode==0
odbexport=subprocess.run(['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-python',str(out/'export.py')]);assert odbexport.returncode==0
for n in ('baseline','A','B'):
 d=out/n;d.mkdir();odb=base/'shared-native-v1'/n/'results/asap7/rv32_post_lsu_v1/base/1_synth.odb'
 env=dict(os.environ,RV32_CORNER='SS',RV32_ODB=str(odb),RV32_OUT=str(d))
 with (d/'sta.log').open('x') as log:r=subprocess.run(['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','-threads','1','/workspace/physical/asap7/fpu-isolated/synthesis_timing.tcl'],env=env,stdout=log,stderr=subprocess.STDOUT)
 rows.append(dict(candidate=n,timing_returncode=r.returncode,odb_sha256=hashlib.sha256(odb.read_bytes()).hexdigest()));assert r.returncode==0
(out/'native-results.json').write_text(json.dumps(dict(records=rows,complete=True),indent=2)+'\n')
