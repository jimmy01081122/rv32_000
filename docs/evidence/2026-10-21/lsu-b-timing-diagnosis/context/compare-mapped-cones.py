"""Structural diagnostics of the original scalar, flat ASAP7 mapped netlists.

This is not logical equivalence. It fails on duplicate drivers or unsupported
cell outputs rather than silently making an incomplete cone comparison.
"""
from pathlib import Path
from functools import lru_cache
import collections, hashlib, json, re, sys
sys.setrecursionlimit(10000)
root=Path('/workspace/rv32_000'); out=root/'build/experiments/lsu-b-diagnosis-v1'
def sha(b):return hashlib.sha256(b).hexdigest()
netlists={
 'baseline':root/'build/baselines/ap5b-post-lsu-v1/physical-5500ps-abc-mapping-probe/results/asap7/rv32_post_lsu_v1/base/1_2_yosys.v',
 'A':root/'build/experiments/lsu-a-v1/physical-5500ps-synth-clean-v1/results/asap7/rv32_post_lsu_v1/base/1_2_yosys.v',
 'B':root/'build/experiments/lsu-b-v1/physical-5500ps-synth-clean-v1/results/asap7/rv32_post_lsu_v1/base/1_2_yosys.v',
}
import importlib.util
spec=importlib.util.spec_from_file_location('netlist_reader',out/'mapped-netlist-reader.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
parse=reader.parse
results={};selected_paths=json.loads((out/'reported-path-comparison.json').read_text())['records']
for candidate,path in netlists.items():
 cells,drivers,resolve=parse(path)
 unknown=set()
 @lru_cache(None)
 def walk(net):
  net=resolve(net)
  if net not in drivers:
   # Explicit primary-input or constant leaves, never an anonymous ABC wire.
   if re.fullmatch(r'_\d+_',net):unknown.add(net)
   return sha(('leaf:'+net).encode()),0
  name=drivers[net];c=cells[name]
  if c['master'].startswith('DFF'):return sha(('register:'+name+':'+c['output']).encode()),0
  inputs=[(p,walk(v)) for p,v in sorted(c['pins'].items()) if p!=c['output']]
  digest=sha(json.dumps([c['master'],[(p,v[0]) for p,v in inputs]],separators=(',',':')).encode())
  return digest,1+max((v[1] for p,v in inputs),default=0)
 sinks={}
 for name,c in cells.items():
  if name.startswith('u_fp_execute.cmp_data') and c['master'].startswith('DFF'):
   digest,depth=walk(c['pins']['D']);sinks[name]=dict(structural_sha256=digest,max_combinational_cell_depth=depth)
 assert not unknown,unknown
 p=next(r for r in selected_paths if r['candidate']==candidate and r['corner']=='SS' and r['kind']=='setup' and r['group']=='reg2reg')
 mapped=[];unmapped=[]
 for node in p['data_path_nodes']:
  name=node['pin'].rsplit('/',1)[0]
  if node['cell'].startswith(('DFF','BUF')):continue
  if name in cells:mapped.append(dict(instance=name,original_master=cells[name]['master'],final_master=node['cell']))
  else:unmapped.append(name)
 results[candidate]=dict(path=str(path.relative_to(root)),sha256=sha(path.read_bytes()),cell_count=len(cells),
   fp_completion_sinks=sinks,selected_routed_path_original_nonbuffer_cells=mapped,
   selected_routed_path_unmatched_nonbuffer_cells=unmapped,
   selected_routed_path_nonbuffer_cell_count=len(mapped),unresolved_anonymous_cone_nets=sorted(unknown))
 print(candidate,'mapped cells',len(cells),'selected path original nonbuffers',len(mapped),'unmatched',len(unmapped),'sinks',len(sinks),flush=True)
 lowered={
  'baseline':root/'build/baseline-setup/rtl_lowered.v',
  'A':root/'build/experiments/lsu-a-v1/rtl_lowered.v',
  'B':root/'build/experiments/lsu-b-v1/rtl_lowered.v',
 }
 modules={}
 for name,p in lowered.items():
  body=re.search(r'^module rv32_ooo_fp_execute\b.*?^endmodule',p.read_text(),re.M|re.S)[0]
  modules[name]=dict(path=str(p.relative_to(root)),file_sha256=sha(p.read_bytes()),fp_module_sha256=sha(body.encode()))
common=set.intersection(*(set(r['fp_completion_sinks']) for r in results.values()))
comparisons={n:dict(common_sinks=len(common),structurally_identical_to_baseline=sum(results[n]['fp_completion_sinks'][k]['structural_sha256']==results['baseline']['fp_completion_sinks'][k]['structural_sha256'] for k in common)) for n in ('A','B')}
assert len({v['fp_module_sha256'] for v in modules.values()})==1,modules
report=dict(scope='structural mapped-cone diagnostics; different signatures do not imply functional inequivalence',lowered_fp_modules=modules,records=results,comparisons=comparisons)
(out/'mapped-cone-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('FP lowered module identical',comparisons)
