"""Bind actual build/measurement revisions to identical frozen implementation inputs."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/workspace/rv32_000')
EXP = ROOT/'build/experiments/lsu-a-v1'
manifest = json.loads((ROOT/'experiments/lsu-a-v1/manifest.json').read_text())
sha = lambda data:hashlib.sha256(data).hexdigest()
groups = {key:manifest[key] for key in ['candidate_rtl_files_sha256',
          'simulation_inputs_sha256','physical_inputs_sha256']}
commits = ['39bc12d87f80af2520a72f3a75adb3151a55f4c8',
           'a94132c5bcdc2845f2751962eb715c21bef50c92',
           '70727f50db4e77e4904d4d3492979e6a0f4ad2ba']
result = {'scope':'Direct git-object hash comparison across actual implementation, archive and operating-point-tool revisions.',
          'script_sha256':sha(Path(__file__).read_bytes()),'records':[]}
for commit in commits:
    record = {'commit':commit,'groups':{}}
    for group, files in groups.items():
        checked = {}
        for path, expected in files.items():
            actual = sha(subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT))
            assert actual == expected == sha((ROOT/path).read_bytes()),(commit,path)
            checked[path] = actual
        record['groups'][group] = checked
    result['records'].append(record)
differences=[]
for path, expected in manifest['candidate_rtl_files_sha256'].items():
    original=sha(subprocess.check_output(['git','show',f"{manifest['baseline_commit']}:{path}"],cwd=ROOT))
    if original != expected:differences.append(path)
assert differences == ['rtl/lsu/rv32_ooo_lsu.sv']
result.update(baseline_commit=manifest['baseline_commit'],rtl_files_differing_from_baseline=differences,passed=True)
target=EXP/'source-lineage.json'
assert not target.exists()
target.write_text(json.dumps(result,indent=2)+'\n')
print('All three actual revisions have identical candidate RTL, simulator and physical policy hashes; only LSU differs from frozen baseline')
