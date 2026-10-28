from pathlib import Path
import subprocess,json,hashlib,datetime
root=Path.cwd();out=Path(__file__).parent.resolve();driver=root/'experiments/fpu-mapping-v1/gate_driver.cc';headers=out.parent/'gate-sim-v1/include/backends/cxxrtl/runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={str(p.relative_to(root)):sha(p) for p in [driver,out/'model.cc']+list(headers.rglob('*.h'))}
cmd=['c++','-std=c++17','-O2','-fno-inline','-g0','-D__has_attribute(x)=0','-I',str(headers),'-I',str(out),str(driver),'-o',str(out/'check-gates')]
r=dict(scope='original RTL model versus mapped-cell function model; not independent IEEE oracle',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs=inputs,compile_command=cmd,compiler=subprocess.check_output(['c++','--version'],text=True),state='compiling',passed=False)
def save():(out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n')
save()
with (out/'compile.log').open('x') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
r['compile_returncode']=rc;save()
if rc:raise SystemExit(rc)
r.update(state='testing',executable_sha256=sha(out/'check-gates'));save()
with (out/'result.json').open('x') as stdout,(out/'test.log').open('x') as stderr:rc=subprocess.run([str(out/'check-gates')],stdout=stdout,stderr=stderr).returncode
r.update(test_returncode=rc,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),input_identities_unchanged=all(sha(root/p)==h for p,h in inputs.items()),state='finished')
if rc==0:r['test_result']=json.loads((out/'result.json').read_text())
r['passed']=rc==0 and r['input_identities_unchanged'] and r['test_result']['passed'];save()
raise SystemExit(0 if r['passed'] else 1)
