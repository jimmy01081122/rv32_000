#!/usr/bin/env python3
"""Archive the complete ROB-space physical experiment and its restored environment."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE = ROOT/'build/experiments/lsu-rob-room-v1'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch-directory', type=Path, default=BASE,
                        help='Directory for assembling the archive before splitting it.')
    args = parser.parse_args()
    out = args.output.resolve()
    for name in ['complete-review.json','environment-restoration.json','physical-path-summary.json']:
        require(json.loads((BASE/name).read_text())['passed'], 'incomplete review: '+name)
    require(not out.exists(), 'preserve previous public evidence')
    selected = set()
    def include(path):
        require(path.is_file() and not path.is_symlink(), 'missing/nonregular evidence: '+str(path))
        selected.add(path)
    def tree(directory):
        require(directory.is_dir(), 'missing evidence directory: '+str(directory))
        for path in sorted(directory.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                include(path)
    for name in ['checkpoints','mapping-v1','shared-linked-v1','interrupted-parent-sta-v1','targeted-probe-attempt-1']:
        tree(BASE/name)
    for path in sorted((BASE/'native').iterdir()):
        if path.is_file():
            include(path)
    for path in sorted((BASE/'native').rglob('*')):
        if path.is_file() and any(p.startswith('independent-') for p in path.relative_to(BASE/'native').parts):
            include(path)
    for directory in sorted(BASE.glob('measurement-*ps-v1')):
        tree(directory)
    include(BASE/'probe_rob_count.tcl')
    include(ROOT/'docs/LSU_ROB_ROOM_PHYSICAL.md')
    for path in sorted(BASE.iterdir()):
        if path.name in ('format_physical.py','update_docs.py','archive-adjusted.py'):
            continue
        if path.is_file() and path.suffix in ('.json','.log','.py','.v'):
            include(path)
    for directory in ['experiments/lsu-rob-room-v1','scripts','physical/asap7/baseline',
                      'physical/asap7/fpu-isolated','baselines/ap5b-post-lsu-v1',
                      'docs/evidence/2026-11-18/lsu-rob-room-functional']:
        tree(ROOT/directory)
    for name in ['checkpoint.py','review_physical_A.py']:
        include(ROOT/'experiments/optimization-135-v1'/name)
    for name in ['review.py','review_guard.py','analyze_guard.py','physical.py','repair.py',
                 'ready_guard.tcl','ready_guard.mk','contract-ready-guard.json','contract-hold40.json']:
        include(ROOT/'experiments/lsu-b-validation-v2'/name)
    for name in ['run_synthesis.py','link_shared.py','compare_mapped.py']:
        include(ROOT/'experiments/fpu-mapping-v1'/name)
    include(ROOT/'build/experiments/lsu-b-validation-v2/analyze_physical_v2.py')
    include(ROOT/'docs/evidence/2026-11-13/lsu-ab-complete/copy-inventory.json')
    include(ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt')
    contract = json.loads((ROOT/'experiments/lsu-rob-room-v1/manifest.json').read_text())
    for name, digest in {**contract['candidate_rtl_files_sha256'], **contract['simulation_inputs_sha256'],
                         **contract['physical_inputs_sha256']}.items():
        require(sha(ROOT/name) == digest, 'frozen experiment source changed')
        include(ROOT/name)
    whole = args.scratch_directory.resolve()/'ROOM-physical-completion.tar.gz'
    require(not whole.exists(), 'preserve earlier assembled archive')
    records = []
    with whole.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', compresslevel=6, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w|') as tar:
            for path in sorted(selected):
                member = str(path.relative_to(ROOT))
                row = dict(source=member, member=member, bytes=path.stat().st_size, sha256=sha(path))
                info = tar.gettarinfo(str(path), arcname=member)
                # Record every selected path as its own regular-file payload.
                info.type = tarfile.REGTYPE
                info.linkname = ''
                info.size = row['bytes']
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ''
                with path.open('rb') as source:
                    tar.addfile(info, source)
                require(sha(path) == row['sha256'], 'input changed during archive')
                records.append(row)
    out.mkdir(parents=True)
    subprocess.run(['split','-b','32M','-d','-a','3',str(whole),str(out/'ROOM-completion.tar.gz.part-')], check=True)
    parts = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(out.glob('*.part-*'))]
    inventory = dict(passed=True, scope='Complete ROB-space global-route research experiment; original baseline unchanged',
                     archive_sha256=sha(whole), archive_bytes=whole.stat().st_size, parts=parts, records=records,
                     publication_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                     native_source_commit=json.loads((BASE/'native/physical-controller.json').read_text())['source_commit'],
                     functional_source_commit=json.loads((BASE/'functional-pipeline.json').read_text())['start']['commit'],
                     retained_shared_FPU_proof='docs/evidence/2026-10-29/lsu-b-complete-validation',
                     retained_AB_reference='docs/evidence/2026-11-13/lsu-ab-complete',
                     retained_functional_reference='docs/evidence/2026-11-18/lsu-rob-room-functional')
    (out/'copy-inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    for name in ['complete-review.json','physical-review.json','physical-path-summary.json','environment-restoration.json']:
        (out/name).write_bytes((BASE/name).read_bytes())
    (out/'README.md').write_text('''# ROB-space physical completion evidence

Fresh native ROOM synthesis, the exact proved shared FPU, global-route, hold40,
uniform ready guard, independent TT/SS/FF trials and complete workload measurements.
The original baseline, fixed 10,000 ps memory and two-family targets are unchanged.
This is global-route research evidence, not detailed-route or tapeout signoff.

Stage checkpoint archives retain raw construction files. Independent STA reports
and all workload files are separate members. Failed capacity preparation and its
recovery are retained. The interrupted predecessor collection and its replay
receipt are also included. Exact parked images and historical caches are restored.
The prior complete functional archive is nested unchanged. Replay additionally
uses the original baseline, shared-FPU proof and A+B/arbitration reference archives;
their identities are checked by the retained independent reviewers.

Verify all public files and every decoded payload without extraction:

```sh
python3 experiments/lsu-rob-room-v1/verify_completion_archive.py <this-directory>
```

Only extract verified evidence into a fresh review checkout. Member paths are
repository relative; original execution commands retain their original paths.
See [the result](../../../LSU_ROB_ROOM_REVIEW.md) and
[critical paths](../../../CRITICAL_PATHS.md).
'''.replace('<this-directory>', str(out.relative_to(ROOT))))
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k:v for k,v in inventory.items() if k != 'records'}, indent=2))

if __name__ == '__main__':
    main()
