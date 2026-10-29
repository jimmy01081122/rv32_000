#!/usr/bin/env python3
"""Verify stored/decoded evidence; optionally compare retained workspace sources."""
import argparse,datetime,gzip,hashlib,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=Path);ap.add_argument('--report',type=Path);args=ap.parse_args();root=Path(__file__).resolve().parent;data=json.loads((root/'copy-inventory.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest();stored_hashes={};sources=0
for row in data['records']:
 p=root/row['destination'];assert p.resolve().is_relative_to(root)
 raw=p.read_bytes();assert sha(raw)==row['stored_sha256'],row['destination'];assert len(raw)==row['stored_bytes'];decoded=gzip.decompress(raw) if row['encoding']=='gzip' else raw;assert sha(decoded)==row['source_sha256'],row['source'];assert len(decoded)==row['source_bytes'];stored_hashes[row['destination']]=row['stored_sha256']
 if args.workspace:
  source=args.workspace/row['source'];assert source.resolve().is_relative_to(args.workspace.resolve());assert sha(source.read_bytes())==row['source_sha256'],row['source'];sources+=1
for name in ['final-common-clock-review.json','final-fastest-review.json']:
 result=json.loads((root/'runs'/name).read_text());assert result['passed'] and not result['all_planning_targets_met'];assert result['reviewer_sha256']==sha((root/'inputs/experiments/lsu-b-validation-v2/review_guard.py').read_bytes());assert len(result['measurement']['records'])==27 and result['measurement']['numerical_values_checked']==3629
negative=json.loads((root/'runs/guard-admission-controls-v1/summary.json').read_text());assert negative['passed'] and len(negative['records'])==7 and all(r['rejected'] for r in negative['records'])
assert (root/'inputs/experiments/lsu-b-validation-v2/check_guard_admission.py').read_bytes()==(root/'runs/check_guard_admission.py').read_bytes()
report=dict(passed=True,checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),copy_inventory_sha256=sha((root/'copy-inventory.json').read_bytes()),inventory_records=len(data['records']),unique_payload_files=len(stored_hashes),decoded_originals_verified=len(data['records']),workspace_sources_verified=sources,stored_payload_bytes=sum((root/p).stat().st_size for p in stored_hashes),excluded_entries=len(data['excluded']),final_reviews_passed=2,workloads_per_review=27,numerical_values_per_review=3629,negative_controls_rejected=7)
if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
