#!/usr/bin/env python3
"""Check retained measurements and summarize native top-path reports; no rescore."""
import argparse, collections, hashlib, json, re
from pathlib import Path

MEASUREMENTS = {
    'baseline': 'build/baselines/ap5b-post-lsu-v1/measurement-formal-10000ps',
    'A': 'build/experiments/lsu-a-v1/measurement-10000ps-v1',
    'B': 'build/experiments/lsu-b-validation-v2/measurement-10000ps-v1',
}
MODELS = {'baseline':'build/sim',
    'A':'build/experiments/lsu-a-v1/build-clean-v1/sim-normal',
    'B':'build/experiments/lsu-b-v1/build-clean-v1/sim-normal'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)
def retained(root):
    sources, rows, frozen = {}, [], {}
    for variant, directory in MEASUREMENTS.items():
        base = root/directory; p=base/'summary.json'; d=json.loads(p.read_text());sources[str(p)]=sha(p)
        require(d['passed'] and len(d['records'])==27, 'incomplete source '+variant)
        require(d.get('period_ps',d.get('core_period_ps'))==10000 and d['memory_ps']==10000,'wrong memory/CPU point')
        require(not d.get('preparation_only',False),'preparation data excluded')
        require(sha(root/MODELS[variant]/'rv32_ooo_sim')==d['simulator_sha256'],'changed scored simulator')
        require(collections.Counter(r['family'] for r in d['records'])=={'embench':19,'fp32':8},'wrong families')
        seen=set()
        for r in d['records']:
            key=(r['family'],r['name']);require(key not in seen,'duplicate case');seen.add(key)
            case=base/Path(*key); p=case/'profile.json'; profile=json.loads(p.read_text())
            require(sha(p)==r['profile_sha256'],'profile hash '+str(p));sources[str(p)]=sha(p)
            require(sha(case/'input.elf')==r['elf_sha256'],'ELF changed')
            require(sha(case/'dut.log')==r['execution']['log_sha256'],'log changed')
            require(r['passed'] and profile['cycles']==r['cycles'],'cycle/pass mismatch')
            require(not profile['trace_mismatches'] and not profile['layout_mismatches'],'profile interpretation mismatch')
            require(sum(profile['cycle_partition'].values())==r['cycles'],'invalid cycle partition')
            if variant=='baseline':frozen[key]=r['elf_sha256']
            require(frozen[key]==r['elf_sha256'],'workload changed')
            rows.append(dict(variant=variant,family=key[0],name=key[1],cycles=r['cycles'],
                elf_sha256=r['elf_sha256'],profile_sha256=r['profile_sha256'],
                cycle_partition=profile['cycle_partition'],overlapping_events=profile['overlapping_events'],
                retired_classes=profile['retired_classes']))
        require(set(frozen)==seen,'suite changed')
    return dict(scope='All 81 retained profiles, fixed 10 ns CPU/memory; overlapping events are not saved cycles',
                sources_sha256=sources,records=rows,passed=True)

def parse_paths(text):
    rows=[]
    for block in text.split('Startpoint: ')[1:]:
        group=re.search(r'^Path Group: (\S+)',block,re.M)[1]
        slack=float(re.search(r'([-\d.]+)\s+slack \(',block)[1])
        arrival=float(re.search(r'^\s*([-\d.]+)\s+data arrival time',block,re.M)[1])
        nodes=[]
        for line in block.split('data arrival time')[0].splitlines():
            m=re.match(r'^\s*([-\d.]+)\s+([-\d.]+)\s+[\^v]\s+(\S+)\s+\(([^)]+)\)',line)
            if m:nodes.append(dict(increment_ps=float(m[1]),arrival_ps=float(m[2]),pin=m[3],master=m[4]))
        row=dict(group=group,startpoint=block.splitlines()[0],endpoint=re.search(r'^Endpoint: (.*)',block,re.M)[1],
                 slack_ps=slack,arrival_ps=arrival,nodes=nodes)
        if group=='reg2reg':
            q=next(i for i,n in enumerate(nodes) if n['pin'].endswith(('/Q','/QN')))
            require(nodes[-1]['pin'].endswith('/D'),'unexpected endpoint')
            data=nodes[q+1:-1]
            row.update(q_to_d_ps=round(nodes[-1]['arrival_ps']-nodes[q]['arrival_ps'],2),
                       combinational_output_pins=len(data),
                       buffer_output_pins=sum(n['master'].startswith('BUF') for n in data),
                       within_fp_execute_output_pins=sum(n['pin'].startswith('u_fp_execute/') for n in data))
        rows.append(row)
    require(collections.Counter(r['group'] for r in rows)==dict(in2out=5,in2reg=5,reg2out=5,reg2reg=5),'unexpected path coverage')
    return rows

def paths(root):
    archive=root/'docs/evidence/2026-10-29/lsu-b-complete-validation'
    inventory={r['source']:r for r in json.loads((archive/'copy-inventory.json').read_text())['records']}
    reports=[]
    for variant in ['baseline','B']:
        for corner in ['TT','SS','FF']:
            rel=f'build/experiments/lsu-b-validation-v2/physical-{variant}-v4/guard/independent-boundary-v1/{corner}/setup_paths_10000.rpt'
            p=root/rel;require(sha(p)==inventory[rel]['source_sha256'],'native report archive mismatch')
            rows=parse_paths(p.read_text())
            reports.append(dict(variant=variant,corner=corner,source=rel,sha256=sha(p),paths=rows,
                worst_by_group={g:min((r for r in rows if r['group']==g),key=lambda r:r['slack_ps']) for g in ['in2out','in2reg','reg2out','reg2reg']}))
    return dict(scope='Existing native global-route estimated parasitics, fixed 10 ns; 5 worst paths/group/corner, not exhaustive path enumeration. Pin increments combine cell/net effects; no separate wire-vs-cell claim.',reports=reports,passed=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    for name, fn in [('retained-profiles',retained),('native-paths',paths)]:
        d=fn(a.repo);(a.output/(name+'.json')).write_text(json.dumps(d,indent=2)+'\n');print(name,'PASS')
if __name__=='__main__':main()
