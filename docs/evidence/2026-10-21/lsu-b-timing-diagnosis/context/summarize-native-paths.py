"""Split input-pin net delay from output-pin cell arcs in six-digit reports."""
from pathlib import Path
import json, re
root=Path('/workspace/rv32_000'); out=root/'build/experiments/lsu-b-diagnosis-v1'
def parse(block):
 nodes=[]
 for line in block.splitlines():
  m=re.match(r'^\s*([\d.\s-]+)\s+([\^v])\s+(\S+)\s+\(([^)]+)\)\s*$',line)
  if not m:continue
  nums,edge,pin,cell=m.groups();nums=[float(s) for s in nums.split()]
  if len(nums)==1:nums.insert(0,0.0) # ideal clock pin has only an arrival column
  assert len(nums)>=2,line
  nodes.append(dict(delay_ps=nums[-2],time_ps=nums[-1],pin=pin,cell=cell,edge=edge))
 start=re.search(r'^Startpoint: (.*?)(?: \(|\n)',block)[1]
 end=re.search(r'^Endpoint: (.*?)(?: \(|\n)',block,re.M)[1]
 active=False;data=[];launch_clock=0.0
 for i,node in enumerate(nodes):
  if node['pin']==start+'/QN':
   assert i>0 and nodes[i-1]['pin']==start+'/CLK'
   launch_clock=nodes[i-1]['time_ps'];active=True
  elif node['pin']==start and node['cell']=='in':active=True
  if active:data.append(node)
  if active and node['pin']==end+'/D':break
 assert data and data[-1]['pin']==end+'/D',(start,end)
 cell_nodes=[n for n in data if n['pin'].endswith(('/Y','/QN'))]
 cq=[n for n in cell_nodes if n['cell'].startswith('DFF')]
 gates=[n for n in cell_nodes if not n['cell'].startswith('DFF')]
 wires=[n for n in data if n not in cell_nodes]
 arrival=data[-1]['time_ps'];summed=sum(n['delay_ps'] for n in data)
 assert abs(summed-(arrival-launch_clock))<0.02,(summed,arrival,launch_clock)
 clocks=[n for n in nodes if n['pin']==end+'/CLK']
 clock_capture=clocks[-1]['time_ps'] if clocks else 0
 required=float(re.findall(r'([-\d.]+)\s+data required time',block)[-1])
 slack=float(re.search(r'([-\d.]+)\s+slack \(',block)[1])
 kind=re.search(r'Path Type: (\w+)',block)[1]
 if 'clock network delay (ideal)' in block:clock_capture=10000 if kind=='max' else 0
 assert abs(slack-((required-arrival) if kind=='max' else (arrival-required)))<0.02
 return dict(start=start,end=end,kind=kind,slack_ps=slack,arrival_ps=arrival,required_ps=required,
  launch_clock_ps=launch_clock,capture_clock_arrival_ps=clock_capture,
  capture_minus_launch_skew_ps=clock_capture-(10000 if kind=='max' else 0)-launch_clock,
  clock_to_q_ps=sum(n['delay_ps'] for n in cq),wire_delay_ps=sum(n['delay_ps'] for n in wires),
  combinational_cell_delay_ps=sum(n['delay_ps'] for n in gates),
  buffer_cell_delay_ps=sum(n['delay_ps'] for n in gates if n['cell'].startswith('BUF')),
  combinational_cells=len(gates),buffers=sum(n['cell'].startswith('BUF') for n in gates),
  nonbuffer_combinational_cells=sum(not n['cell'].startswith('BUF') for n in gates),data_delay_ps=summed,
  data_path_nodes=data)
rows=[]
for p in sorted((out/'native').glob('*/*/*/*.rpt')):
 if p.name not in ('fp_max.rpt','reg2reg_max.rpt','ready_to_tracking_min.rpt','fp_sink_115_max.rpt','fp_sink_124_max.rpt','fp_sink_125_max.rpt'):continue
 candidate,view,corner=p.relative_to(out/'native').parts[:3]
 text=p.read_text();blocks=re.findall(r'Startpoint:.*?slack \((?:MET|VIOLATED)\)',text,re.S)
 assert blocks,p
 # The first path is the lowest slack in these single-group reports.
 parsed=[parse(b) for b in blocks]
 result=min(parsed,key=lambda r:r['slack_ps'])
 rows.append(dict(candidate=candidate,view=view,corner=corner,report=p.name,source=str(p.relative_to(root)),**result))
 for r in [result]:
  if corner=='SS' and p.name=='fp_max.rpt' or candidate=='B' and view=='routed' and p.name=='ready_to_tracking_min.rpt':
   print(candidate,view,corner,p.name,'slack',r['slack_ps'],'cq',r['clock_to_q_ps'],'cell',r['combinational_cell_delay_ps'],'wire',r['wire_delay_ps'],'count',r['combinational_cells'],flush=True)
(out/'native-path-comparison.json').write_text(json.dumps(dict(scope='Cell/net decomposition of selected paths; cell arcs retain actual load and slew effects, not an isolated topology causal model.',records=rows),indent=2)+'\n')
