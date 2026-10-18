#!/usr/bin/env python3
"""Legacy equivalence, faster-core fixed-memory tests and invalid timing controls."""
import hashlib
import json
import re
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/qualification/memory-time'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True);summary=OUT/'summary.json';summary.unlink(missing_ok=True)
 rows=[];sim=ROOT/'build/sim/rv32_ooo_sim';old=ROOT/'build/baselines/ap5b-post-lsu-v1/qualified-reference-sim'
 timing=['+core-period-ps=5500','+imem-response-ps=5500','+imem-interval-ps=5500','+dmem-response-ps=5500']
 for name in ('rv32i_basic','store_forwarding','lsu_redirect_variable_lat','wrong_path_store','partial_overlap','unresolved_store','fp_basic','fp_fma'):
  elf=ROOT/f'build/tests/{name}.elf';texts={}
  for mode,model,args in (('old',old,[]),('legacy',sim,[]),('fixed',sim,timing),('faster_core',sim,['+core-period-ps=3000',*timing[1:]])):
   log=OUT/f'{name}-{mode}.log';audit=OUT/f'{name}-{mode}.json';audit.unlink(missing_ok=True)
   cmd=[str(model),f'+elf={elf}','+max-cycles=1000000',*args,*([f'+memory-audit={audit}'] if mode in ('fixed','faster_core') else [])]
   result=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60);log.write_text(result.stdout);texts[mode]=result.stdout
   passed=result.returncode==0 and 'PASS (0)' in result.stdout
   if mode in ('fixed','faster_core'):
    data=json.loads(audit.read_text());passed &= data['imem_min_response_ps']>=5500 and data['dmem_min_response_ps']>=5500 and data['imem_max_response_ps']<5500+(5500 if mode=='fixed' else 3000) and data['dmem_max_response_ps']<5500+(5500 if mode=='fixed' else 3000)
   rows.append(dict(name=name,mode=mode,command=cmd,passed=passed,returncode=result.returncode,log=str(log.relative_to(ROOT)),log_sha256=sha(log)))
  rows.append(dict(name=name,mode='stdout_equivalence',passed=texts['old']==texts['legacy']==texts['fixed']))
 for name,args in (('zero',['+core-period-ps=0']),('negative',['+core-period-ps=-1']),('junk',['+core-period-ps=1x']),('partial',['+core-period-ps=5500']),('mixed',[*timing,'+dmem-latency=1']),('overflow',['+core-period-ps=18446744073709551615',*timing[1:]])):
  result=subprocess.run([str(sim),*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10);(OUT/f'invalid-{name}.log').write_text(result.stdout);rows.append(dict(name=name,mode='reject_invalid',passed=result.returncode==2,returncode=result.returncode))
 # Reuse the exact already-qualified access-fault ELF bytes, without recompiling.
 prior=json.loads((ROOT/'docs/evidence/2026-10-18/lsu-interface-fix/verifier/interface.json').read_text())
 for name in ('sw','sb','sh','fsw','lw','flw'):
  source=next(r for r in prior['records'] if r['name']==f'{name}-ready1-delay1')
  elf=ROOT/f'build/qualification/lsu-interface/{name}.elf';assert sha(elf)==source['elf_sha256']
  for core_ps in (5500,3000):
   trace=OUT/f'fault-{name}-{core_ps}.trace';trace.unlink(missing_ok=True)
   addr=source['expected_tval'];mode='load' if name in ('lw','flw') else 'store'
   cmd=[str(sim),f'+elf={elf}',f'+core-period-ps={core_ps}',*timing[1:],f'+dmem-fault-{mode}=0x{addr & ~3:x}',f'+trace={trace}']
   result=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60);log=OUT/f'fault-{name}-{core_ps}.log';log.write_text(result.stdout)
   traps=re.findall(r'TRAP encountered.*PC=0x([0-9a-f]+).*cause=0x([0-9a-f]+) tval=0x([0-9a-f]+)',result.stdout)
   retired={int(x,16) for x in re.findall(r'^core 0: 0x([0-9a-f]+)',trace.read_text(),re.MULTILINE)}
   pc=source['expected_pc'];passed=result.returncode==0 and traps==[(f'{pc:x}',f"{source['expected_cause']:x}",f'{addr:x}')] and 'fault_requests=1 fault_responses=1' in result.stdout and not(retired & {pc,pc+4,pc+8})
   rows.append(dict(name=name,mode=f'fixed_fault_core{core_ps}',passed=passed,command=cmd,returncode=result.returncode,elf_sha256=sha(elf),log=str(log.relative_to(ROOT)),log_sha256=sha(log),trace=str(trace.relative_to(ROOT)),trace_sha256=sha(trace)))
 report={'scope' :'Fixed-physical-time model qualification; no physical frequency claim','simulator_sha256':sha(sim),'reference_simulator_sha256':sha(old),'records':rows,'passed':len(rows)==58 and all(r['passed'] for r in rows)};summary.write_text(json.dumps(report,indent=2)+'\n');print('memory time',sum(r['passed'] for r in rows),'/',len(rows));raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
