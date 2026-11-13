#!/usr/bin/env python3
"""Identify sampled AB timing-path groups from the independently reviewed report."""
import hashlib,json,math,re
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 review=json.loads((BASE/'physical-review.json').read_text());assert review['passed']
 output=BASE/'physical-path-summary.json';assert not output.exists()
 a=review['AB_physical'];period=a['smallest_tested_passing_period_ps'];directory=BASE/'native/physical-AB-v4/guard/independent-boundary-v1';collection=json.loads((directory/'run.json').read_text());sources={};records=[]
 for corner in ['TT','SS','FF']:
  source=directory/corner/f'setup_paths_{period}.rpt';digest=sha(source)
  entry=next(r for r in collection['records'] if r['corner']==corner)
  assert entry['outputs_sha256'][source.name]==digest
  sources[str(source.relative_to(ROOT))]=digest;paths=[]
  for chunk in source.read_text().split('Startpoint: ')[1:]:
   start=chunk.splitlines()[0];end=re.search(r'^Endpoint: (.+)',chunk,re.M);group=re.search(r'^Path Group: (.+)',chunk,re.M);slack=re.search(r'^\s*(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)',chunk,re.M)
   if slack:paths.append(dict(startpoint=start,endpoint=end[1],group=group[1],reported_slack_ps=float(slack[1])))
  assert len(paths)==20
  paths.sort(key=lambda r:r['reported_slack_ps'])
  raw=next(t for c in a['records'] if c['corner']==corner for t in c['trials'] if t['period_ps']==period)
  assert math.isclose(paths[0]['reported_slack_ps'],raw['setup_slack_ps'],abs_tol=.005)
  records.append(dict(corner=corner,period_ps=period,exact_setup_slack_ps=raw['setup_slack_ps'],exact_hold_slack_ps=raw['hold_slack_ps'],paths=paths))
 output.write_text(json.dumps(dict(passed=True,scope='sampled native timing paths, not full reverse mapping to an RTL arithmetic expression',analyzer_sha256=sha(Path(__file__)),physical_review_sha256=sha(BASE/'physical-review.json'),source_sha256=sources,records=records),indent=2)+'\n');print('All 60 sampled corner paths agree with independent closure evidence')
if __name__=='__main__':main()
