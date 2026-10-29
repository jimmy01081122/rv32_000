"""Make the convenience GRT aliases resolve identically on host and container."""
from pathlib import Path
import json,time,datetime
base=Path(__file__).resolve().parent;records=[];deadline=time.monotonic()+7200
for variant in ['B','baseline']:
 link=base/('physical-'+variant+'-v2')/'grt';target=Path('../physical-'+variant+'-v1/grt');expected='/workspace/build/experiments/lsu-b-validation-v2/physical-'+variant+'-v1/grt'
 while not link.is_symlink():
  if time.monotonic()>deadline:raise TimeoutError(str(link))
  time.sleep(10)
 before=str(link.readlink());assert before==expected,(before,expected);link.unlink();link.symlink_to(target,target_is_directory=True);assert link.resolve()==(base/('physical-'+variant+'-v1')/'grt').resolve()
 records.append(dict(variant=variant,before=before,after=str(target),scope='convenience alias only; exact incoming report/ODB paths and hashes unchanged',utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));(base/'route-alias-portability.json').write_text(json.dumps(dict(records=records),indent=2)+'\n');print(variant,'alias resolves on both host and container',flush=True)
