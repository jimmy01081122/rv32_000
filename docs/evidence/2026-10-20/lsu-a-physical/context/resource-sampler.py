import datetime,json,subprocess,shutil,time
from pathlib import Path
root=Path('/workspace/rv32_000');out=root/'build/experiments/lsu-a-v1';dest=out/'physical-resources.jsonl';assert not dest.exists()
while True:
 state=json.loads((out/'physical-pipeline.json').read_text());p=subprocess.run(['ps','-C','yosys,yosys-abc,abc,openroad','-o','pid,ppid,pcpu,etime,rss,comm','--no-headers'],text=True,stdout=subprocess.PIPE)
 processes=[]
 for line in p.stdout.splitlines():
  pid,parent,cpu,elapsed,rss,comm=line.split();processes.append({'pid':int(pid),'ppid':int(parent),'cumulative_lifetime_cpu_percent':float(cpu),'elapsed':elapsed,'rss_kib':int(rss),'comm':comm})
 record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'read-only host resource samples beginning mid-synthesis; no arguments or environment values collected','active_attempt':state.get('active_attempt'),'processes':processes,'workspace_free_bytes':shutil.disk_usage(root).free,'pipeline_complete':state.get('complete'),'pipeline_error':state.get('error')}
 with dest.open('a') as f:f.write(json.dumps(record)+'\n')
 if state.get('complete') or state.get('error'):break
 time.sleep(25)
