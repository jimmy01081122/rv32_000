"""Cross-check the inductive proof using actual RTL mutations and shape faults."""
from pathlib import Path
import copy, datetime, gzip, hashlib, importlib.util, json, subprocess
ROOT=Path('/workspace');BASE=ROOT/'build/experiments/lsu-b-validation-v2';OUT=BASE/'fpu-negative-controls-v1';OUT.mkdir()
PROOF=BASE/'fpu-state-relation-v1';SOURCE=ROOT/'build/experiments/fpu-mapping-v1/shared-unit-v1/fp-source.v';GEN=ROOT/'experiments/lsu-b-validation-v2/fpu_state_models.py';MAPPED=ROOT/'build/experiments/fpu-mapping-v1/shared-unit-v1/results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json';YOSYS='/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys';ABC=YOSYS+'-abc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs={str(p):sha(p) for p in [Path(__file__),SOURCE,GEN,MAPPED,PROOF/'cell.json',PROOF/'proof-summary.json',PROOF/'step-gate.blif']},records=[],passed=False)
def save():(OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def run(command,log):
 with log.open('x') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 assert r.returncode==0,(command,r.returncode)
 return dict(command=command,returncode=r.returncode,log_sha256=sha(log))
save()
for label,before,after,mode in [('rtl-drop-valid','holding_valid <= issue_valid;',"holding_valid <= 1'b0;",'step'),('rtl-reset-high',"holding_valid <= 1'b0;","holding_valid <= 1'b1;",'reset')]:
 out=OUT/label;out.mkdir();text=SOURCE.read_text();assert text.count(before)==1
 source=out/'mutant.v';source.write_text(text.replace(before,after));prepare=out/'prepare.ys';prepare.write_text(f'read_verilog {source}\nhierarchy -check -top rv32_ooo_fp_execute\nproc\nopt_clean\ncheck -assert\nwrite_json {out}/original.json\n')
 row=dict(label=label,mutation=dict(before=before,after=after),source_sha256=sha(source),commands=[]);report['records'].append(row);save()
 row['commands'].append(run([YOSYS,'-s',str(prepare)],out/'prepare.log'))
 row['commands'].append(run(['python3',str(GEN),'--original',str(out/'original.json'),'--mapped',str(MAPPED),'--cell',str(PROOF/'cell.json'),'--output',str(out/'models')],out/'models.log'))
 n=mode+'-gold';script=out/'lower.ys';original=(PROOF/(n+'.ys')).read_text();script.write_text(original.replace(str(PROOF/'models'/(n+'.json')),str(out/'models'/(n+'.json'))).replace(str(PROOF/(n+'-lowered.json')),str(out/'lowered.json')).replace(str(PROOF/(n+'.blif')),str(out/'mutant.blif')))
 row['commands'].append(run([YOSYS,'-s',str(script)],out/'lower.log'))
 lowered=json.loads((out/'lowered.json').read_text())['modules']['rv32_ooo_fp_execute'];allowed={'$_AND_','$_OR_','$_NOT_','$_XOR_','$_XNOR_','$_NAND_','$_NOR_','$_MUX_','$_NMUX_','$_ANDNOT_','$_ORNOT_','$_AOI3_','$_OAI3_','$_AOI4_','$_OAI4_'};assert {c['type'] for c in lowered['cells'].values()}<=allowed
 reference=PROOF/('step-gate.blif' if mode=='step' else 'reset-gold-zero.blif')
 row['commands'].append(run([ABC,'-c',f'cec {out}/mutant.blif {reference}'],out/'cec.log'))
 log=(out/'cec.log').read_text();row.update(rejected='Networks are NOT EQUIVALENT' in log and 'Networks are equivalent' not in log);assert row['rejected'];save();print(label,'REJECTED',flush=True)
 p=out/'lowered.json';raw=p.read_bytes()
 with gzip.GzipFile(filename=str(p)+'.gz',mode='wb',mtime=0) as f:f.write(raw)
 assert gzip.decompress(Path(str(p)+'.gz').read_bytes())==raw
 row['lowered_json_compaction']=dict(sha256=sha(p),raw_bytes=len(raw),gzip_sha256=sha(Path(str(p)+'.gz')));p.unlink();save()
spec=importlib.util.spec_from_file_location('models',GEN);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
gate=module.load(MAPPED);cell=module.load(PROOF/'cell.json',module.FF);gold=module.load(PROOF/'original.json')
for label in ['mapped-wrong-clock','hidden-mapped-state','gold-init','wrong-ff-polarity']:
 try:
  if label.startswith('mapped-') or label=='hidden-mapped-state':
   m=copy.deepcopy(gate);n=next(n for n,c in m['cells'].items() if c['type']==module.FF)
   if label=='mapped-wrong-clock':m['cells'][n]['connections']['CLK']=m['ports']['rst']['bits']
   else:m['cells']['$extra_hidden']=copy.deepcopy(m['cells'][n])
   module.mapped_relation(m)
  elif label=='gold-init':
   m=copy.deepcopy(gold);next(iter(m['netnames'].values()))['attributes']['init']='0';module.gold_flops(m)
  else:
   m=copy.deepcopy(cell);next(c for c in m['cells'].values() if c['type']=='$_DFF_P_')['connections']['D']=m['ports']['D']['bits'];module.validate_library_cell(m)
 except ValueError as e:report['records'].append(dict(label=label,rejected=True,reason=str(e)))
 else:raise AssertionError('accepted '+label)
 save()
report.update(input_identities_unchanged=all(sha(Path(p))==h for p,h in report['inputs'].items()),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());report['passed']=report['input_identities_unchanged'] and len(report['records'])==6 and all(r['rejected'] for r in report['records']);save();assert report['passed'];print('ALL SIX NEGATIVE CONTROLS PASS',flush=True)
