"""Parser for the scalar named-pin instances in the archived ASAP7 netlists."""
import re
def norm(s):return s.strip().removeprefix('\\')
def parse(path):
 text=re.sub(r'\(\*.*?\*\)','',path.read_text(),flags=re.S)
 cells={}
 for m in re.finditer(r'^\s*(\S+_ASAP7_75t_R)\s+(\\?\S+)\s*\((.*?)\n\s*\);',text,re.M|re.S):
  master,name,body=m.groups();name=norm(name)
  pins={p:norm(v) for p,v in re.findall(r'\.(\w+)\(([^()]*)\)',body)}
  assert name not in cells
  outputs=set(pins)&{'Y','QN','Q','H','L'}
  assert len(outputs)==1,(name,master,pins)
  output=outputs.pop();cells[name]=dict(master=master,pins=pins,output=output)
 aliases={norm(a):norm(b) for a,b in re.findall(r'^\s*assign\s+(.*?)\s*=\s*(.*?);',text,re.M)
          if not any(c in a+b for c in '{}~&|^?:()+*/')}
 def resolve(net):
  seen=set()
  while net in aliases:
   assert net not in seen,(net,'alias cycle');seen.add(net);net=aliases[net]
  return net
 drivers={}
 for name,c in cells.items():
  net=resolve(c['pins'][c['output']]);assert net not in drivers,(net,name,drivers.get(net));drivers[net]=name
 return cells,drivers,resolve
