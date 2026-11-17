#!/usr/bin/env python3
"""Publish the complete ROB-space functional experiment, retaining failed attempts."""
import argparse,gzip,hashlib,json,subprocess,sys,tarfile
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
BASE=ROOT/'build/experiments/lsu-rob-room-v1'
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
def require(ok,msg):
    if not ok:raise ValueError(msg)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);out=ap.parse_args().output.resolve();require(not out.exists(),'fresh archive directory required')
    for n in ['unit-v2/summary.json','admission-controls.json','common-clock-review.json','parent-comparison.json','resume-verification.json']:require(json.loads((BASE/n).read_text())['passed'],'incomplete gate: '+n)
    pipeline=json.loads((BASE/'functional-pipeline.json').read_text());require(pipeline['complete'] and pipeline['start']==pipeline['end'] and not pipeline['start']['status'],'incomplete clean functional pipeline')
    paths=set()
    def tree(p):paths.update(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
    for n in ['unit-v1','unit-v2','build-v1','qualification-v1','measurement-10000ps-v1']:tree(BASE/n)
    for n in ['rtl-review.json','resume-verification.json','parent-comparison-resume.json','admission-controls.json','contract-controls.log','provenance-controls.log','functional-pipeline.json','build-driver.log','qualification-driver.log','measurement-driver.log','review-driver.log','comparison-driver.log','common-clock-review.json','parent-comparison.json']:paths.add(BASE/n)
    for p in [ROOT/'scripts',ROOT/'experiments/lsu-rob-room-v1',ROOT/'baselines/ap5b-post-lsu-v1',ROOT/'build/tests']:tree(p)
    for n in ['lsu_rob_room_top.sv','test_lsu_rob_room.cpp','test_lsu_arbitration.cpp','test_lsu_ab.cpp','lsu_marking_top.sv','lsu_overlap_top.sv','tb_lsu_ap5b.sv']:paths.add(ROOT/'verification/unit'/n)
    for n in ['lsu-ab-v1','lsu-load-arb-v1']:
        for f in ['manifest.json','review_measurement.py']:paths.add(ROOT/'experiments'/n/f)
    paths.add(ROOT/'docs/LSU_ROB_ROOM_REVIEW.md')
    paths.add(ROOT/'docs/evidence/2026-11-16/lsu-arbitration-functional/inventory.json')
    contract=json.loads((ROOT/'experiments/lsu-rob-room-v1/manifest.json').read_text())
    for n,h in {**contract['candidate_rtl_files_sha256'],**contract['simulation_inputs_sha256'],**contract['physical_inputs_sha256']}.items():
        require(sha(ROOT/n)==h,'frozen experiment source changed');paths.add(ROOT/n)
    records=[]
    for p in sorted(paths):
        require(p.is_file() and not p.is_symlink(),'invalid payload');records.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
    out.mkdir(parents=True);archive=out/'rob-room-functional.tar.gz'
    with archive.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w|') as tar:
            for r in records:
                p=ROOT/r['path'];info=tar.gettarinfo(str(p),arcname=r['path']);info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname=''
                with p.open('rb') as src:tar.addfile(info,src)
    require(archive.stat().st_size<100*1024**2,'split large publication before committing')
    require(all(sha(ROOT/r['path'])==r['sha256'] for r in records),'archive inputs changed')
    inv=dict(passed=True,scope='Complete ROB-space functional/all27 experiment; no new physical timing or area qualification',archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),functional_source_commit=pipeline['start']['commit'],publication_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),records=records)
    (out/'inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
    for n in ['common-clock-review.json','parent-comparison.json']:(out/n).write_bytes((BASE/n).read_bytes())
    (out/'README.md').write_text('''# ROB-space arbitration functional evidence

The candidate requires at least two free ROB slots for a new first-head load
bypass. Held loads retain ownership under backpressure. Original baseline,
frozen ELF bytes, memory times, two-family scores and targets are unchanged.

This archive includes both unit attempts (the first failed filename/module-name
lint), the repaired checker and actual parent/candidate/mutant models, clean
normal/assert core builds, complete qualification, all 27 workload logs/profiles/
memory audits/ELFs, independent reviews and the five-stage pipeline receipts.
It does not qualify new physical timing or area.

See [results and limits](../../../LSU_ROB_ROOM_REVIEW.md) and
[the experiment contract](../../../../experiments/lsu-rob-room-v1/README.md).
Original A+B, arbitration-v1 and baseline reference files are reused from
[the prior functional archive](../../2026-11-16/lsu-arbitration-functional/README.md).
Restore those earlier inputs before replaying the independent full comparison.
Their published inventory is retained here; reference measurements are not relabeled.

Verify public files and every decoded member without extracting:

```sh
python3 experiments/lsu-load-arb-v1/verify_archive.py <this-directory>
```

Only extract verified evidence into a fresh review checkout. All members use
repository-relative paths; prior execution commands retain their original paths.
'''.replace('<this-directory>',str(out.relative_to(ROOT))))
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k:v for k,v in inv.items() if k!='records'},indent=2))
if __name__=='__main__':main()
