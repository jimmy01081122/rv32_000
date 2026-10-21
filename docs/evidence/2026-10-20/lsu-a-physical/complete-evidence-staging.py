"""Append completed score evidence and promote the archive after clean measurement."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import subprocess

ROOT = Path('/workspace/rv32_000')
EXP = ROOT/'build/experiments/lsu-a-v1'
DEST = EXP/'physical-evidence-staging'
PUBLISHED = ROOT/'docs/evidence/2026-10-20/lsu-a-physical'
records = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

supervisor = json.loads((EXP/'measurement-review-supervisor.json').read_text())
assert supervisor['complete'] and not supervisor.get('error')
worker = json.loads((EXP/'measurement-9900ps-relaunch-v2/run.json').read_text())
assert worker['flow_completed'] and worker['input_identities_unchanged'] and worker['returncode'] == 0
assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
analysis = json.loads((EXP/'operating-point-analysis.json').read_text())
assert len(analysis['operating_points']) == 2

def copy(source, relative):
    target = DEST/relative
    assert not target.exists(), target
    target.parent.mkdir(parents=True,exist_ok=True)
    expected = sha(source)
    shutil.copyfile(source,target)
    assert sha(target) == sha(source) == expected
    records.append({'source':str(source.relative_to(ROOT)),
                    'archive_path':str(target.relative_to(DEST)),
                    'sha256':expected,'bytes':target.stat().st_size})

for directory in ['measurement-9900ps-v1','measurement-9900ps-relaunch-v2']:
    for source in sorted((EXP/directory).rglob('*')):
        if source.is_file():copy(source,Path(directory)/source.relative_to(EXP/directory))
for name in ['review-fastest-v1.json','operating-point-analysis.json','analyze-operating-points.py',
             'finish-measurement-review.py','measurement-review-supervisor.json',
             'measurement-review-1.log','measurement-review-2.log',
             'original-launch-lock-negative.log','original-launch-lock-negative.json',
             'runtime-restart-validation.json','verify-source-lineage.py','source-lineage.json',
             'historical-evidence-integrity.json','write-physical-readme.py',
             'cleanup-completed-runtime.py','runtime-completion-cleanup.json',
             'runtime-cleanup-preflight-v1.json']:
    copy(EXP/name,Path('context')/name)
copy(Path(__file__),Path('complete-evidence-staging.py'))
copy(ROOT/'physical/asap7/toolchain.lock',Path('inputs/physical/asap7/toolchain.lock'))
checkpoint = EXP/'physical-5500ps-synth-clean-v1/results/asap7/rv32_post_lsu_v1/base/1_synth.odb.gz'
copy(checkpoint,Path('physical/physical-5500ps-synth-clean-v1/1_synth.odb.gz'))
decoded = hashlib.sha256()
with gzip.open(checkpoint,'rb') as data:
    for block in iter(lambda:data.read(1024*1024),b''):decoded.update(block)
original = next(x for x in json.loads((EXP/'completed-odb-compression-v2.json').read_text())['records']
                if x['gzip_path'] == str(checkpoint.relative_to(ROOT)))
assert decoded.hexdigest() == original['original_sha256']
records[-1]['decoded_original_sha256'] = decoded.hexdigest()
records[-1]['original_bytes'] = original['original_bytes']
(DEST/'completion-copy-inventory.json').write_text(json.dumps({'scope':'Completed fastest-clock full27 evidence and independent reviews; copied only after clean end and231 unchanged inputs.','records':records},indent=2)+'\n')
assert not PUBLISHED.exists()
PUBLISHED.parent.mkdir(parents=True,exist_ok=True)
shutil.move(str(DEST),str(PUBLISHED))
print('Promoted completed evidence:',PUBLISHED,flush=True)
