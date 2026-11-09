#!/usr/bin/env python3
"""Preserve and independently hash-check AB functional and divider evidence."""
import argparse,hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    if out.exists():raise ValueError('fresh evidence output required')
    ab=ROOT/'build/experiments/lsu-ab-v1';div=ROOT/'build/experiments/divider-diagnosis-v1'
    required=[ab/'common-clock-review.json',ab/'parent-comparison.json',div/'diagnostic-review.json']
    if not all(json.loads(p.read_text())['passed'] for p in required):raise ValueError('complete reviewed results required')
    roots=[ab/n for n in ['unit-v1','unit-v2','unit-v3','build-v1','qualification-v1','measurement-10000ps-v1','failure-snapshots']]
    roots += [div,ROOT/'build/tests',ROOT/'build/baselines/ap5b-post-lsu-v1/measurement-formal-10000ps',
              ROOT/'build/experiments/lsu-b-validation-v2/measurement-10000ps-v1',
              ROOT/'build/experiments/optimization-135-v1/measurement-source/build/measurement-10000ps-v1']
    files={p for tree in roots for p in tree.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(p for p in ab.iterdir() if p.is_file() and (p.suffix in ('.json','.log','.v') or p.name.endswith('.lowering.json')))
    build=json.loads((ab/'build-v1/summary.json').read_text())
    files.update(ROOT/n for n in build['source_sha256'])
    files.update(ROOT/n for n in ['experiments/lsu-ab-v1/manifest.json','baselines/ap5b-post-lsu-v1/manifest.json',
                                 'verification/unit/lsu_marking_top.sv','verification/unit/test_lsu_ab.cpp'])
    files.update((ROOT/'scripts').glob('*.py'))
    files.update((ROOT/'experiments/divider-diagnosis-v1').glob('*.*'))
    # Exact observer compilation inputs include the retained B model/runtime.
    observer=json.loads((div/'observer-v1/B/build.json').read_text())
    for name in observer['inputs_sha256']:
        f=Path(name);files.add(f if f.is_relative_to(ROOT) else ROOT/f.relative_to('/workspace'))
    files.add(ROOT/'build/experiments/lsu-b-v1/build-clean-v1/sim-normal/rv32_ooo_sim')
    rows=[]
    for f in sorted(files):
        if f.is_symlink() or not f.is_file():raise ValueError('unexpected evidence source type: '+str(f))
        rows.append(dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=sha(f)))
    out.mkdir(parents=True);archive=out/'functional-evidence.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
        for r in rows:tar.add(ROOT/r['path'],arcname=r['path'],recursive=False)
    seen=set()
    with tarfile.open(archive,'r|gz') as tar:
        expected={r['path']:r for r in rows}
        for m in tar:
            if m.name in seen or m.name not in expected or not m.isfile():raise ValueError('archive member mismatch')
            seen.add(m.name);r=expected[m.name];h=hashlib.sha256();stream=tar.extractfile(m)
            for b in iter(lambda:stream.read(1048576),b''):h.update(b)
            if m.size!=r['bytes'] or h.hexdigest()!=r['sha256']:raise ValueError('archive bytes mismatch')
    if len(seen)!=len(rows) or any(sha(ROOT/r['path'])!=r['sha256'] for r in rows):raise ValueError('evidence changed during archive')
    inventory=dict(passed=True,scope='AB functional/common-clock and read-only B divider study; no AB physical qualification',
        archive=archive.name,archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,decoded_members=len(rows),records=rows)
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for src,name in [(required[0],'common-clock-review.json'),(required[1],'parent-comparison.json'),
                     (required[2],'divider-diagnosis.json')]: (out/name).write_bytes(src.read_bytes())
    (out/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
    print('functional archive verified',len(rows),archive.stat().st_size,inventory['archive_sha256'])
if __name__=='__main__':main()
