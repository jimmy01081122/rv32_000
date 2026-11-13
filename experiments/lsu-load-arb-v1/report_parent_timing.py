#!/usr/bin/env python3
"""Recheck and extract the completed A+B parent's setup/hold path inventory."""
import argparse,hashlib,json,math,re,shutil
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
PARENT=ROOT/'build/experiments/lsu-ab-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();require(not out.exists(),'preserve previous timing inventory')
    public=ROOT/'docs/evidence/2026-11-13/lsu-ab-complete';inventory=json.loads((public/'copy-inventory.json').read_text())
    retained={r['member']:r['sha256'] for r in inventory['records']}
    def bound(path):require(sha(path)==retained[str(path.relative_to(ROOT))],'parent archived input differs: '+str(path))
    physical=PARENT/'physical-review.json';bound(physical);review=json.loads(physical.read_text())
    require(review['passed'],'parent physical review failed')
    directory=PARENT/'native/physical-AB-v4/guard/independent-boundary-v1'
    bound(directory/'run.json');collector=json.loads((directory/'run.json').read_text())
    out.mkdir(parents=True);records=[]
    for corner in ['TT','SS','FF']:
        record=next(r for r in collector['records'] if r['corner']==corner)
        for period in [9400,10000]:
            exact=next(t for r in review['AB_physical']['records'] if r['corner']==corner for t in r['trials'] if t['period_ps']==period)
            for kind in ['setup','hold']:
                source=directory/corner/f'{kind}_paths_{period}.rpt';bound(source)
                require(sha(source)==record['outputs_sha256'][source.name],'collector hash differs');paths=[]
                for chunk in source.read_text().split('Startpoint: ')[1:]:
                    endpoint=re.search(r'^Endpoint: (.+)',chunk,re.M)[1]
                    group=re.search(r'^Path Group: (.+)',chunk,re.M)[1]
                    slack=float(re.search(r'^\s*(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)',chunk,re.M)[1])
                    paths.append(dict(startpoint=chunk.splitlines()[0],endpoint=endpoint,group=group,slack_ps=slack))
                require(len(paths)==20 and {p['group'] for p in paths}=={'in2out','in2reg','reg2out','reg2reg'},'incomplete path groups')
                paths.sort(key=lambda p:p['slack_ps']);require(math.isclose(paths[0]['slack_ps'],exact[kind+'_slack_ps'],abs_tol=.005),'path minimum differs from admitted closure')
                target=out/corner/source.name;target.parent.mkdir(exist_ok=True);shutil.copy2(source,target)
                records.append(dict(corner=corner,period_ps=period,kind=kind,source=str(source.relative_to(ROOT)),sha256=sha(source),exact_minimum_slack_ps=exact[kind+'_slack_ps'],paths=paths))
    result=dict(passed=True,scope='retained A+B parent timing, not fresh arbitration timing',parent_commit='49122fb9b37292c9a2c2dc4b4b70226909304293',
                native_commit='f66e12baf034113070c298006595d7292aa911bd',analyzer_sha256=sha(Path(__file__)),physical_review_sha256=sha(physical),records=records)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print('Verified 240 retained parent paths across three corners and two periods')
if __name__=='__main__':main()
