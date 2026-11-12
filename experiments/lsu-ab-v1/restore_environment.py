#!/usr/bin/env python3
"""Restore exact tool images and temporary cache/sparse changes after native review."""
import datetime,gzip,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').is_file())
BASE=ROOT/'build/experiments/lsu-ab-v1'
sys.path.insert(0,str(ROOT/'experiments/lsu-ab-v1'))
sys.path.insert(0,str(ROOT/'experiments/optimization-135-v1'))
from publish_native import DOCKER,CONTAINER,verify
from checkpoint import atomic_json

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):h.update(block)
 return h.hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def main():
 out=BASE/'environment-restoration.json';require(not out.exists(),'preserve prior restoration receipt')
 require(json.loads((BASE/'physical-review.json').read_text())['passed'],'physical qualification required before runtime teardown')
 publication=json.loads((BASE/'native/native-publication.json').read_text());require(publication['passed'],'host publication incomplete');verify(BASE/'native',publication['files'])
 state=dict(passed=False,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stages=[],script_sha256=sha(Path(__file__)));atomic_json(out,state)
 def run(name,command):
  with (BASE/('restore-'+name+'.log')).open('x') as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  state['stages'].append(dict(name=name,command=command,returncode=result.returncode,log_sha256=sha(BASE/('restore-'+name+'.log'))));atomic_json(out,state)
  require(result.returncode==0,'restoration step failed: '+name)
 commands=subprocess.check_output(DOCKER+['top',CONTAINER,'-eo','comm'],text=True).splitlines()
 require(not any(x.strip() in ['openroad','yosys','make','python3'] for x in commands[1:]),'native job still running')
 run('final-platform-check',DOCKER+['exec',CONTAINER,'sha256sum','--strict','--quiet','-c','/workspace/docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'])
 run('native-stop',DOCKER+['stop','--time','10',CONTAINER]);run('native-remove',DOCKER+['rm',CONTAINER])
 cache=BASE/'image-cache-v2';receipt=json.loads((cache/'summary.json').read_text());archive=cache/'rv32-inactive-images.tar.gz'
 require(receipt['complete'] and archive.stat().st_size==receipt['archive_bytes'] and sha(archive)==receipt['archive_sha256'],'pinned image backup changed')
 require(shutil.disk_usage(ROOT).free>=5*1024**3,'need 5 GiB restoration capacity')
 run('pinned-images',DOCKER+['load','--input',str(archive)])
 image_sizes={}
 for tag,expected in receipt['images'].items():
  info=json.loads(subprocess.check_output(DOCKER+['image','inspect',tag]))[0];require(info['Id']==expected,'restored image differs: '+tag);image_sizes[tag]=info['Size']
 smoke={
  'rv32ooo-fp:p1':[['verilator','--version'],['g++','--version'],['riscv-none-elf-gcc','--version'],['riscv-none-elf-gcc','-march=rv32imf_zicsr','-mabi=ilp32f','-print-multi-directory']],
  'rv32ooo-sim:g1':[['verilator','--version'],['riscv32-unknown-elf-gcc','--version'],['spike','--help']],
  'rv32ooo-syn:g1':[['sv2v','--version'],['yosys','-V']]}
 for number,(tag,commands) in enumerate(smoke.items()):
  require(shutil.disk_usage(ROOT).free>=2*image_sizes[tag]+1024**3,'insufficient VFS capacity for exact image smoke: '+tag)
  code='import subprocess,json\ncommands='+repr(commands)+'\nfor command in commands:\n result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)\n print(json.dumps(dict(command=command,returncode=result.returncode,output=result.stdout)))\n assert result.returncode==0 or command==["spike","--help"] and result.returncode==1 and "usage:" in result.stdout.lower()\n'
  run('smoke-'+str(number),DOCKER+['run','--rm','--network','none','--entrypoint','python3',tag,'-c',code])
 historical=json.loads((BASE/'historical-native-compaction.json').read_text());restored=[];seen={}
 for row in historical['records']:
  path=ROOT/row['path'];compressed=ROOT/row['gzip'];require(sha(compressed)==row['gzip_sha256'],'historical compressed bytes changed')
  if path.exists():require(sha(path)==row['sha256'],'unexpected existing historical data')
  elif row['sha256'] in seen:os.link(seen[row['sha256']],path)
  else:
   temporary=path.with_name(path.name+'.restore-tmp');require(not temporary.exists(),'preserve incomplete restoration')
   with gzip.open(compressed,'rb') as source,temporary.open('xb') as destination:shutil.copyfileobj(source,destination)
   require(temporary.stat().st_size==row['bytes'] and sha(temporary)==row['sha256'],'decoded historical bytes differ');os.replace(temporary,path)
  seen[row['sha256']]=path;restored.append(dict(path=row['path'],bytes=path.stat().st_size,sha256=sha(path)))
 run('sparse-checkout', ['git','sparse-checkout','disable'])
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT),'restoration left tracked source changes')
 state.update(passed=True,images=receipt['images'],backup_sha256=receipt['archive_sha256'],historical_files=restored,
              sparse_checkout_restored=True,native_runtime_removed=True,free_bytes=shutil.disk_usage(ROOT).free,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());atomic_json(out,state)
 print('Exact project images, eight historical files and full checkout restored')
if __name__=='__main__':main()
