"""Run only the unmodified v2 baseline GRT stage; separately version ECO selection."""
from pathlib import Path
import datetime,importlib.util,json,subprocess
root=Path('/workspace');script=root/'experiments/lsu-b-validation-v2/physical.py';spec=importlib.util.spec_from_file_location('physical',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
contract=json.loads(m.CONTRACT.read_text())
assert subprocess.check_output(['git','-C','/orfs-source','rev-parse','HEAD'],text=True).strip()==contract['physical']['orfs_commit']
assert not subprocess.check_output(['git','-C','/orfs-source','status','--porcelain'])
for name,h in contract['unchanged_rtl'].items():assert m.sha(root/name)==h
for row in contract['variants'].values():assert m.sha(root/row['netlist'])==row['netlist_sha256']
assert m.sha(root/contract['shared_link_manifest']['path'])==contract['shared_link_manifest']['sha256']
subprocess.run(['sha256sum','--strict','--quiet','-c',str(m.MANIFEST)],check=True)
out=root/'build/experiments/lsu-b-validation-v2/physical-baseline-v1';out.mkdir();state=dict(variant='baseline',contract_sha256=m.sha(m.CONTRACT),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stages=[],complete=False,scope='unmodified v2 GRT only; 100 ps ECO not repeated after B nonconvergence',controller_sha256=m.sha(Path(__file__)));m.write_json(out/'pipeline.json',state)
m.run_stage(out/'grt','grt','baseline',contract)
subprocess.run(['sha256sum','--strict','--quiet','-c',str(m.MANIFEST)],check=True)
state.update(stages=['grt'],grt_complete=True,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());m.write_json(out/'pipeline.json',state);print('BASELINE GRT COMPLETE; ECO SELECTION SEPARATELY VERSIONED',flush=True)
