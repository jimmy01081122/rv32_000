#!/usr/bin/env python3
"""Capture existing A/AB binaries without modifying RTL, ELF or host harness."""
import datetime,gzip,hashlib,json,os,shutil,subprocess,threading
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 out=BASE/'pid-waveforms-v1';out.mkdir();summary=out/'summary.json'
 paths={'A':ROOT/'build/experiments/optimization-135-v1/measurement-source/build/measurement-10000ps-v1','AB':BASE/'measurement-10000ps-v1'}
 state=dict(scope='read-only VCD capture with previously measured unchanged native binaries',script_sha256=sha(Path(__file__)),records=[],passed=False)
 summary.write_text(json.dumps(state,indent=2)+'\n')
 for variant,reference in paths.items():
  summary_data=json.loads((reference/'summary.json').read_text());row=next(r for r in summary_data['records'] if r['name']=='pid' and r['family']=='fp32')
  binary=Path(row['execution']['command'][0]);binary=ROOT/str(binary).removeprefix('/workspace/') if not binary.is_file() else binary
  assert binary.is_file() and sha(binary)==summary_data['simulator_sha256']
  elf=reference/'fp32/pid/input.elf';assert sha(elf)==row['elf_sha256']
  dest=out/variant;dest.mkdir();pipe=dest/'capture.fifo';os.mkfifo(pipe);errors=[]
  def compress():
   try:
    with pipe.open('rb') as src,(dest/'wave.vcd.gz').open('xb') as target:
     with gzip.GzipFile(fileobj=target,mode='wb',compresslevel=1,mtime=0) as gz:shutil.copyfileobj(src,gz,1048576)
   except Exception as error:errors.append(str(error))
  worker=threading.Thread(target=compress,daemon=True);worker.start()
  command=[str(binary),'+elf='+str(elf),'+max-cycles=100000000','+core-period-ps=10000','+imem-response-ps=10000','+imem-interval-ps=10000','+dmem-response-ps=10000','+memory-audit='+str(dest/'memory.json'),'+profile-core-roi='+str(dest/'profile.json'),'+vcd='+str(pipe)]
  start=datetime.datetime.now(datetime.timezone.utc).isoformat()
  with (dest/'dut.log').open('x') as log:run=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  worker.join(timeout=30);assert not worker.is_alive() and not errors and run.returncode==0
  pipe.unlink()
  assert sha(dest/'profile.json')==row['profile_sha256'] and sha(dest/'memory.json')==row['memory_audit_sha256']
  # All program output and simulator accounting must also be byte-identical
  # after removing the sole VCD announcement and normalizing only the ELF path.
  def normalized(text):
   return '\n'.join(line.replace(str(elf),'<ELF>').replace('/workspace/'+str(elf.relative_to(ROOT)),'<ELF>') for line in text.splitlines() if not line.startswith('[Simulator] VCD tracing enabled: '))
  assert normalized((dest/'dut.log').read_text())==normalized((reference/'fp32/pid/dut.log').read_text())
  state['records'].append(dict(variant=variant,command=command,returncode=run.returncode,simulator_sha256=sha(binary),elf_sha256=sha(elf),started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_summary_sha256=sha(reference/'summary.json'),outputs_sha256={p.name:sha(p) for p in dest.iterdir() if p.is_file()},profile_memory_and_program_output_identical=True))
  summary.write_text(json.dumps(state,indent=2)+'\n');print(variant,'waveform captured; all profile/memory/program output identical',flush=True)
 state['passed']=True;summary.write_text(json.dumps(state,indent=2)+'\n')
if __name__=='__main__':main()
