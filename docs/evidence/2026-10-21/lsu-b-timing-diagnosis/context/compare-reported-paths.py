"""Compare per-group paths, without treating rounded path text as qualification."""
from pathlib import Path
import re, json, hashlib
root=Path('/workspace/rv32_000')
out=root/'build/experiments/lsu-b-diagnosis-v1'
sources={
 'baseline':root/'docs/evidence/2026-10-18/post-lsu-baseline/physical/boundary-9900-10000ps',
 'A':root/'docs/evidence/2026-10-20/lsu-a-physical/physical/physical-14000ps-eco-clean-v1/boundary-v1',
 'B':root/'build/experiments/lsu-b-v1/physical-14000ps-eco-clean-v1/diagnostic-boundary-v1',
}
rows=[]
for name,base in sources.items():
 for corner,kind in [('SS','setup'),('FF','hold'),('TT','hold')]:
  path=base/corner/f'{kind}_paths_10000.rpt'
  raw=path.read_text()
  blocks=re.findall(r'Startpoint:.*?slack \((?:MET|VIOLATED)\)',raw,re.S)
  for group in ['in2out','in2reg','reg2out','reg2reg']:
   subset=[b for b in blocks if f'Path Group: {group}\n' in b]
   if not subset: continue
   block=min(subset,key=lambda b:float(re.search(r'(-?[\d.]+)\s+slack \(',b)[1]))
   nodes=[]; active=False
   for line in block.splitlines():
    m=re.fullmatch(r'\s*(-?[\d.]+)\s+(-?[\d.]+)\s+([\^v])\s+(\S+)\s+\(([^)]+)\)\s*',line)
    if not m: continue
    delay,time,edge,pin,cell=m.groups()
    if pin.endswith('/QN') or (cell=='in' and pin!='clk'): active=True
    if active: nodes.append(dict(delay_ps=float(delay),arrival_ps=float(time),edge=edge,pin=pin,cell=cell))
    if active and pin.endswith('/D'): break
   gates=[n for n in nodes if n['cell'].endswith('_ASAP7_75t_R') and not n['cell'].startswith('DFF')]
   row=dict(candidate=name,corner=corner,kind=kind,group=group,period_ps=10000,
     source=str(path.relative_to(root)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
     start=re.search(r'Startpoint: (.*)',block)[1],end=re.search(r'Endpoint: (.*)',block)[1],
     slack_ps_rounded=float(re.search(r'(-?[\d.]+)\s+slack \(',block)[1]),
     data_path_nodes=nodes,combinational_cells=len(gates),
     buffer_cells=sum(n['cell'].startswith('BUF') for n in gates),
     inverter_cells=sum(n['cell'].startswith('INV') for n in gates),
     data_path_delay_ps_rounded=sum(n['delay_ps'] for n in nodes),
     note='Each output row combines its cell arc and preceding net delay; this is not a cell/wire split.')
   rows.append(row)
   (out/f'{name}-{corner}-{kind}-{group}.rpt').write_text(block+'\n')
   if group=='reg2reg' and kind=='setup' or kind=='hold' and group=='in2reg':
    print(name,corner,kind,group,row['slack_ps_rounded'],len(gates),row['buffer_cells'],row['start'],row['end'])
(out/'reported-path-comparison.json').write_text(json.dumps(dict(scope='per-group reported path diagnostics, not physical qualification',records=rows),indent=2)+'\n')
