from pathlib import Path
import hashlib,json
ROOT=Path('/workspace/rv32_000');OUT=ROOT/'build/experiments/lsu-b-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((ROOT/'baselines/ap5b-post-lsu-v1/manifest.json').read_text())
ref=ROOT/baseline['measurement']['formal_evidence'];assert sha(ref/'summary.json')==baseline['measurement']['formal_summary_sha256']
a=ROOT/'build/experiments/lsu-a-v1/measurement-10000ps-v1'
archived=ROOT/'docs/evidence/2026-10-19/lsu-a-functional/measurement-10000ps-v1/summary.json'
assert sha(a/'summary.json')==sha(archived)=='5de23abc1efa4c617c872d3f1dedd707bad8d99a27f24ce0790d984aecda919e'
b=OUT/'measurement-10000ps-v1'
diag=json.loads((OUT/'common-clock-diagnostics.json').read_text());rows=[]
for folder in [ref,a,b]:
 summary=json.loads((folder/'summary.json').read_text());assert summary['passed'] and len(summary['records'])==27
 for record in summary['records']:
  p=folder/record['family']/record['name']/'profile.json';assert sha(p)==record['profile_sha256']
 rows.append({'summary':str((folder/'summary.json').relative_to(ROOT)),'sha256':sha(folder/'summary.json'),'all27_profile_digests_match':True})
for row in diag['records']:
 for path,digest in row['profile_sha256'].items():assert sha(ROOT/path)==digest
assert sha(b/'summary.json')==diag['measurement_summary_sha256']
(OUT/'comparison-provenance-review.json').write_text(json.dumps({'scope':'bind complete baseline/A/B common-clock diagnostic table to immutable original summaries and all81 raw profiles','records':rows,'diagnostics_sha256':sha(OUT/'common-clock-diagnostics.json'),'script_sha256':sha(Path(__file__)),'passed':True},indent=2)+'\n')
print('comparison provenance PASS: all81 profiles; baseline manifest and original archivedA summary matched')
