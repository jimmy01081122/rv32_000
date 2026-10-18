#!/usr/bin/env python3
"""Qualify the bounded ASAP7 adder warning interpretation, not analog models."""
import argparse,ast,copy,gzip,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def group(text,pattern):
 m=re.search(pattern,text)
 if not m:raise ValueError('missing group '+pattern)
 start=m.end();depth=1;i=start
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[start:i-1]

def collect(platform):
 rows=[]
 for corner in ('TT','SS','FF'):
  filename=platform/'lib/NLDM'/('asap7sc7p5t_SIMPLE_RVT_'+corner+'_nldm_211120.lib.gz')
  text=gzip.open(filename,'rt').read()
  for name in ('FAx1_ASAP7_75t_R','HAxp5_ASAP7_75t_R'):
   cell=group(text,r'cell\s*\(\s*'+name+r'\s*\)\s*\{');pins={};arcs=[]
   for m in re.finditer(r'\bpin\s*\(\s*(\w+)\s*\)\s*\{',cell):
    pin=group(cell[m.start():],r'pin\s*\(\s*\w+\s*\)\s*\{');direction=re.search(r'direction\s*:\s*(\w+)',pin)[1];function=re.search(r'function\s*:\s*"([^"]+)"',pin);pins[m[1]]={'direction':direction,'function':function[1] if function else None}
    for a in re.finditer(r'\btiming\s*\([^)]*\)\s*\{',pin):
     t=group(pin[a.start():],r'timing\s*\([^)]*\)\s*\{')
     def field(f):
      v=re.search(f+r'\s*:\s*([^;]+)',t);return v[1].strip('" ') if v else None
     arcs.append({'to':m[1],'from':field('related_pin'),'type':field('timing_type'),'sense':field('timing_sense'),'when':field('when'),'rise':bool(re.search(r'\bcell_rise\s*\(',t)),'fall':bool(re.search(r'\bcell_fall\s*\(',t))})
   rows.append({'corner':corner,'cell':name,'pins':pins,'arcs':arcs,'library_file':str(filename),'library_sha256':sha(filename)})
 return rows

def boolean(expression,values):
 node=ast.parse(expression.replace('!',' not ').replace('*',' and ').replace('+',' or ').strip(),mode='eval').body
 def visit(n):
  if isinstance(n,ast.Name):return bool(values[n.id])
  if isinstance(n,ast.Constant) and n.value in (0,1,False,True):return bool(n.value)
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):return not visit(n.operand)
  if isinstance(n,ast.BoolOp):
   evaluated=[visit(v) for v in n.values]
   if isinstance(n.op,ast.And):return all(evaluated)
   if isinstance(n.op,ast.Or):return any(evaluated)
  raise ValueError('unsupported Liberty Boolean expression')
 return visit(node)

def validate(rows):
 assert len(rows)==6
 results=[]
 for r in rows:
  pins=r['pins'];inputs=sorted(p for p,v in pins.items() if v['direction']=='input');outputs=['CON','SN'];transitions=0
  assert set(inputs)==({'A','B','CI'} if r['cell'].startswith('FA') else {'A','B'})
  for bits in itertools.product((0,1),repeat=len(inputs)):
   values=dict(zip(inputs,bits));actual={p:boolean(pins[p]['function'],values) for p in outputs}
   expected={'CON':sum(bits)<(2 if len(inputs)==3 else 2),'SN':sum(bits)%2==0}
   assert actual==expected,(r['cell'],'truth table',values)
   for source in inputs:
    changed=dict(values);changed[source]=1-changed[source]
    for target in outputs:
     final=boolean(pins[target]['function'],changed)
     if actual[target]==final:continue
     transitions+=1;rising=final
     sense='positive_unate' if bool(values[source])==actual[target] else 'negative_unate'
     matches=[a for a in r['arcs'] if a['from']==source and a['to']==target
       and a['sense'] in (sense,'non_unate') and a['type'] in ('combinational','combinational_rise' if rising else 'combinational_fall')
       and a['rise' if rising else 'fall'] and (not a['when'] or boolean(a['when'],dict(values,**actual)))]
     assert matches,(r['corner'],r['cell'],'uncovered transition',source,target,values)
  ignored=[a for a in r['arcs'] if a['from'] not in inputs]
  assert all(a['from']=='CON' and a['to']=='SN' for a in ignored)
  results.append({'corner':r['corner'],'cell':r['cell'],'truth_states':2**len(inputs),'covered_transitions':transitions,'extra_output_groups':len(ignored)})
 return results

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--out',type=Path,required=True)
 parser.add_argument('--openroad',default='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad')
 args=parser.parse_args()
 if not __debug__:parser.error('assertion-enabled Python required for the structural audit')
 out=args.out.resolve()
 if not out.is_relative_to(ROOT/'build'):parser.error('output must be under build/')
 if out.exists():parser.error('output exists; choose a fresh directory')
 out.mkdir(parents=True);summary=out/'summary.json'
 report={'scope':'bounded Boolean/functional-arc and independent-STA path coverage; not analog characterization or core timing closure','openroad_binary_sha256':sha(Path(args.openroad)),'passed':False}
 summary.write_text(json.dumps(report,indent=2)+'\n')
 rows=collect(Path('/OpenROAD-flow-scripts/flow/platforms/asap7'))
 expected={(c,n) for c in ('TT','SS','FF') for n in ('FAx1_ASAP7_75t_R','HAxp5_ASAP7_75t_R')}
 if {(r['corner'],r['cell']) for r in rows}!=expected:raise ValueError('incomplete corner/cell set')
 report['coverage']=validate(rows)
 (out/'raw-arcs.json').write_text(json.dumps(rows,indent=2)+'\n')
 report['raw_arcs_sha256']=sha(out/'raw-arcs.json')
 report['libraries']={r['library_file']:r['library_sha256'] for r in rows}
 report['negative_controls']=[]
 for fault in ('missing_arc','missing_table','wrong_function'):
  broken=copy.deepcopy(rows)
  if fault=='missing_arc':broken[0]['arcs']=[a for a in broken[0]['arcs'] if not(a['from']=='A' and a['to']=='SN')]
  if fault=='missing_table':
   for a in broken[0]['arcs']:
    if a['from']=='A' and a['to']=='SN':a['fall']=False
  if fault=='wrong_function':broken[0]['pins']['SN']['function']='0'
  try:validate(broken)
  except AssertionError:report['negative_controls'].append({'fault':fault,'rejected':True})
  else:raise ValueError('negative control accepted '+fault)
 report['sta_records']=[]
 for corner in ('TT','SS','FF'):
  directory=out/corner;directory.mkdir()
  env=dict(os.environ,RV32_CORNER=corner,RV32_REPORT_DIR=str(directory))
  command=[args.openroad,'-no_init','-exit',str(ROOT/'physical/asap7/baseline/adder_audit.tcl')]
  with (directory/'sta.log').open('w') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
  if result.returncode:raise ValueError(corner+' STA failed')
  for source in ('A','B','CI'):
   for target in ('FCON','FSN','HCON','HSN'):
    if source=='CI' and target.startswith('H'):continue
    path=directory/(source+'_'+target+'.rpt');text=path.read_text()
    types=set(re.findall(r'Path Type:\s*(min|max)',text))
    if types!={'min','max'} or 'No paths' in text:raise ValueError('missing path '+str(path))
    report['sta_records'].append({'corner':corner,'path':source+'_'+target,'sha256':sha(path)})
  if not re.search(r'\btime\s+1ps\b',(directory/'units.rpt').read_text()):raise ValueError('unexpected library time units')
 report['source_sha256']={name:sha(ROOT/name) for name in ('scripts/audit_asap7_adders.py','physical/asap7/baseline/adder_audit.tcl','physical/asap7/baseline/adder_audit.v','physical/asap7/baseline/timing_common.tcl')}
 report['passed']=len(report['sta_records'])==30 and sum(r['covered_transitions'] for r in report['coverage'])==144
 summary.write_text(json.dumps(report,indent=2)+'\n')
 print('ASAP7 adder audit:',report['passed'],'144 transitions, 30 min/max paths, 3 negative controls',flush=True)
 if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
