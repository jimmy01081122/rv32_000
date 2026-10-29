"""Exercise strict v2 admission on positive physical data and actual corrupted records."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,re,shutil,os
ap=argparse.ArgumentParser();ap.add_argument('--analysis',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();root=Path.cwd();script=root/'experiments/lsu-b-validation-v2/review.py';spec=importlib.util.spec_from_file_location('review',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);contract=json.loads(m.CONTRACT.read_text());analysis=args.analysis.resolve();out=args.output.resolve();out.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();records=[]
positive=m.review_physical(analysis,'B',contract);assert positive['passed'];(out/'positive.json').write_text(json.dumps(positive,indent=2)+'\n')
def reject(label,fn):
 try:fn()
 except ValueError as e:records.append(dict(control=label,rejected=True,reason=str(e)))
 else:raise AssertionError('accepted '+label)
reject('wrong-core-variant',lambda:m.review_physical(analysis,'baseline',contract))
wrong=copy.deepcopy(contract);wrong['physical']['post_route_eco']['hold_margin_ps']=50
reject('unmatched-repair-policy',lambda:m.review_physical(analysis,'B',wrong))

def write(path,text):
 temporary=path.with_name(path.name+'.new');temporary.write_text(text);temporary.replace(path)

def copied_attempt(label):
 original=analysis.parent.parent;target=out/label;target.mkdir()
 for p in original.iterdir():
  if p.name=='eco':continue
  (target/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
 stage=target/'eco';stage.mkdir()
 for p in (original/'eco').iterdir():
  if p.name in (analysis.name,'run.json','make.log'):continue
  (stage/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
 shutil.copyfile(original/'eco/run.json',stage/'run.json');shutil.copyfile(original/'eco/make.log',stage/'make.log')
 target_analysis=stage/analysis.name;shutil.copytree(analysis,target_analysis,copy_function=lambda src,dst:os.symlink(Path(src).resolve(),dst))
 return stage,target_analysis

stage,where=copied_attempt('route-overflow');log=stage/'make.log';text=log.read_text();prefix,final=text.rsplit('RV32_GRT_FINAL_FULL_ROUTE_BEGIN',1);final,count=re.subn(r'(^Total\s+\d+\s+\d+\s+[\d.]+%\s+)0 /\s*0 /\s*0',r'\g<1>1 / 0 / 1',final,count=1,flags=re.M);assert count==1;write(log,prefix+'RV32_GRT_FINAL_FULL_ROUTE_BEGIN'+final);run=json.loads((stage/'run.json').read_text());run['log_sha256']=sha(log);write(stage/'run.json',json.dumps(run,indent=2)+'\n');collection=json.loads((where/'run.json').read_text());collection['implementation_report_sha256']=sha(stage/'run.json');write(where/'run.json',json.dumps(collection,indent=2)+'\n');reject('route-overflow',lambda:m.review_physical(where,'B',contract))

stage,where=copied_attempt('negative-hold');corner=where/'FF';trials=json.loads((corner/'clock_trials.json').read_text());collection=json.loads((where/'run.json').read_text())
for row in trials['trials']:
 row['hold_slack_ps']=-1.0;write(corner/f"hold_{row['period_ps']}.rpt",'worst slack min -1.00\n')
write(corner/'clock_trials.json',json.dumps(trials,indent=2)+'\n');record=next(r for r in collection['records'] if r['corner']=='FF');record['outputs_sha256']={p.name:sha(p) for p in sorted(corner.iterdir()) if p.is_file()};write(where/'run.json',json.dumps(collection,indent=2)+'\n');reject('negative-hold-all-clocks',lambda:m.review_physical(where,'B',contract))

stage,where=copied_attempt('electrical-failure');corner=where/'SS';collection=json.loads((where/'run.json').read_text())
for period in collection['clock_trials_ps']:write(corner/f'electrical_{period}.rpt','injected max slew violation\n')
record=next(r for r in collection['records'] if r['corner']=='SS');record['outputs_sha256']={p.name:sha(p) for p in sorted(corner.iterdir()) if p.is_file()};write(where/'run.json',json.dumps(collection,indent=2)+'\n');reject('electrical-violation-all-clocks',lambda:m.review_physical(where,'B',contract))

stage,where=copied_attempt('raw-report-changed');corner=where/'TT';write(corner/'units.rpt','time 1ns\n');reject('raw-report-digest-changed',lambda:m.review_physical(where,'B',contract))
report=dict(passed=len(records)==6 and all(r['rejected'] for r in records),reviewer_sha256=sha(script),positive_review_sha256=sha(out/'positive.json'),records=records);(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
