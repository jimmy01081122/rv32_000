"""Bind recovered synth ODBs to all cells/pins in recorded mapped netlists."""
from pathlib import Path
import gzip, hashlib, importlib.util, json, re
root=Path('/workspace/rv32_000'); out=root/'build/experiments/lsu-b-diagnosis-v1'
spec=importlib.util.spec_from_file_location('netlist_reader',out/'mapped-netlist-reader.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
inputs=json.loads((out/'replay-inputs.json').read_text())['implementations']
records=[]
def odb_name(name):
 # OpenDB stores literal brackets and slashes with backslashes. Verilog
 # escaped identifiers use a leading backslash; compare represented names.
 return name.replace('\\[','[').replace('\\]',']').replace('\\/','/')
for candidate in ('baseline','A','B'):
 path=root/inputs[candidate]['netlist']['path']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==inputs[candidate]['netlist']['sha256']
 cells,drivers,resolve=reader.parse(path)
 stat=path.parents[4]/'reports/asap7/rv32_post_lsu_v1/base/synth_stat.txt'
 expected=int(re.search(r'^\s*(\d+)\s+\S+\s+\d+\s+\S+\s+cells\s*$',stat.read_text(),re.M)[1])
 assert len(cells)==expected,(candidate,len(cells),expected)
 exported={}
 with gzip.open(out/f'{candidate}-synthesis-connectivity.jsonl.gz','rt') as f:
  for line in f:
   name,master,pins=json.loads(line);name=odb_name(name)
   assert name not in exported
   exported[name]=(master,{p:odb_name(n) for p,n in pins.items()})
 missing=sorted(cells.keys()-exported.keys());extra=sorted(exported.keys()-cells.keys());diffs=[]
 for name in cells.keys()&exported.keys():
  original=cells[name];master,pins=exported[name]
  a={p:resolve(n) for p,n in original['pins'].items()}
  b={p:resolve(n) for p,n in pins.items()}
  if master!=original['master'] or a!=b:diffs.append(dict(instance=name,netlist=original,odb=dict(master=master,pins=pins)))
 row=dict(candidate=candidate,mapped_netlist_sha256=inputs[candidate]['netlist']['sha256'],
  synthesis_odb_sha256=inputs[candidate]['synthesis']['sha256'],parser_cell_count=len(cells),
  original_yosys_cell_count=expected,exported_odb_cell_count=len(exported),
  missing_cells=missing,extra_cells=extra,cell_or_pin_differences=diffs,
  passed=not(missing or extra or diffs))
 records.append(row);print(candidate,len(cells),len(exported),'differences',len(missing),len(extra),len(diffs),flush=True)
(out/'synthesis-connectivity-review.json').write_text(json.dumps(dict(scope='Exact master/instance/pin-to-net comparison after scalar alias resolution and OpenDB literal-bracket/slash escape normalization; power/ground ITerms omitted because original netlist has no PG wiring.',records=records,passed=all(r['passed'] for r in records)),indent=2)+'\n')
assert all(r['passed'] for r in records)
