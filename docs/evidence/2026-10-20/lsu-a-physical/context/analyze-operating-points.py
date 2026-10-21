"""Derive both operating points from complete qualified reviews and raw audits."""
from pathlib import Path
import hashlib
import json
import math
import re

ROOT = Path('/workspace/rv32_000')
EXP = ROOT/'build/experiments/lsu-a-v1'
BASE = ROOT/'docs/evidence/2026-10-18/post-lsu-baseline/measurement'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def retired_work(profile):
    rows = [p for p in profile['pcs'] if p['retired']]
    counts = {(p['pc'], p['insn'], p['kind']):p['retired'] for p in rows}
    assert len(rows) == len(counts)
    return counts

manifest = ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'
baseline = json.loads(manifest.read_text())
rows = baseline['workloads']
result = {'scope':'Two complete qualified research operating points; no primary point selection, no ordered-trace or full-ISA proof.',
          'script_sha256':sha(Path(__file__)), 'baseline_manifest_sha256':sha(manifest),
          'baseline_summary_sha256':sha(BASE/'summary.json'), 'operating_points':[]}
for period, label in [(10000,'common-clock'), (9900,'fastest')]:
    measurement = EXP/f'measurement-{period}ps-v1'
    review_path = EXP/('review-common-clock-v1.json' if period == 10000 else 'review-fastest-v1.json')
    review = json.loads(review_path.read_text())
    summary_path = measurement/'summary.json'
    summary = json.loads(summary_path.read_text())
    assert review['passed'] and summary['passed']
    assert sha(summary_path) == review['measurement_summary_sha256']
    assert review['core_period_ps'] == period and review['comparison_point'] == label
    assert summary['start'] == summary['end'] and not summary['start']['status']
    assert len(summary['records']) == len(rows) == len(review['records']) == 27
    point = {k:review[k] for k in ['comparison_point','core_period_ps','memory_ps',
             'embench_time_geomean_speedup','fp32_time_geomean_speedup','fp32_subgroup_speedup',
             'standard_cell_area_um2','area_ratio','planning_targets','all_planning_targets_met']}
    point.update(review_sha256=sha(review_path), measurement_summary_sha256=sha(summary_path), records=[])
    for row, record, score in zip(rows, summary['records'], review['records']):
        identity = (row['family'], row['name'])
        assert identity == (record['family'], record['name']) == (score['family'], score['name'])
        directory = measurement/row['family']/row['name']
        profile_path = directory/'profile.json'
        old_path = BASE/row['family']/row['name']/'profile.json'
        audit_path = directory/'memory.json'
        old = json.loads(old_path.read_text())
        new = json.loads(profile_path.read_text())
        audit = json.loads(audit_path.read_text())
        assert sha(profile_path) == record['profile_sha256']
        assert sha(audit_path) == record['memory_audit_sha256']
        assert retired_work(old) == retired_work(new)
        expected_sampled_response = math.ceil(10000/period)*period
        for port in ['imem','dmem']:
            assert audit[f'{port}_min_response_ps'] == audit[f'{port}_max_response_ps'] == expected_sampled_response
        point['records'].append({**score, 'per_pc_insn_kind_retired_counts_match':True,
            'nonzero_retired_pc_count':len(retired_work(new)),
            'baseline_profile_sha256':sha(old_path), 'candidate_profile_sha256':sha(profile_path),
            'memory_audit_sha256':sha(audit_path),
            'sampled_memory':{k:v for k,v in audit.items() if 'response_ps' in k or 'interval_ps' in k},
            'cycle_partition':new['cycle_partition'],
            'load_head_wait_phases':new['load_head_wait_phases'],
            'store_ack_wait_phases':new['store_ack_wait_phases']})
    point['all_27_per_pc_work_maps_match'] = True
    result['operating_points'].append(point)

common = result['operating_points'][0]
result['remaining_planning_gap_from_common_point'] = {
    'scope':'Required further improvement relative to common-clock A; no predicted B benefit.',
    'embedded_additional_speedup_required':1.20/common['embench_time_geomean_speedup'],
    'fp32_additional_speedup_required':1.20/common['fp32_time_geomean_speedup'],
    'remaining_standard_cell_budget_um2':1.10*baseline['physical']['standard_cell_area_um2']-common['standard_cell_area_um2']}

log_path = EXP/'physical-14000ps-eco-clean-v1/make.log'
text = log_path.read_text()
assert text.count('RV32_GRT_FINAL_FULL_ROUTE_BEGIN') == 1 and '[ERROR ' not in text
final = text.split('RV32_GRT_FINAL_FULL_ROUTE_BEGIN')[1]
totals = re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s*(\d+) /\s*(\d+)', final, re.M)
failures = re.findall(r'Total Placement Failures:\s+(\d+)', text)
assert totals[-1][3:] == ('0','0','0') and failures == ['0','0']
assert '[INFO ANT-0002] Found 0 net violations.' in final
assert '[INFO ANT-0001] Found 0 pin violations.' in final
result['native_route_evidence'] = {
    'make_log_sha256':sha(log_path), 'final_whole_design_route_markers':1,
    'final_overflow_h_v_total':[int(x) for x in totals[-1][3:]],
    'final_demand_percent':float(totals[-1][2]),
    'final_routed_nets':int(re.findall(r'Routed nets:\s+(\d+)',final)[-1]),
    'final_wirelength_um':int(re.findall(r'Total wirelength:\s+(\d+) um',final)[-1]),
    'eco_placement_failures':[int(x) for x in failures],
    'antenna_net_violations':0,'antenna_pin_violations':0}
out = EXP/'operating-point-analysis.json'
assert not out.exists()
out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({**result,'operating_points':[{k:v for k,v in x.items() if k != 'records'} for x in result['operating_points']]},indent=2))
