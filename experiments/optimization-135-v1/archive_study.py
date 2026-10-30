#!/usr/bin/env python3
"""Preserve source-bound diagnostic results and their exact input bytes."""
import argparse,gzip,hashlib,json,os
from pathlib import Path
from analyze_retained import MEASUREMENTS,require,sha
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--working',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    require(not a.output.exists(),'fresh archive required');a.output.mkdir(parents=True);rows=[]
    def copy(src,destination):
        raw=src.read_bytes();binary=src.suffix in ['.o','.a','.elf'] or src.name in ['observer','test_observer_adapter_final']
        data=gzip.compress(raw,mtime=0) if binary else raw
        target=a.output/(destination+('.gz' if binary else ''));target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        rows.append(dict(source=str(src),destination=str(target.relative_to(a.output)),encoding='gzip' if binary else 'copy',
            source_sha256=hashlib.sha256(raw).hexdigest(),stored_sha256=sha(target),source_bytes=len(raw),stored_bytes=len(data)))
    for tree in ['analysis-v1','observer-v1','observer-v2','controls-v1']:
        for p in sorted((a.working/tree).rglob('*')):
            if p.is_file():copy(p,'runs/'+str(p.relative_to(a.working)))
    for name in ['study-review.json','A-preflight.json','prior-B-archive-check.json','adapter-controls.log','adapter-controls.json','observer-v1.log','observer-v2.log','test_observer_adapter_final']:
        copy(a.working/name,'runs/'+name)
    copy(a.working/'run_observer.py','source/observer-controller-v1.py')
    for p in sorted(HERE.iterdir()):
        if p.is_file():copy(p,'source/'+p.name)
    # Full frozen reference logs/profiles and ELFs are retained, not replaced by
    # the nine-case observer subset. This is still not a fresh full-suite run.
    for variant,directory in MEASUREMENTS.items():
        base=ROOT/directory;copy(base/'summary.json','references/'+variant+'/summary.json')
        for r in json.loads((base/'summary.json').read_text())['records']:
            for name in ['input.elf','dut.log','profile.json','memory.json']:
                copy(base/r['family']/r['name']/name,'references/'+variant+'/'+r['family']+'/'+r['name']+'/'+name)
    inputs={}
    for variant,run in [('baseline','observer-v2'),('A','observer-v2'),('B','observer-v1')]:
        d=json.loads((a.working/run/variant/'build.json').read_text())
        for p,h in d['inputs_sha256'].items():
            require(sha(Path(p))==h,'changed observer source input');inputs[p]=h
    # Content-identical inputs are stored once; retain all original path aliases.
    seen={}
    for path,h in sorted(inputs.items()):
        if h not in seen:
            seen[h]='inputs/'+h[:16]+'/'+Path(path).name;copy(Path(path),seen[h])
    (a.output/'input-aliases.json').write_text(json.dumps({p:seen[h] for p,h in inputs.items()},indent=2)+'\n')
    for name in ['completed-checkpoint-compaction.json','completed-guide-compaction.json']:
        copy(ROOT/'build/experiments/optimization-135-v1'/name,'environment/'+name)
    data=dict(scope='1/3/5 first study; diagnostic source snapshots, all retained references, actual observer runs and failed path-comparison attempt. A native physical run remains outstanding.',records=rows)
    (a.output/'copy-inventory.json').write_text(json.dumps(data,indent=2)+'\n')
    print('archived',len(rows),'files')
if __name__=='__main__':main()
