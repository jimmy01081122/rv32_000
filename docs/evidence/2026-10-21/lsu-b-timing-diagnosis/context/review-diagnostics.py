"""Cross-check new diagnostics against immutable original implementation proof."""
from pathlib import Path
import datetime, hashlib, json, subprocess
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-diagnosis-v1'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
native=load(out/'native-probes.json');assert native['complete'] and len(native['jobs'])==12
assert native['input_identities_unchanged'] and native['critical_hashes_before_returncode']==native['critical_hashes_after_returncode']==0
for p,h in native['input_sha256'].items():assert sha(root/p)==h,p
inputs=load(out/'replay-inputs.json')['implementations']
matches=[]
for row in native['jobs']:
 assert row['status']=='complete' and row['returncode']==0
 base=out/'native'/row['candidate']/row['view']/row['corner']
 for p,h in row['outputs_sha256'].items():assert sha(base/p)==h,(base,p)
 if row['view']!='routed':continue
 orig=root/inputs[row['candidate']]['final_metadata']['path']
 original=load(orig.parent/row['corner']/'clock_trials.json')
 trial=next(r for r in original['trials'] if r['period_ps']==10000)
 deltas={k:row['metrics'][k]-trial[k] for k in ('setup_slack_ps','hold_slack_ps')}
 assert max(abs(v) for v in deltas.values())<1e-6,deltas
 matches.append(dict(candidate=row['candidate'],corner=row['corner'],original_trial=str((orig.parent/row['corner']/'clock_trials.json').relative_to(root)),original_sha256=sha(orig.parent/row['corner']/'clock_trials.json'),differences_ps=deltas))
assert len(matches)==9
connectivity=load(out/'synthesis-connectivity-review.json');assert connectivity['passed']
assert len(connectivity['records'])==3
cones=load(out/'mapped-cone-comparison.json')
assert len({r['fp_module_sha256'] for r in cones['lowered_fp_modules'].values()})==1
for r in cones['records'].values():assert not r['selected_routed_path_unmatched_nonbuffer_cells'] and not r['unresolved_anonymous_cone_nets']
paths=load(out/'native-path-comparison.json')['records']
assert len(paths)==72,len(paths)
def path(candidate,view,corner,report):return next(r for r in paths if (r['candidate'],r['view'],r['corner'],r['report'])==(candidate,view,corner,report))
for candidate in ('baseline','A','B'):
 assert path(candidate,'synthesis','SS','fp_max.rpt')['wire_delay_ps']==0
 # Check worst FP path against the original independently collected reg2reg group.
 original=next(r for r in load(out/'reported-path-comparison.json')['records'] if (r['candidate'],r['corner'],r['kind'],r['group'])==(candidate,'SS','setup','reg2reg'))
 current=path(candidate,'routed','SS','fp_max.rpt')
 assert abs(original['slack_ps_rounded']-current['slack_ps'])<=0.0051
 assert original['start']==current['start'] and original['end']==current['end']
assert path('B','routed','FF','ready_to_tracking_min.rpt')['slack_ps']<0
assert next(r for r in native['jobs'] if (r['candidate'],r['view'],r['corner'])==('B','routed','FF'))['metrics']['reported_hold_violating_endpoints']==2
old_archives=[]
for name in ['2026-10-18/post-lsu-baseline','2026-10-19/lsu-a-functional','2026-10-20/lsu-a-physical','2026-10-20/lsu-a-review','2026-10-21/lsu-b']:
 archive=root/'docs/evidence'/name
 subprocess.run(['sha256sum','--quiet','--strict','-c','SHA256SUMS'],cwd=archive,check=True)
 old_archives.append(dict(path=str(archive.relative_to(root)),indexed_files=len((archive/'SHA256SUMS').read_text().splitlines()),index_sha256=sha(archive/'SHA256SUMS'),verified=True))
baseline_sim=root/'build/sim/rv32_ooo_sim'
assert sha(baseline_sim)=='fd2049c30c5453a532735eefe6c189bc879ce1220a2c33464573168bf24eae78'
subprocess.run(['git','diff','--exit-code','0804b7c','--','rtl','sim','physical','scripts','baselines','experiments'],cwd=root,check=True)
summary=dict(scope='Read-only B timing diagnosis, not a new physical operating-point qualification',reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,native_jobs=12,original_routed_corner_matches=matches,cell_net_decompositions=len(paths),synthesis_cache_cells_checked=sum(r['parser_cell_count'] for r in connectivity['records']),old_archives_verified=old_archives,baseline_sim_sha256=sha(baseline_sim),CPU_and_scored_inputs_unchanged=True,
 setup_deltas_B_minus_baseline_ps={
  'routed_worst_FP_data_delay':path('B','routed','SS','fp_max.rpt')['data_delay_ps']-path('baseline','routed','SS','fp_max.rpt')['data_delay_ps'],
  'synthesis_zero_wire_worst_FP_data_delay':path('B','synthesis','SS','fp_max.rpt')['data_delay_ps']-path('baseline','synthesis','SS','fp_max.rpt')['data_delay_ps'],
  'synthesis_zero_wire_same_FP_sink_115':path('B','synthesis','SS','fp_sink_115_max.rpt')['data_delay_ps']-path('baseline','synthesis','SS','fp_sink_115_max.rpt')['data_delay_ps'],
 },interpretation='Original B remains timing rejected. Structural mapping and loaded cell-arc differences precede route; zero-wire results do not establish a usable clock. No particular FP opcode, optimizer pass, deterministic rerun property, or inevitable B architecture penalty is proved.')
(out/'diagnostic-review.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('original_routed_corner_matches','old_archives_verified')},indent=2))
