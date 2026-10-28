#!/usr/bin/env python3
"""Compare each mapped cell and signal pin after native OpenDB import."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

def name(s):
    return s.strip().removeprefix('\\').replace('\\[','[').replace('\\]',']').replace('\\/','/')

def read_flat(path):
    text = path.read_text()
    cells = {}
    for match in re.finditer(r'^\s*(\S+_ASAP7_75t_R)\s+(\\?\S+)\s*\((.*?)\n\s*\);', text, re.M|re.S):
        master, instance, body = match.groups()
        instance = name(instance)
        if instance in cells:
            raise ValueError('duplicate cell')
        pins = {p:name(v) for p,v in re.findall(r'\.(\w+)\(([^()]*)\)',body)}
        cells[instance] = (master,pins)
    scalar = r"(?:\\\S+|[A-Za-z_$][\w$]*(?:\[\d+\])?)"
    widths = {name(n):(int(a),int(b)) for a,b,n in re.findall(
        r'\b(?:wire|input|output)\s+\[(\d+):(\d+)\]\s+(\\?\S+)\s*;',text)}
    def bits(expr):
        expr=expr.strip()
        if expr.startswith('{') and expr.endswith('}'):
            result=[];depth=0;start=1
            for i,c in enumerate(expr[1:-1],1):
                if c=='{':depth+=1
                elif c=='}':depth-=1
                elif c==',' and depth==0:
                    result.extend(bits(expr[start:i]));start=i+1
            result.extend(bits(expr[start:-1]));return result
        const=re.fullmatch(r"(\d+)'b([01xz]+)",expr,re.I)
        if const:
            width=int(const[1]);digits=const[2].lower()
            if len(digits)>width:raise ValueError('oversized binary constant')
            return ["1'b"+c for c in digits.rjust(width,'0')]
        if not re.fullmatch(scalar,expr):
            raise ValueError('unsupported reference expression: '+expr[:120])
        n=name(expr)
        if n in widths:
            high,low=widths[n];step=-1 if high>=low else 1
            return [f'{n}[{i}]' for i in range(high,low+step,step)]
        return [n]
    aliases = {}
    for a,b in re.findall(r'^\s*assign\s+(.*?)\s*=\s*(.*?);',text,re.M):
        lhs,rhs=bits(a),bits(b)
        if len(lhs)!=len(rhs):raise ValueError('alias width mismatch')
        for x,y in zip(lhs,rhs):
            if x in aliases:raise ValueError('duplicate alias driver')
            aliases[x]=y
    def resolve(net):
        seen=set()
        while net in aliases:
            if net in seen: raise ValueError('alias cycle')
            seen.add(net);net=aliases[net]
        return net
    resolve.top_outputs = {resolve(bit) for port in re.findall(
        r'^\s*output\s+(?:\[\d+:\d+\]\s+)?(\\?\S+)\s*;',text,re.M) for bit in bits(port)}
    if not resolve.top_outputs: raise ValueError('no top-level outputs found')
    return cells,resolve

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('directory',type=Path);args=ap.parse_args()
    records=[]
    for variant in ('baseline','A','B'):
        path=args.directory/(variant+'-flat.v');cells,resolve=read_flat(path);exported={}
        with gzip.open(args.directory/(variant+'-synthesis-connectivity.jsonl.gz'),'rt') as f:
            for line in f:
                inst,master,pins=json.loads(line);inst=name(inst)
                if inst in exported:raise ValueError('duplicate exported instance')
                exported[inst]=(master,{p:name(n) for p,n in pins.items()})
        missing=sorted(cells.keys()-exported.keys());extra=sorted(exported.keys()-cells.keys());diff=[]
        for inst in cells.keys()&exported.keys():
            a,apins=cells[inst];b,bpins=exported[inst]
            if a!=b or {p:resolve(n) for p,n in apins.items()}!={p:resolve(n) for p,n in bpins.items()}:
                diff.append(dict(instance=inst,reference=cells[inst],readback=exported[inst]))
        # Native ORFS read_netlist removes unused instances, including state
        # that only supplies unused FPU input bits. Prove that the entire
        # removed subgraph drives neither a retained cell nor a top output.
        observed=set(resolve.top_outputs)
        for inst in cells.keys()&exported.keys():
            observed.update(resolve(n) for n in cells[inst][1].values())
        observable_missing=[]
        for inst in missing:
            pins=cells[inst][1];outputs=set(pins)&{'Y','QN','Q','H','L'}
            if len(outputs)!=1:raise ValueError('unknown cell output')
            if resolve(pins[outputs.pop()]) in observed:observable_missing.append(inst)
        row=dict(variant=variant,reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 reference_cells=len(cells),readback_cells=len(exported),missing=missing,extra=extra,differences=diff,
                 removed_subgraph_drives_observable_cells=observable_missing,
                 passed=not(observable_missing or extra or diff));records.append(row)
        print(variant,len(cells),len(exported),'unused removed',len(missing),'differences',len(observable_missing),len(extra),len(diff))
    passed=all(r['passed'] for r in records)
    (args.directory/'connectivity-review.json').write_text(json.dumps(dict(passed=passed,records=records),indent=2)+'\n')
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
