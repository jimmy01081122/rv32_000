from pathlib import Path
import subprocess,json,hashlib
base=Path('build/qualification/lsu-review/diagnostics');records=[]
for name in ('store_forwarding','rv32i_basic'):
 elf=Path('/workspace/build/tests')/(name+'.elf');rows={}
 for mode,model,args in (('baseline','/workspace/build/sim/rv32_ooo_sim',[]),('control','/workspace/'+str(base/'diagnostic-sim'),[]),('ready','/workspace/'+str(base/'diagnostic-sim'),['+diagnostic-ready-stall']),('store_error','/workspace/'+str(base/'diagnostic-sim'),['+diagnostic-store-error'])):
  command=[model,'+elf='+str(elf),'+max-cycles=100000',*args]
  result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
  path=base/(name+'-'+mode+'.log');path.write_text(result.stdout)
  rows[mode]={'command':command,'returncode':result.returncode,'log':str(path),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'store_fault_delivered':'store_error_responses=1' in result.stdout,'watchdog':'Watchdog timeout' in result.stdout,'store_access_trap':'cause=0x7' in result.stdout,'upstream_accepts_blocked_load':'lsu_ready=1 ex0_advance=1' in result.stdout}
  print(name,mode,result.returncode,'watchdog',rows[mode]['watchdog'],'fault',rows[mode]['store_fault_delivered'],'trap7',rows[mode]['store_access_trap'],flush=True)
 records.append({'name':name,'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'records':rows,'control_matches_baseline':(base/(name+'-baseline.log')).read_bytes()==(base/(name+'-control.log')).read_bytes()})
report={'scope':'Separate environment fault diagnostics, not passing ISA tests or performance measurements','baseline_simulator_sha256':hashlib.sha256(Path('build/sim/rv32_ooo_sim').read_bytes()).hexdigest(),'diagnostic_simulator_sha256':hashlib.sha256((base/'diagnostic-sim').read_bytes()).hexdigest(),'records':records}
report['environment_contract_passed']=all(r['control_matches_baseline'] and r['records']['ready']['returncode']==0 and r['records']['store_error']['store_access_trap'] and r['records']['store_error']['store_fault_delivered'] for r in records)
(base/'results.json').write_text(json.dumps(report,indent=2)+'\n')

raise SystemExit(0 if report['environment_contract_passed'] else 1)
