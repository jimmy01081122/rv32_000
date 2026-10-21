"""Validate complete functional/cycle evidence independently of failed PPA; no clock qualification."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1';sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from experiment_contract import load_experiment
from experiment_provenance import review_provenance,measurement_command,retired_work
from measure_post_lsu_baseline import check_result
contract=ROOT/'experiments/lsu-b-v1/manifest.json';experiment,baseline=load_experiment(contract)
folder=OUT/'measurement-10000ps-v1';summary=json.loads((folder/'summary.json').read_text());build=OUT/'build-clean-v1/summary.json';qualification=OUT/'qualification-clean-v1/summary.json'
proof,normal=review_provenance(contract,experiment,summary,build,qualification)
assert summary['passed'] and summary['start']==summary['end'] and not summary['start']['status']
assert summary['core_period_ps']==summary['memory_ps']==10000
assert summary['result_checker_sha256']==sha(ROOT/'scripts/measure_post_lsu_baseline.py')
ref=ROOT/baseline['measurement']['formal_evidence'];assert sha(ref/'summary.json')==baseline['measurement']['formal_summary_sha256']==summary['baseline_summary_sha256']
old={(r['family'],r['name']):r for r in json.loads((ref/'summary.json').read_text())['records']}
expected=baseline['workloads'];assert len(summary['records'])==27 and [(x['family'],x['name']) for x in summary['records']]==[(x['family'],x['name']) for x in expected]
records=[];checked=0
for row,record in zip(expected,summary['records']):
 p=folder/row['family']/row['name'];measurement_command(record,normal,p,10000)
 assert record['passed'] and record['execution']['returncode']==0
 for name,digest in [('input.elf',row['elf_sha256']),('dut.log',record['execution']['log_sha256']),('profile.json',record['profile_sha256']),('memory.json',record['memory_audit_sha256'])]:assert sha(p/name)==digest,(row['name'],name)
 counters=json.loads((p/'profile.json').read_text());result=check_result(row,(p/'dut.log').read_text(),json.loads((p/'memory.json').read_text()),10000,10000,p/'input.elf',counters,require_reference_cycles=False)
 assert not result['problems'],result
 original=ref/row['family']/row['name']/'profile.json';assert sha(original)==old[row['family'],row['name']]['profile_sha256'];reference=json.loads(original.read_text())
 assert counters['retired_classes']==reference['retired_classes'] and retired_work(counters)==retired_work(reference)
 if result['numeric']:checked+=result['numeric']['checked_values']
 records.append({'family':row['family'],'name':row['name'],'cycles':result['cycles'],'numeric_checked':result['numeric']['checked_values'] if result['numeric'] else 0,'raw_hashes_and_memory_and_stack_passed':True,'retired_classes_and_per_pc_work_match':True})
assert checked==3629
(OUT/'review-common-diagnostics-v1.json').write_text(json.dumps({'scope':'complete functional and common-clock cycle-diagnostic review only; physical acceptance is separate and FAILED','physical_operating_point_qualified':False,'functional_measurement_passed':True,'experiment_manifest_sha256':sha(contract),'measurement_summary_sha256':sha(folder/'summary.json'),'build_functional_provenance':proof,'reviewer_sha256':sha(Path(__file__)),'records':records,'numeric_values_checked':checked},indent=2)+'\n')
print('full common-clock diagnostic review PASS: actual build/function proof, all27 raw/numerics/memory/stack/perPCwork, FP3629. No physical operating point qualified.')
