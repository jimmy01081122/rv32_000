"""Copy completed evidence only; never edit active measurement or original bytes."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil

ROOT = Path('/workspace/rv32_000')
SOURCE = ROOT/'build/experiments/lsu-a-v1'
DEST = SOURCE/'physical-evidence-staging'
DEST.mkdir(exist_ok=False)
records = []

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()

def copy(source, target, compress=False):
    target = DEST/target
    target.parent.mkdir(parents=True, exist_ok=True)
    original_sha = digest(source)
    if compress:
        with source.open('rb') as data, target.open('wb') as output:
            with gzip.GzipFile(filename='', fileobj=output, mode='wb', mtime=0) as encoded:
                shutil.copyfileobj(data, encoded)
        decoded = hashlib.sha256()
        with gzip.open(target, 'rb') as data:
            for block in iter(lambda: data.read(1024*1024), b''):
                decoded.update(block)
        assert decoded.hexdigest() == original_sha
    else:
        shutil.copyfile(source, target)
        assert digest(target) == original_sha
    assert digest(source) == original_sha
    records.append({'source':str(source.relative_to(ROOT)),
                    'archive_path':str(target.relative_to(DEST)),
                    'source_sha256':original_sha,
                    'archive_sha256':digest(target),
                    'source_bytes':source.stat().st_size,
                    'archive_bytes':target.stat().st_size,
                    'gzip_roundtrip_verified':compress})

for name in ['physical-5500ps-synth-clean-v1', 'physical-14000ps-backend-clean-v1',
             'physical-14000ps-eco-clean-v1']:
    attempt = SOURCE/name
    report = json.loads((attempt/'run.json').read_text())
    assert report['flow_completed'] and report['returncode'] == 0
    assert report['input_identities_unchanged']
    for path in sorted(attempt.rglob('*')):
        if not path.is_file() or 'results' in path.relative_to(attempt).parts:
            continue
        copy(path, Path('physical')/name/path.relative_to(attempt))
    result = attempt/'results/asap7/rv32_post_lsu_v1/base'
    selected = ['1_2_yosys.v', '1_2_yosys.sdc', '1_synth.sdc'] if 'synth-clean' in name else ['5_1_grt.odb', '5_1_grt.sdc', 'route.guide']
    for name2 in selected:
        copy(result/name2, Path('physical')/name/(name2+'.gz'), True)

for name in ['physical-pipeline.py','physical-pipeline.json','physical-resources.jsonl',
             'resource-sampler.py','runtime-transition.json','transition-to-physical.py',
             'completed-odb-compression-v2.json','completed-odb-compression-v3.json',
             'baseline-storage-compression.json','vfs-readonly-diagnosis.json',
             'vfs-owned-failure-cleanup.json','vfs-old-unreferenced-cleanup.json',
             'lowering-v1-driver.log','lowering-v2-driver.log','rtl_lowered.lowering.json',
             'rtl_lowered.lowering.log','operating-point-controls.log',
             'per-pc-work-analysis.py','per-pc-work-identity.json',
             'review-common-clock-v1.json','measurement-9900ps-job.json',
             'measurement-9900ps-run.json','job.lock']:
    copy(SOURCE/name, Path('context')/name)
for name in ['backend-launch-driver.log','eco-launch-driver.log','initial-14000ps-driver.log',
             'initial-14000ps-review-driver.log','boundary-v1-driver.log','boundary-v1-review-driver.log']:
    copy(SOURCE/name, Path('context')/name)
copy(SOURCE/'rtl_lowered.v', Path('physical/rtl_lowered.v.gz'), True)
for name in ['Makefile','scripts/review_cpu_experiment.py','scripts/test_cpu_experiment_review.py',
             'scripts/run_physical_job.py','scripts/run_baseline_physical.py',
             'scripts/analyze_baseline_physical.py','scripts/check_physical_closure.py',
             'scripts/measure_cpu_experiment.py','scripts/lower_baseline_rtl.py',
             'experiments/lsu-a-v1/manifest.json','experiments/lsu-a-v1/baseline-inputs.json',
             'toolchain.lock']:
    copy(ROOT/name, Path('inputs')/name)
for path in sorted((ROOT/'physical/asap7/baseline').rglob('*')):
    if path.is_file(): copy(path, Path('inputs')/path.relative_to(ROOT))
copy(ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt',
     Path('inputs/physical-tool-platform-sha256.txt'))
inventory={'scope':'Completed physical evidence; raw source bytes unchanged. Gzip files decoded and hashed before acceptance.',
           'script_sha256':digest(Path(__file__)), 'records':records}
(DEST/'copy-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
shutil.copyfile(Path(__file__), DEST/'gather-physical-evidence.py')
print('Copied',len(records),'files;',sum(x['archive_bytes'] for x in records),'bytes; all original/gzip identities verified',flush=True)
