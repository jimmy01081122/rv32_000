"""Verify indexed bytes, staged Git blobs, current-doc links and change scope."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path('/workspace/rv32_000')
ARCHIVE = ROOT/'docs/evidence/2026-10-20/lsu-a-physical'
DOCS = ['README.md','PLAN.md','architecture_spec.md','docs/STATUS.md',
        'docs/PROGRESS_REVIEW.md','docs/LSU_OPTIMIZATION_REVIEW.md','docs/README.md',
        'docs/FP32_BALANCED_PROPOSAL.md','docs/LSU_INTERFACE_FIX.md',
        'experiments/lsu-a-v1/README.md']
indexed = set()
for line in (ARCHIVE/'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ',1)
    assert name not in indexed
    path = ARCHIVE/name
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    indexed.add(name)
actual = {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file()}
assert indexed | {'SHA256SUMS'} == actual

staged = {}
for entry in subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).split(b'\0'):
    if not entry:continue
    metadata, name = entry.split(b'\t',1)
    staged[name.decode()] = metadata.split()[1].decode()
for name in actual:
    path = ARCHIVE/name
    data = path.read_bytes()
    object_id = hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    assert staged.get(str(path.relative_to(ROOT))) == object_id, name

links = 0
for path in [ROOT/name for name in DOCS]+[ARCHIVE/'README.md']:
    for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)',path.read_text()):
        if '://' in target or target.startswith(('mailto:','#')):continue
        assert (path.parent/target).exists(), (path,target)
        links += 1
changed = subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines()
assert changed and all(name in DOCS or name.startswith(str(ARCHIVE.relative_to(ROOT))+'/') for name in changed)
assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True)
assert hashlib.sha256((ROOT/'baselines/ap5b-post-lsu-v1/manifest.json').read_bytes()).hexdigest() == '60f59b3cc705560885e2101046d810cf3548fef277c1c1e5820826ef25485fb6'
summary={'scope':'Final archive byte, staged Git-blob and current-document validation.',
         'indexed_files_verified':len(indexed),'all_archive_files_tracked_with_exact_bytes':True,
         'current_local_links_verified':links,'changed_paths':len(changed),
         'frozen_baseline_manifest_unchanged':True,'only_current_docs_and_new_evidence_changed':True,
         'passed':True}
(ROOT/'build/experiments/lsu-a-v1/final-archive-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
