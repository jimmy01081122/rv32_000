#!/usr/bin/env python3
"""Preserve arbitration functional evidence and the identified parent timing reports."""
import argparse,hashlib,json,subprocess,tarfile
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-load-arb-v1'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);out=ap.parse_args().output.resolve()
    require(not out.exists(),'preserve prior archive')
    for name in ['common-clock-review.json','parent-comparison.json','unit-v1/summary.json','parent-timing/summary.json']:
        require(json.loads((BASE/name).read_text())['passed'],'incomplete review: '+name)
    require(json.loads((BASE/'functional-pipeline.json').read_text())['complete'],'pipeline incomplete')
    paths=set()
    def add_tree(root):
        paths.update(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ['unit-dev-v1','unit-v1','build-v1','qualification-v1','measurement-10000ps-v1','parent-timing']:add_tree(BASE/name)
    for p in BASE.iterdir():
        if p.is_file() and p.suffix in ['.json','.log','.py']:paths.add(p)
    parent=ROOT/'build/experiments/lsu-ab-v1'
    for name in ['build-v1','qualification-v1','measurement-10000ps-v1']:add_tree(parent/name)
    paths.update([parent/'common-clock-review.json',parent/'physical-review.json'])
    for root in [ROOT/'scripts',ROOT/'experiments/lsu-load-arb-v1',ROOT/'baselines/ap5b-post-lsu-v1',
                 ROOT/'build/tests',ROOT/'build/baselines/ap5b-post-lsu-v1/measurement-formal-10000ps']:add_tree(root)
    paths.update([ROOT/'experiments/lsu-ab-v1/manifest.json',ROOT/'experiments/lsu-ab-v1/review_measurement.py',
                  ROOT/'verification/unit/lsu_marking_top.sv',ROOT/'verification/unit/test_lsu_ab.cpp',ROOT/'verification/unit/test_lsu_arbitration.cpp'])
    manifest=json.loads((ROOT/'experiments/lsu-load-arb-v1/manifest.json').read_text())
    for name,h in {**manifest['candidate_rtl_files_sha256'],**manifest['simulation_inputs_sha256'],**manifest['physical_inputs_sha256']}.items():
        require(sha(ROOT/name)==h,'experiment source changed: '+name);paths.add(ROOT/name)
    rows=[]
    for p in sorted(paths):
        require(not p.is_symlink(),'unexpected source symlink')
        rows.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
    out.mkdir(parents=True);archive=out/'arbitration-functional.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
        for row in rows:tar.add(ROOT/row['path'],arcname=row['path'],recursive=False)
    require(archive.stat().st_size<100*1024**2,'use split publication for larger evidence')
    require(all(sha(ROOT/r['path'])==r['sha256'] for r in rows),'evidence changed while archiving')
    inventory=dict(passed=True,scope='arbitration functional/common-clock results; timing reports describe the A+B parent only',
                   archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),
                   archive_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   functional_source_commit=json.loads((BASE/'build-v1/summary.json').read_text())['start']['commit'],records=rows)
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for name in ['common-clock-review.json','parent-comparison.json']:(out/name).write_bytes((BASE/name).read_bytes())
    (out/'parent-critical-paths.json').write_bytes((BASE/'parent-timing/summary.json').read_bytes())
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k:v for k,v in inventory.items() if k!='records'},indent=2))
if __name__=='__main__':main()
