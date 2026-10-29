from pathlib import Path
import datetime,hashlib,json,subprocess
root=Path('/workspace');out=Path(__file__).parent;models=out/'models'
yosys='/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys';abc=yosys+'-abc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
libs=[Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')/n for n in ['asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz']]
inputs=[Path(__file__),root/'experiments/lsu-b-validation-v2/fpu_state_models.py',out/'original.json',out/'cell.json',root/'build/experiments/fpu-mapping-v1/shared-unit-v1/fp-source.v',root/'build/experiments/fpu-mapping-v1/shared-unit-v1/results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json',*models.glob('*.json'),*libs,Path(yosys),Path(abc)]
report=dict(scope='reset-established full FPU state relation; no internal arithmetic cutpoints',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs={str(p):sha(p) for p in inputs},stages=[],passed=False,state='running')
def save():(out/'proof-summary.json').write_text(json.dumps(report,indent=2)+'\n')
save()
allowed={'$_AND_','$_OR_','$_NOT_','$_XOR_','$_XNOR_','$_NAND_','$_NOR_','$_MUX_','$_NMUX_','$_ANDNOT_','$_ORNOT_','$_AOI3_','$_OAI3_','$_AOI4_','$_OAI4_'}
def lower(n):
 script=out/(n+'.ys');script.write_text('\n'.join('read_liberty -ignore_miss_func '+str(p) for p in libs)+f'''
read_json {models/(n+'.json')}
setattr -mod -unset keep_hierarchy
hierarchy -check -top rv32_ooo_fp_execute
flatten
delete =A:whitebox =A:blackbox
hierarchy -check -top rv32_ooo_fp_execute
synth -top rv32_ooo_fp_execute -noabc -extra-map /orfs-source/flow/platforms/common/lcu_kogge_stone.v
check -assert
write_json {out/(n+'-lowered.json')}
write_blif -noalias {out/(n+'.blif')}
''')
 command=[yosys,'-s',str(script)]
 with (out/(n+'.log')).open('x') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 row=dict(stage='lower-'+n,command=command,returncode=r.returncode,script_sha256=sha(script),log_sha256=sha(out/(n+'.log')));report['stages'].append(row);save();assert r.returncode==0
 design=json.loads((out/(n+'-lowered.json')).read_text());assert set(design['modules'])=={'rv32_ooo_fp_execute'}
 m=design['modules']['rv32_ooo_fp_execute'];types={c['type'] for c in m['cells'].values()};assert types<=allowed,types-allowed
 row.update(combinational_cells=len(m['cells']),no_remaining_state=True,blif_sha256=sha(out/(n+'.blif')));save();print('LOWERED',n,len(m['cells']),flush=True)
def cec(label,a,b,expected):
 command=[abc,'-c',f'cec {out/(a+".blif")} {out/(b+".blif")}'];row=dict(stage=label,command=command,state='running',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['stages'].append(row);save();print('PROVING',label,flush=True)
 with (out/(label+'.log')).open('x') as log:
  try:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1800);row.update(returncode=r.returncode,state='finished')
  except subprocess.TimeoutExpired:row.update(state='timeout')
 text=(out/(label+'.log')).read_text();equal='Networks are equivalent' in text;unequal='Networks are NOT EQUIVALENT' in text
 row.update(equivalent=equal,inequivalent=unequal,expected_equivalent=expected,passed=row.get('returncode')==0 and (equal and not unequal if expected else unequal and not equal),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),log_sha256=sha(out/(label+'.log')));save();assert row['passed'],row;print('PROVED',label,flush=True)
try:
 for role in ('gold','gate'):
  for n in (f'reset-{role}',f'reset-{role}-zero'):lower(n)
  cec('reset-'+role+'-proof','reset-'+role,'reset-'+role+'-zero',True)
 for n in ('step-gold','step-gate'):lower(n)
 cec('step-output-proof','step-gold','step-gate',True)
 lower('step-mutant');cec('negative-bit-proof','step-gold','step-mutant',False)
 report.update(input_identities_unchanged=all(sha(Path(p))==h for p,h in report['inputs'].items()))
 report['passed']=report['input_identities_unchanged']
finally:
 report.update(state='finished',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
raise SystemExit(0 if report['passed'] else 1)
