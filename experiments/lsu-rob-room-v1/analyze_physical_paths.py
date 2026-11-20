#!/usr/bin/env python3
"""Cross-check sampled ROOM setup/hold paths against independently admitted closure."""
import hashlib,json,math,re
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
BASE=ROOT/'build/experiments/lsu-rob-room-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    review=json.loads((BASE/'physical-review.json').read_text());require(review['passed'],'physical review required')
    output=BASE/'physical-path-summary.json';require(not output.exists(),'fresh path inventory required')
    admitted=review['ROOM_physical'];periods=sorted({10000,admitted['smallest_tested_passing_period_ps']})
    directory=BASE/'native/physical-ROOM-v4/guard/independent-boundary-v1'
    collection=json.loads((directory/'run.json').read_text());records=[]
    require(collection['collection_completed'] and all(r['returncode']==0 for r in collection['records']),
            'independent collection incomplete')
    for corner in ['TT','SS','FF']:
        entry=next(r for r in collection['records'] if r['corner']==corner)
        for period in periods:
            exact=next(t for c in admitted['records'] if c['corner']==corner for t in c['trials'] if t['period_ps']==period)
            for kind in ['setup','hold']:
                source=directory/corner/f'{kind}_paths_{period}.rpt';digest=sha(source)
                require(entry['outputs_sha256'][source.name]==digest,'raw timing report differs from collector')
                paths=[]
                for chunk in source.read_text().split('Startpoint: ')[1:]:
                    endpoint=re.search(r'^Endpoint: (.+)',chunk,re.M)[1]
                    group=re.search(r'^Path Group: (.+)',chunk,re.M)[1]
                    slack=float(re.search(r'^\s*(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)',chunk,re.M)[1])
                    paths.append(dict(startpoint=chunk.splitlines()[0],endpoint=endpoint,group=group,slack_ps=slack))
                require(len(paths)==20 and {p['group'] for p in paths}=={'in2out','in2reg','reg2out','reg2reg'},'incomplete sampled groups')
                paths.sort(key=lambda p:p['slack_ps'])
                require(math.isclose(paths[0]['slack_ps'],exact[kind+'_slack_ps'],abs_tol=.005),'path minimum differs from independent closure')
                records.append(dict(corner=corner,period_ps=period,kind=kind,source=str(source.relative_to(ROOT)),
                                    sha256=digest,exact_minimum_slack_ps=exact[kind+'_slack_ps'],paths=paths))
    result=dict(passed=True,scope='five sampled paths per group; not an exhaustive path enumeration or full reverse mapping to RTL arithmetic',
                analyzer_sha256=sha(Path(__file__)),physical_review_sha256=sha(BASE/'physical-review.json'),
                collector_sha256=sha(directory/'run.json'),records=records)
    output.write_text(json.dumps(result,indent=2)+'\n');print('All',sum(len(r['paths']) for r in records),'sampled corner/period/setup/hold paths match independent closure')
if __name__=='__main__':main()
