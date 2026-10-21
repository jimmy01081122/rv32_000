import datetime,json,os,shutil,time
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-b-v1'
log=out/'resource-samples.jsonl'
assert not log.exists()
while True:
 state=None;p=out/'physical-pipeline.json'
 if p.exists():state=json.loads(p.read_text())
 memory={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ['MemTotal','MemAvailable','SwapTotal','SwapFree']}
 row={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'free_disk_bytes':shutil.disk_usage(root).free,'load_average':os.getloadavg(),'memory_kib':memory,'physical_attempt':state.get('active_attempt') if state else None,'physical_complete':state.get('complete') if state else False}
 with log.open('a') as f:f.write(json.dumps(row)+'\n')
 if state and (state.get('complete') or state.get('error')):break
 time.sleep(30)
