"""Run actual old/new reviewers on deliberately mismatched copies of real evidence."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys

ROOT=Path('/workspace/rv32_000')
sys.path.insert(0,str(ROOT/'scripts'))
from review_cpu_experiment import review

EXP=ROOT/'build/experiments/lsu-a-v1'
OUT=EXP/'review-v1/admission-controls-v1'
assert not OUT.exists()
OUT.mkdir()
old_path=ROOT/'docs/evidence/2026-10-20/lsu-a-physical/inputs/scripts/review_cpu_experiment.py'
spec=importlib.util.spec_from_file_location('prior_review',old_path)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
source=EXP/'measurement-10000ps-v1'
contract=ROOT/'experiments/lsu-a-v1/manifest.json'
physical=EXP/'physical-14000ps-eco-clean-v1/boundary-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=[source/'summary.json',source/'fp32/fir/profile.json',EXP/'build-clean-v1/summary.json']
original={str(p):sha(p) for p in guard}
records=[]
for label,field in [('unrelated-simulator','simulator_sha256'),
                    ('missing-build-proof','build_summary_sha256'),
                    ('wrong-measurement-wrapper','wrapper_sha256'),
                    ('per-pc-work-mismatch',None)]:
    directory=OUT/label;directory.mkdir()
    summary=json.loads((source/'summary.json').read_text())
    for family in ['fp32','embench']:
        (directory/family).mkdir()
        for case in (source/family).iterdir():
            destination=directory/family/case.name
            if field is None and family=='fp32' and case.name=='fir':
                shutil.copytree(case,destination)
            else:destination.symlink_to(case,target_is_directory=True)
    if field:
        summary[field]='0'*64
    else:
        profile=directory/'fp32/fir/profile.json'
        data=json.loads(profile.read_text())
        rows=[row for row in data['pcs'] if row['retired']>1]
        a=rows[0];b=next(row for row in rows[1:] if row['kind']==a['kind'])
        a['retired']-=1;b['retired']+=1
        profile.write_text(json.dumps(data,indent=2)+'\n')
        record=next(r for r in summary['records'] if r['family']=='fp32' and r['name']=='fir')
        record['profile_sha256']=sha(profile)
        # Bind command paths to this copied case so only the work check rejects it.
        paths={'+elf':profile.parent/'input.elf','+memory-audit':profile.parent/'memory.json',
               '+profile-core-roi':profile}
        record['execution']['command']=[arg.partition('=')[0]+'='+str(paths[arg.partition('=')[0]])
                           if arg.partition('=')[0] in paths else arg
            for arg in record['execution']['command']]
    (directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    before=old.review(contract,directory,physical,'common-clock')
    (directory/'before-review.json').write_text(json.dumps(before,indent=2)+'\n')
    assert before['passed']
    try:
        review(contract,directory,physical,'common-clock',
               build_summary=EXP/'build-clean-v1/summary.json',
               qualification_summary=EXP/'review-v1/qualification-clean-v1/summary.json')
    except ValueError as error:
        after={'passed':False,'rejection':str(error)}
    else:raise AssertionError('new reviewer accepted '+label)
    (directory/'after-review.json').write_text(json.dumps(after,indent=2)+'\n')
    records.append({'name':label,'old_reviewer_accepted':True,**after})
    print(label,'old accepted; new rejected:',after['rejection'],flush=True)
assert all(sha(Path(p))==digest for p,digest in original.items())
report={'scope':'Actual admission controls; deliberately altered copies, never new CPU results.',
        'script_sha256':sha(Path(__file__)),'old_reviewer_sha256':sha(old_path),
        'new_reviewer_sha256':sha(ROOT/'scripts/review_cpu_experiment.py'),
        'provenance_validator_sha256':sha(ROOT/'scripts/experiment_provenance.py'),
        'original_inputs_sha256':original,'original_inputs_unchanged':True,'records':records,
        'all_four_regressions_rejected':len(records)==4}
(OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
