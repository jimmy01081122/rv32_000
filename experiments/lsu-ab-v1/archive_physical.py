#!/usr/bin/env python3
"""Archive AB mapping, native stages, independent timing and complete scores."""
import argparse,hashlib,json,subprocess,sys,tarfile
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    review=json.loads((BASE/'complete-review.json').read_text())
    require(review['passed'],'complete physical/workload review required')
    require(json.loads((BASE/'environment-restoration.json').read_text())['passed'],'restore temporary environment before archive')
    require(not out.exists(),'preserve previous archive');out.mkdir(parents=True)
    selected={}
    def include(path):
        require(path.is_file() and not path.is_symlink(),'missing/nonregular evidence: '+str(path))
        member=str(path.relative_to(ROOT));selected[member]=path
    for directory in [BASE/'checkpoints',BASE/'mapping-v1',BASE/'shared-linked-v1']:
        for path in sorted(directory.rglob('*')):
            if path.is_file():include(path)
    for path in sorted((BASE/'native').iterdir()):
        if path.is_file():include(path)
    for path in sorted((BASE/'native').rglob('*')):
        if path.is_file() and any(p.startswith('independent-') for p in path.relative_to(BASE/'native').parts):include(path)
    for directory in sorted(BASE.glob('measurement-*ps-v1')):
        for path in sorted(directory.rglob('*')):
            if path.is_file():include(path)
    for name in ['rtl_lowered.v','rtl_lowered.lowering.json','complete-review.json','physical-review.json',
                 'formal-link-preflight.json','physical-recovery-review.json','native-restart-visibility-v3.json','physical-path-summary.json','common-clock-review.json','common-clock-recovery-review.json',
                 'parent-comparison.json','regression-attribution-v1.json','remaining-bottlenecks-v1.json','pid-mechanism-review.json','physical-driver.json',
                 'physical-driver-launch.json','physical-driver-console.log','physical-native.log',
                 'physical-publication.log','physical-parent-sta.log','physical-guard-sta.log','physical-review.log',
                 'environment-restoration.json','private-runtime-pruning.json','historical-native-compaction.json',
                 'temporary-sparse.json','link-recovery.json','native-runtime-v2.json','cache-deduplication.json']:
        include(BASE/name)
    # Selected raw signals cover every PID ROI cycle. Full-program VCD files
    # contain mostly non-ROI initialization/output and remain local reproducible artifacts.
    for directory in [BASE/'pid-waveforms-v1',BASE/'pid-waveform-review-v2']:
        for path in sorted(directory.rglob('*')):
            if path.is_file() and path.name!='wave.vcd.gz':include(path)
    capture=json.loads((BASE/'pid-waveforms-v1/summary.json').read_text())
    for record in capture['records']:
        binary=Path(record['command'][0]);require(sha(binary)==record['simulator_sha256'],'captured model changed')
        # Retain the exact A and AB executables and generated normal models for replay.
        for path in sorted(binary.parent.rglob('*')):
            if path.is_file():include(path)
    include(BASE/'image-cache-v2/summary.json')
    for path in sorted(BASE.glob('restore-*.log')):include(path)
    for path in sorted(BASE.glob('environment-restoration-*.json')):include(path)
    for path in sorted(BASE.glob('environment-restoration-*.log')):include(path)
    for path in sorted(BASE.glob('fastest-*.json')):include(path)
    for path in sorted(BASE.glob('fastest-*.log')):include(path)
    for directory in [ROOT/'experiments/lsu-ab-v1',ROOT/'scripts',ROOT/'physical/asap7/baseline',ROOT/'baselines/ap5b-post-lsu-v1']:
        for path in sorted(directory.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:include(path)
    for name in ['checkpoint.py','review_physical_A.py']:
        include(ROOT/'experiments/optimization-135-v1'/name)
    for name in ['review.py','review_guard.py','analyze_guard.py','physical.py','repair.py','ready_guard.tcl','ready_guard.mk','contract-ready-guard.json','contract-hold40.json']:
        include(ROOT/'experiments/lsu-b-validation-v2'/name)
    include(ROOT/'build/experiments/lsu-b-validation-v2/analyze_physical_v2.py')
    manifest=json.loads((ROOT/'experiments/lsu-ab-v1/manifest.json').read_text())
    for name,digest in {**manifest['candidate_rtl_files_sha256'],**manifest['simulation_inputs_sha256'],**manifest['physical_inputs_sha256']}.items():
        path=ROOT/name;require(sha(path)==digest,'experiment source changed: '+name);include(path)
    functional=ROOT/'docs/evidence/2026-11-09/lsu-ab-functional'
    for path in sorted(functional.iterdir()):
        if path.is_file():include(path)
    whole=BASE/'AB-physical-completion.tar.gz';require(not whole.exists(),'preserve previous assembled archive');rows=[]
    with tarfile.open(whole,'w:gz',compresslevel=6,dereference=True) as tar:
        for member,path in sorted(selected.items()):
            row=dict(source=member,member=member,bytes=path.stat().st_size,sha256=sha(path))
            tar.add(path,arcname=member,recursive=False)
            require(sha(path)==row['sha256'],'input changed while archiving: '+member);rows.append(row)
    with tarfile.open(whole,'r:gz') as tar:
        require(len(tar.getmembers())==len(rows),'archive member count differs')
        for row in rows:
            h=hashlib.sha256();size=0
            with tar.extractfile(row['member']) as stream:
                for block in iter(lambda:stream.read(1048576),b''):h.update(block);size+=len(block)
            require(h.hexdigest()==row['sha256'] and size==row['bytes'],'decoded archive member differs')
    subprocess.run(['split','-b','32M','-d','-a','3',str(whole),str(out/'AB-completion.tar.gz.part-')],check=True)
    parts=[];aggregate=hashlib.sha256()
    for path in sorted(out.glob('*.part-*')):
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1048576),b''):aggregate.update(block)
        parts.append(dict(path=path.name,bytes=path.stat().st_size,sha256=sha(path)))
    require(aggregate.hexdigest()==sha(whole),'split archive identity differs')
    inventory=dict(passed=True,scope='AB complete global-route research experiment; original baseline unchanged',
                   archive_sha256=sha(whole),archive_bytes=whole.stat().st_size,parts=parts,records=rows,
                   archive_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                   native_source_commit=json.loads((BASE/'native/physical-controller.json').read_text())['source_commit'],
                   functional_source_commit='3f079c1c3d7b53c50beb13bc2d8bf366ac42999f',
                   retained_shared_FPU_proof='docs/evidence/2026-10-29/lsu-b-complete-validation',
                   retained_reference_inventory_sha256='4a67509515d6c320b633c9f0d2e063c9e85b5697d8ac739637759253ef5e1920')
    (out/'copy-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for name in ['complete-review.json','physical-review.json','regression-attribution-v1.json','pid-mechanism-review.json','remaining-bottlenecks-v1.json','environment-restoration.json']:
        (out/name).write_bytes((BASE/name).read_bytes())
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k:v for k,v in inventory.items() if k!='records'},indent=2))
if __name__=='__main__':main()
