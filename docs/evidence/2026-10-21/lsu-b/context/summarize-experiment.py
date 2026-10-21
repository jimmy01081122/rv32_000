"""Complete B v1 evidence review; retain failed timing and unqualified cycle scores."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1';sys.path.insert(0,str(ROOT/'scripts'))
from experiment_contract import load_experiment
from baseline_contract import sha
contract=ROOT/'experiments/lsu-b-v1/manifest.json';exp,baseline=load_experiment(contract)
unit=json.loads((OUT/'unit-clean-v1/summary.json').read_text());assert unit['passed'] and unit['input_identities_unchanged'] and len(unit['records'])==3 and all(x['passed'] for x in unit['records'])
functional=json.loads((OUT/'review-common-diagnostics-v1.json').read_text());assert functional['functional_measurement_passed'] and functional['numeric_values_checked']==3629 and len(functional['records'])==27
for name in ['source-lineage.json','comparison-provenance-review.json','prior-a-evidence-integrity.json','prior-baseline-evidence-integrity.json','admission-controls/summary.json']:
 j=json.loads((OUT/name).read_text());assert j['passed'],name
stages=[]
for name in ['physical-5500ps-synth-clean-v1','physical-14000ps-backend-clean-v1','physical-14000ps-eco-clean-v1']:
 p=OUT/name/'run.json';j=json.loads(p.read_text());assert j['job_state']=='finished' and j['returncode']==0 and j['flow_completed'] and j['input_identities_unchanged'];stages.append({'stage':name,'started_utc':j['started_utc'],'finished_utc':j['finished_utc'],'summary_sha256':sha(p),'native_execution_passed':True})
eco=OUT/'physical-14000ps-eco-clean-v1';text=(eco/'make.log').read_text();assert '[ERROR ' not in text
assert re.findall(r'Total Placement Failures:\s+(\d+)',text)==['0','0']
final=text.split('RV32_GRT_FINAL_FULL_ROUTE_BEGIN')[-1]
route=re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)',final,re.M);assert route and route[-1][3:]==('0','0','0')
assert '[INFO ANT-0002] Found 0 net violations.' in final and '[INFO ANT-0001] Found 0 pin violations.' in final
collections=[]
for name in ['initial-14000ps','diagnostic-boundary-v1']:
 p=eco/name;j=json.loads((p/'closure-review.json').read_text());raw=json.loads((p/'run.json').read_text());assert raw['collection_completed'] and raw['platform_files_verified']==204 and raw['platform_validation_before_returncode']==raw['platform_validation_after_returncode']==0
 assert not j['passed'] and j['qualified_periods_ps']==[]
 collections.append({'name':name,'review_sha256':sha(p/'closure-review.json'),'records':j['records']})
diag=collections[1]['records'];all_periods={x['period_ps'] for row in diag for x in row['trials']};setup_only=[p for p in sorted(all_periods) if all(next(x for x in row['trials'] if x['period_ps']==p)['setup_slack_ps']>=0 for row in diag)]
assert setup_only==[12300]
area=collections[1]['records'][0]['standard_cell_area_um2'];ratio=area/baseline['physical']['standard_cell_area_um2']
assert all(x['standard_cell_area_um2']==area for c in collections for x in c['records'])
rejection=json.loads((OUT/'review-unqualified-common-clock-v1.json').read_text());assert rejection['passed'] is False and 'not independently qualified' in rejection['error']
cycles=json.loads((OUT/'common-clock-diagnostics.json').read_text());assert cycles['per_pc_work_matches']
assert sha(ROOT/'build/sim/rv32_ooo_sim')=='fd2049c30c5453a532735eefe6c189bc879ce1220a2c33464573168bf24eae78'
status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True);assert not status
r={'scope':'completed independent B v1 experiment at fixed global-route research boundary; physical acceptance FAILED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'experiment_execution_complete':True,'candidate_status':'rejected by physical timing gate; no baseline promotion','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_status':status,'experiment_manifest_sha256':sha(contract),'baseline_commit':exp['baseline_commit'],'baseline_manifest_sha256':sha(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'),'baseline_executable_preserved':True,'unit_cases_per_RTL':62,'unit_original_RTL_negative_control_passed':True,'directed_and_Spike_cases_each':18,'interface_cases':48,'fixed_time_cases':58,'finite_FMA_vectors':3400,'contract_tests':31,'full_common_clock_cases':27,'FP32_outputs':3629,'full_functional_measurement_passed':True,'per_pc_work_matches':True,'common_clock_cycle_diagnostics':{'period_ps':10000,'memory_ps':10000,'embench_geomean':cycles['B_embench_common_clock_geomean'],'fp32_geomean':cycles['B_fp32_common_clock_geomean'],'FP32_groups':cycles['B_fp32_groups'],'physical_qualified':False},'native_execution_stages':stages,'global_route':{'nets':int(re.search(r'Routed nets: (\d+)',final)[1]),'wirelength_um':int(re.search(r'Total wirelength: (\d+) um',final)[1]),'overflow_H_V_total':[0,0,0],'ECO_placement_failures':[0,0],'antenna_net_pin_violations':[0,0]},'standard_cell_area_um2':area,'standard_cell_area_ratio':ratio,'measured_area_budget_passed':ratio<=1.10,'standard_cell_count':diag[0]['standard_cell_count'],'physical_register_count':diag[0]['register_count'],'timing_collections':collections,'physical_timing_qualified':False,'qualified_period_ps':None,'setup_only_smallest_tested_all_corner_period_ps':12300,'setup_only_period_is_NOT_a_qualified_operating_point':True,'fastest_qualified_workload_measurement':None,'fastest_measurement_omission_reason':'No independently qualified clock; full27 common-clock data retained as cycle diagnostics only.','strict_qualified_score_correctly_rejected':True,'planning_targets_demonstrated':False,'interpretation':'B v1 functional mechanism is validated but whole-suite common-clock gains are below targets. Same fixed physical flow fails SS setup at10000 and FF hold atall tested periods. Worst SS setup is FP input-to-completion, not proof of head-store logic causation. FPU RTL is unchanged; a single mapping/placement run cannot establish architecture inevitability.','next_decision':'Jointly review A/B and decide whether to diagnose B mapping/hold or choose another experiment; no automatic A+B or baseline replacement.','review_script_sha256':sha(Path(__file__))}
(OUT/'experiment-result.json').write_text(json.dumps(r,indent=2)+'\n');print('B experiment execution complete; functionalPASS physicalFAIL; area ratio',ratio)
