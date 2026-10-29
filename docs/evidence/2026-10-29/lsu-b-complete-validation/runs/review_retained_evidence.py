"""Revalidate immutable B functional/build/unit and shared-FPU archive dependencies."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime
root=Path.cwd();sys.path.insert(0,str(root/'scripts'))
from baseline_contract import sha
from experiment_contract import load_experiment
from experiment_provenance import review_provenance,artifacts,retired_work
from measure_post_lsu_baseline import check_result
out=root/'build/experiments/lsu-b-validation-v2/retained-evidence-review.json';assert not out.exists()
report=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archives=[],passed=False)
for rel in ['docs/evidence/2026-10-27/fpu-mapping-repair','docs/evidence/2026-10-21/lsu-b']:
 path=root/rel;run=subprocess.run(['sha256sum','--strict','--quiet','-c','SHA256SUMS'],cwd=path,capture_output=True,text=True);assert run.returncode==0,run.stderr;report['archives'].append(dict(path=rel,sha256sums_sha256=sha(path/'SHA256SUMS'),indexed_files=len((path/'SHA256SUMS').read_text().splitlines()),returncode=run.returncode))
unitdir=root/'build/experiments/lsu-b-v1/unit-clean-v1';unit=json.loads((unitdir/'summary.json').read_text());assert unit['passed'] and unit['input_identities_unchanged'];assert all(sha(root/n)==h for n,h in unit['source_sha256'].items());artifacts(unit)
for row in unit['builds']:assert sha(unitdir/row['rtl']/'lsu_unit')==row['binary_sha256'] and row['generation']['returncode']==row['compile']['returncode']==0
assert len(unit['records'])==3 and all(r['passed'] for r in unit['records']);report['retained_unit']=dict(summary_sha256=sha(unitdir/'summary.json'),cases_per_rtl=62,original_RTL_timing_negative=True,passed=True)
exp=root/'experiments/lsu-b-v1/manifest.json';experiment,baseline=load_experiment(exp);measurement=root/'build/experiments/lsu-b-validation-v2/measurement-10000ps-v1';data=json.loads((measurement/'summary.json').read_text());assert data['passed'] and data['start']==data['end'] and not data['start']['status']
provenance,normal=review_provenance(exp,experiment,data,root/'build/experiments/lsu-b-v1/build-clean-v1/summary.json',root/'build/experiments/lsu-b-v1/qualification-clean-v1/summary.json');report['retained_functional']=provenance
reference=root/baseline['measurement']['formal_evidence'];old={(r['family'],r['name']):r for r in json.loads((reference/'summary.json').read_text())['records']};assert sha(reference/'summary.json')==data['baseline_summary_sha256']==baseline['measurement']['formal_summary_sha256'];assert len(data['records'])==27;count=0
for row,record in zip(baseline['workloads'],data['records']):
 assert (row['family'],row['name'])==(record['family'],record['name']);directory=measurement/row['family']/row['name'];profile=directory/'profile.json';log=directory/'dut.log';audit=directory/'memory.json'
 assert record['passed'] and record['execution']['returncode']==0 and sha(profile)==record['profile_sha256'] and sha(log)==record['execution']['log_sha256'] and sha(audit)==record['memory_audit_sha256'] and sha(directory/'input.elf')==row['elf_sha256']
 counters=json.loads(profile.read_text());check=check_result(row,log.read_text(),json.loads(audit.read_text()),10000,10000,directory/'input.elf',counters,require_reference_cycles=False);assert not check['problems'];previous=reference/row['family']/row['name']/'profile.json';assert sha(previous)==old[row['family'],row['name']]['profile_sha256'];original=json.loads(previous.read_text());assert counters['retired_classes']==original['retired_classes'] and retired_work(counters)==retired_work(original)
 if check['numeric']:count+=check['numeric']['checked_values']
assert count==3629;report['fresh_measurement']=dict(scope='functional/full workload cycle checks only; physical qualification separately required',summary_sha256=sha(measurement/'summary.json'),workloads=27,numerical_values=3629,per_pc_work_matches=True,passed=True)
report.update(passed=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer_sha256=sha(Path(__file__)));out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
