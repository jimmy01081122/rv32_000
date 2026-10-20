"""Preserve reviewed source, raw checks and before/after admission controls."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil

ROOT=Path('/workspace/rv32_000')
SOURCE=ROOT/'build/experiments/lsu-a-v1/review-v1'
DEST=ROOT/'docs/evidence/2026-10-20/lsu-a-review'
assert not DEST.exists()
DEST.mkdir(parents=True)
records=[]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

def copy(source,target):
    target=DEST/target;target.parent.mkdir(parents=True,exist_ok=True)
    expected=sha(source);shutil.copyfile(source,target)
    assert sha(target)==sha(source)==expected
    records.append({'source':str(source.relative_to(ROOT)),'archive':str(target.relative_to(DEST)),
                    'sha256':expected,'bytes':target.stat().st_size})

for name in ['qualification-clean-v1','admission-controls-v1']:
    for path in sorted((SOURCE/name).rglob('*')):
        if path.is_file() and not path.is_symlink():
            copy(path,Path(name)/path.relative_to(SOURCE/name))
for path in sorted((SOURCE/'unit-35-v1').iterdir()):
    if path.is_file():copy(path,Path('unit-35-v1')/path.name)
copy(SOURCE/'unit-35-v1/baseline-rtl/rv32_ooo_lsu.sv',Path('unit-35-v1/baseline-rtl/rv32_ooo_lsu.sv'))
for mode in ['baseline','candidate']:
    directory=SOURCE/'unit-35-v1'/mode
    copy(directory/'Vlsu_overlap_top__verFiles.dat',Path('unit-35-v1')/mode/'Vlsu_overlap_top__verFiles.dat')
    binary=directory/'lsu_unit';target=DEST/'unit-35-v1'/mode/'lsu_unit.gz'
    with binary.open('rb') as data,target.open('wb') as output:
        with gzip.GzipFile(filename='',fileobj=output,mode='wb',mtime=0) as encoded:shutil.copyfileobj(data,encoded)
    assert hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest()==sha(binary)
    records.append({'source':str(binary.relative_to(ROOT)),'archive':str(target.relative_to(DEST)),
                    'source_sha256':sha(binary),'sha256':sha(target),'gzip_roundtrip_verified':True})
for name in ['admission-controls.py','admission-controls.log','contract-controls-v1.log',
             'review-10000ps-v2.json','review-9900ps-v2.json','review-10000ps-v2.log','review-9900ps-v2.log',
             'unit-35-driver.log','qualification-clean-driver.log','qualification-clean-v2-driver.log',
             'runtime-launch-v1.json','runtime-cleanup.json','source-and-evidence-integrity.json']:
    copy(SOURCE/name,Path('context')/name)
for name in ['Makefile','scripts/review_cpu_experiment.py','scripts/experiment_provenance.py',
             'scripts/test_experiment_provenance.py','scripts/test_cpu_experiment_review.py',
             'scripts/check_lsu_overlap.py','verification/unit/test_lsu_overlap.cpp',
             'verification/unit/lsu_overlap_top.sv','rtl/lsu/rv32_ooo_lsu.sv',
             'rtl/core/rv32_ooo_core.sv','rtl/rob/rv32_ooo_rob.sv','experiments/lsu-a-v1/manifest.json']:
    copy(ROOT/name,Path('inputs')/name)
copy(Path(__file__),Path('archive-review.py'))
(DEST/'copy-inventory.json').write_text(json.dumps({'scope':'Exact copies and lossless unit binaries; symlinked original measurement directories deliberately not duplicated.','records':records},indent=2)+'\n')
(DEST/'.gitattributes').write_text('* -text\n')
print('Review archive prepared:',len(records),'copied artifacts')
