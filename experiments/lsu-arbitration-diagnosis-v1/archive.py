#!/usr/bin/env python3
"""Create/verify split evidence with every source and decoded member hashed."""
import argparse,gzip,hashlib,json,shutil,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath
from run_observer import ROOT,HERE,CASES,EXPERIMENTS,require,sha,save
BASE=ROOT/'build/experiments/lsu-arbitration-diagnosis-v1'
def digest(stream):
    h=hashlib.sha256()
    for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def create(out):
    require(not out.exists(),'fresh publication directory required')
    for p in [BASE/'capture-v1/summary.json',BASE/'review-v1/summary.json',BASE/'schedule-comparison-v1.json']:require(json.loads(p.read_text())['passed'],'incomplete evidence')
    paths=set()
    for directory in [BASE/'capture-v1',BASE/'review-v1',BASE/'disassembly',HERE]:
        paths.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.add(BASE/'schedule-comparison-v1.json');paths.add(ROOT/'docs/LSU_ARBITRATION_DIAGNOSIS.md')
    for experiment in EXPERIMENTS.values():
        for family,name in CASES:
            paths.update((ROOT/'build/experiments'/experiment/'measurement-10000ps-v1'/family/name).glob('*'))
    calibration=ROOT/'build/experiments/lsu-ab-v1/pid-waveform-review-v2/AB/roi-signals.json.gz';paths.add(calibration)
    references=[ROOT/'docs/evidence/2026-11-16/lsu-arbitration-functional/inventory.json',ROOT/'docs/evidence/2026-11-13/lsu-ab-complete/copy-inventory.json']
    paths.update(references)
    inventory=[]
    for p in sorted(paths):
        require(p.is_file() and not p.is_symlink(),'invalid payload')
        inventory.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
    out.mkdir(parents=True)
    with tempfile.TemporaryFile() as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                for r in inventory:
                    p=ROOT/r['path'];info=tar.gettarinfo(str(p),arcname=r['path']);info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname=''
                    with p.open('rb') as src:tar.addfile(info,src)
        raw.seek(0);archive_sha=digest(raw);raw.seek(0);parts=[]
        while data:=raw.read(40*1024**2):
            p=out/f'arbitration-diagnosis.tar.gz.part{len(parts):02d}';p.write_bytes(data);parts.append(dict(name=p.name,bytes=len(data),sha256=sha(p)))
    require(all(sha(ROOT/r['path'])==r['sha256'] for r in inventory),'evidence changed during publication')
    save(out/'inventory.json',dict(passed=True,scope='Read-only three-case arbitration diagnosis; original RTL models in linked prior archive; no new CPU score/PPA',archive_sha256=archive_sha,archive_bytes=sum(p['bytes'] for p in parts),parts=parts,records=inventory,publication_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    for src,name in [(BASE/'schedule-comparison-v1.json','schedule-comparison.json'),(BASE/'review-v1/summary.json','review-summary.json'),(BASE/'capture-v1/summary.json','capture-summary.json')]:shutil.copyfile(src,out/name)
    (out/'README.md').write_text('''# Arbitration diagnosis evidence — 2026-11-16

Read-only PID / FFT / statemate comparison between frozen A+B and arbitration v1.
Six observer on/off pairs, all 5,504,081 raw ROI cycles, per-PC/ordered retirement,
load lifecycles, paired store delays, independent VCD calibration and two actual-data
negative controls pass. This is not a new CPU candidate, full-family score or PPA.

See [findings and next proposal](../../../LSU_ARBITRATION_DIAGNOSIS.md).
`capture-summary.json`, `review-summary.json` and `schedule-comparison.json` are
convenience copies; inventory hashes bind the original controller outputs too.
All part files are at most 40 MiB. Verify from the repository root:

```sh
python3 experiments/lsu-arbitration-diagnosis-v1/archive.py --verify \\
  --output docs/evidence/2026-11-16/lsu-arbitration-diagnosis
```

Only extract into a fresh review checkout after verification:

```sh
cat docs/evidence/2026-11-16/lsu-arbitration-diagnosis/arbitration-diagnosis.tar.gz.part* | tar -xz
```

The archive includes every compressed raw stream, unchanged off/on logs/profiles/
memory audits, relinked observer binaries/objects/sources, disassembly with tool
identity, selected frozen reference ELFs/results, the independent PID VCD extraction,
reviewers and schema. No raw stream is downsampled. Original generated RTL models
and runtime objects are reused from the preceding
[functional evidence](../lsu-arbitration-functional/README.md); full original VCD
provenance remains in [A+B evidence](../lsu-ab-complete/README.md) (dated November 13).
Restore those referenced inputs before rebuilding an observer. Review receipts use
absolute original build paths; source hashes and archive member paths are portable.
'''.replace('../lsu-ab-complete/README.md','../../2026-11-13/lsu-ab-complete/README.md'))
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
def verify(out):
    sums={}
    for line in (out/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1);require(Path(n).name==n and n not in sums,'invalid public name');sums[n]=h
    require(set(sums)=={p.name for p in out.iterdir() if p.name!='SHA256SUMS'},'public file set differs')
    for n,h in sums.items():require(not (out/n).is_symlink() and sha(out/n)==h,'public checksum mismatch')
    inv=json.loads((out/'inventory.json').read_text());require(inv['passed'],'unadmitted archive');expected={r['path']:r for r in inv['records']};require(len(expected)==len(inv['records']),'duplicate member');seen=set();size=0
    with tempfile.TemporaryFile() as raw:
        for p in inv['parts']:
            require(p['name'] in sums and sums[p['name']]==p['sha256'] and (out/p['name']).stat().st_size==p['bytes'],'part identity differs')
            with (out/p['name']).open('rb') as src:shutil.copyfileobj(src,raw)
        require(raw.tell()==inv['archive_bytes'],'archive size differs');raw.seek(0);require(digest(raw)==inv['archive_sha256'],'archive hash differs');raw.seek(0)
        with tarfile.open(fileobj=raw,mode='r|gz') as tar:
            for m in tar:
                p=PurePosixPath(m.name);require(not p.is_absolute() and '..' not in p.parts and m.isfile() and m.name in expected and m.name not in seen,'unexpected member')
                r=expected[m.name];require(m.size==r['bytes'],'member size differs')
                with tar.extractfile(m) as src:require(digest(src)==r['sha256'],'member hash differs')
                seen.add(m.name);size+=m.size
    require(seen==set(expected),'missing members')
    return dict(passed=True,members=len(seen),decoded_bytes=size,archive_bytes=inv['archive_bytes'],archive_sha256=inv['archive_sha256'])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    if not a.verify:create(a.output.resolve())
    print(json.dumps(verify(a.output.resolve()),indent=2))
if __name__=='__main__':main()
