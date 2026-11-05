#!/usr/bin/env python3
"""Archive new A native checkpoints, corner trials, complete scores and sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
BASE = ROOT/'build/experiments/optimization-135-v1'
ATTEMPT = BASE/'attempt-v2'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    state = json.loads((ATTEMPT/'finish-controller.json').read_text())
    if not state['complete']:
        raise ValueError('complete physical, workload and image-restoration controller required')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('preserve existing archive')
    output.mkdir(parents=True)
    selected = {}
    def include(path, member):
        if member in selected or not path.is_file() or path.is_symlink():
            raise ValueError('duplicate/missing/symlink archive input: '+str(path))
        selected[member] = path
    # Completed stage archives contain the original native construction trees.
    # Keep their exact bytes once; STA directories were created later and are added separately.
    for p in sorted(ATTEMPT.iterdir()):
        if p.is_file():
            include(p, 'native/'+p.name)
    for p in sorted(ATTEMPT.rglob('*')):
        if p.is_file() and any(part.startswith('independent-') for part in p.relative_to(ATTEMPT).parts):
            include(p, 'native/'+str(p.relative_to(ATTEMPT)))
    for directory in sorted((BASE/'measurement-source/build').glob('measurement-*')):
        for p in sorted(directory.rglob('*')):
            if p.is_file():
                include(p, 'measurements/'+directory.name+'/'+str(p.relative_to(directory)))
    for p in sorted(BASE.iterdir()):
        if p.is_file() and p.suffix in ('.json', '.py', '.sh', '.log', '.md'):
            include(p, 'review-environment/'+p.name)
    include(BASE/'image-cache/summary.json', 'review-environment/image-cache-summary.json')
    include(BASE/'orfs-image-cache/summary.json', 'review-environment/orfs-image-cache-summary.json')
    include(BASE/'common-clock-evidence.tar.gz', 'review-environment/common-clock-evidence.tar.gz')
    for p in sorted((ROOT/'experiments/optimization-135-v1').iterdir()):
        if p.is_file():
            include(p, 'source/experiments/optimization-135-v1/'+p.name)
    for name in ['review.py', 'review_guard.py', 'analyze_guard.py', 'physical.py', 'repair.py',
                 'ready_guard.tcl', 'ready_guard.mk', 'contract-ready-guard.json', 'contract-hold40.json']:
        include(ROOT/'experiments/lsu-b-validation-v2'/name, 'source/accepted-flow/'+name)
    include(ROOT/'build/experiments/lsu-b-validation-v2/analyze_physical_v2.py',
            'source/accepted-flow/analyze_physical_v2.py')
    experiment = json.loads((ROOT/'experiments/lsu-a-v1/manifest.json').read_text())
    sources = {**experiment['candidate_rtl_files_sha256'], **experiment['simulation_inputs_sha256'],
               **experiment['physical_inputs_sha256']}
    for name, digest in sources.items():
        path = BASE/'measurement-source'/name
        if sha(path) != digest:
            raise ValueError('frozen A source changed')
        include(path, 'source/frozen-A/'+name)
    for name in ['scripts/baseline_contract.py', 'scripts/measure_cpu_experiment.py',
                 'scripts/measure_post_lsu_baseline.py', 'scripts/experiment_provenance.py',
                 'scripts/build_experiment_sim.py', 'scripts/review_cpu_experiment.py',
                 'scripts/check_physical_closure.py', 'scripts/run_physical_job.py',
                 'experiments/lsu-a-v1/manifest.json', 'baselines/ap5b-post-lsu-v1/manifest.json']:
        include(ROOT/name, 'source/current/'+name)
    for p in sorted((ROOT/'baselines/ap5b-post-lsu-v1/fixtures').iterdir()):
        if p.is_file():
            include(p, 'source/current/baselines/ap5b-post-lsu-v1/fixtures/'+p.name)
    rows = []
    whole = BASE/'A-completion.tar.gz'
    if whole.exists():
        raise ValueError('preserve previous assembled bundle')
    with tarfile.open(whole, 'w:gz', compresslevel=6, dereference=True) as tar:
        for member, path in sorted(selected.items()):
            row = dict(source=str(path.relative_to(ROOT)), member=member,
                       bytes=path.stat().st_size, sha256=sha(path))
            tar.add(path, arcname=member, recursive=False)
            if sha(path) != row['sha256']:
                raise ValueError('archive input changed during copy: '+str(path))
            rows.append(row)
    with tarfile.open(whole, 'r:gz') as tar:
        if len(tar.getmembers()) != len(rows):
            raise ValueError('bundle member count differs')
        for row in rows:
            h = hashlib.sha256()
            size = 0
            with tar.extractfile(row['member']) as stream:
                for block in iter(lambda: stream.read(1048576), b''):
                    size += len(block)
                    h.update(block)
            if h.hexdigest() != row['sha256'] or size != row['bytes']:
                raise ValueError('decoded bundle member differs')
    # Keep each Git object below GitHub's large-file warning/limit.
    subprocess.run(['split', '-b', '32M', '-d', '-a', '3', str(whole),
                    str(output/'A-completion.tar.gz.part-')], check=True)
    aggregate = hashlib.sha256()
    parts = []
    for part in sorted(output.glob('*.part-*')):
        with part.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                aggregate.update(block)
        parts.append(dict(path=part.name, bytes=part.stat().st_size, sha256=sha(part)))
    if aggregate.hexdigest() != sha(whole):
        raise ValueError('joined chunk identity differs')
    result = dict(passed=True, scope='new A common-flow research comparison; no CPU architecture/baseline promotion',
                  native_source_commit=json.loads((ATTEMPT/'physical-controller.json').read_text())['source_commit'],
                  archive_parent_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  archive_worktree_status=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True),
                  archive_sha256=sha(whole), archive_bytes=whole.stat().st_size, parts=parts, records=rows,
                  retained_reference='docs/evidence/2026-10-29/lsu-b-complete-validation',
                  retained_reference_inventory_sha256='4a67509515d6c320b633c9f0d2e063c9e85b5697d8ac739637759253ef5e1920')
    (output/'copy-inventory.json').write_text(json.dumps(result, indent=2)+'\n')
    for source, name in [(ATTEMPT/'A-physical-review.json', 'physical-review.json'),
                         (BASE/'measurement-10000ps-review.json', 'common-clock-review.json'),
                         (BASE/f"measurement-{state['fastest_period_ps']}ps-review.json", 'fastest-clock-review.json')]:
        (output/name).write_bytes(source.read_bytes())
    files = sorted(p for p in output.iterdir() if p.is_file())
    (output/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in files))
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    main()
