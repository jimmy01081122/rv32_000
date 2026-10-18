from pathlib import Path
import hashlib,json,subprocess

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capture(cmd):return subprocess.check_output(cmd,text=True).strip()
def state():return {'commit':capture(['git','rev-parse','HEAD']),'status':capture(['git','status','--porcelain'])}
base=Path('build/qualification');stage=base/'lsu-fix-archive';after=json.loads((base/'lsu-interface/summary.json').read_text());full=json.loads((stage/'run.json').read_text())
start=state();assert start['status']=='' and after['source_commit']==start['commit'] and not after['tracked_dirty'] and after['passed']
assert not capture(['git','diff',full['start']['commit'],'--','rtl','sim','scripts/build_sim.sh'])
model_hashes={str(p):sha(p) for p in (Path('build/sim/rv32_ooo_sim'),Path('build/sim-assert/rv32_ooo_sim'))};assert model_hashes==full['simulators']
rows=[];dest=base/'lsu-determinism';dest.mkdir(exist_ok=True)
for case,name in enumerate(('sw','sb','sh','fsw','lw','flw')):
 original=base/'lsu-interface'/f'{name}.elf';repeat=dest/f'{name}.elf'
 cmd=['riscv-none-elf-gcc','-march=rv32imf_zicsr','-mabi=ilp32f','-nostdlib','-nostartfiles','-Wl,--no-relax','-Tsoftware/linker/link.ld',f'-DCASE={case}','software/interface/lsu_fault.S','-o',str(repeat)]
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert r.returncode==0,r.stdout
 payload=[]
 for label,path in (('ec0',base/'lsu-frozen-ec0'/f'{name}.elf'),('current',original)):
  binary=dest/f'{name}-{label}.bin';subprocess.run(['riscv-none-elf-objcopy','-O','binary',str(path),str(binary)],check=True);payload.append(sha(binary))
 row={'name':name,'compile_command':cmd,'elf_sha256':sha(original),'repeat_elf_sha256':sha(repeat),'repeat_elf_equal':sha(original)==sha(repeat),'loadable_payload_sha256':payload[0],'prior_payload_equal':payload[0]==payload[1]};rows.append(row)
assert all(r['repeat_elf_equal'] and r['prior_payload_equal'] for r in rows)
end=state();assert start==end
report={'scope':'Verification-only follow-up: stale-summary guard and deterministic STT_FILE metadata; CPU/model identical to full qualification','start':start,'end':end,'functional_qualification_commit':full['start']['commit'],'rtl_sim_diff_empty':True,'simulators':model_hashes,'interface_cases':len(after['records']),'interface_passed':after['passed'],'fixture_identity':rows,'passed':True}
(base/'lsu-verifier-proof.json').write_text(json.dumps(report,indent=2)+'\n');print('verifier follow-up PASS; deterministic ELFs 6/6, payloads/model unchanged')
