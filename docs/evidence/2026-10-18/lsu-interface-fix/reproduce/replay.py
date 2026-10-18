from pathlib import Path
import hashlib,json,subprocess
base=Path('build/qualification/lsu-interface-original');rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
command=['g++','-std=c++17','-Os','-Ibuild/sim','-Isim/tb','-I/usr/share/verilator/include','-I/usr/share/verilator/include/vltstd','-DVM_TRACE=1','-DVM_COVERAGE=0','-DVM_SC=0',str(base/'diagnostic-main.cpp'),'build/sim/sim_mem.o','build/sim/verilated.o','build/sim/verilated_vcd_c.o','build/sim/Vrv32_ooo_core__ALL.a','-o',str(base/'diagnostic-sim')]
r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(base/'build.log').write_bytes(r.stdout)
assert r.returncode==0,r.stdout
for name in ('store_forwarding','rv32i_basic'):
 for mode,options in (('ready',['+diagnostic-ready-stall','+max-cycles=100000']),('store_error',['+diagnostic-store-error','+max-cycles=1000'])):
  cmd=[str(base/'diagnostic-sim'),'+elf=/workspace/build/tests/'+name+'.elf',*options]
  r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60);log=base/(name+'-'+mode+'.log');log.write_bytes(r.stdout);text=r.stdout.decode()
  passed=(r.returncode==0 and 'lsu_ready=1 ex0_advance=1' not in text) if mode=='ready' else ('store_error_responses=1' in text and 'cause=0x7' in text)
  rows.append({'name':name,'mode':mode,'command':cmd,'returncode':r.returncode,'passed':passed,'log':str(log),'log_sha256':sha(log)})
report={'scope':'Replay original environment-only probes; original programs have no dedicated fault handler, so this checks trap observation only. Handled-fault recovery is separately qualified. Request-time write is preserved by this historical harness.','source_sha256':sha(base/'diagnostic-main.cpp'),'build_command':command,'simulator_sha256':sha(base/'diagnostic-sim'),'records':rows,'passed':all(r['passed'] for r in rows)}
(base/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(report['passed']);raise SystemExit(0 if report['passed'] else 1)
