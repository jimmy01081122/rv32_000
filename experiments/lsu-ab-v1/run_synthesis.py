#!/usr/bin/env python3
"""Bind the unchanged native shared-FPU synthesis flow to the new A+B input."""
import importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from experiment_contract import load_experiment
def require(ok,msg):
    if not ok:raise ValueError(msg)
def main():
    contract,_=load_experiment(ROOT/'experiments/lsu-ab-v1/manifest.json')
    path=ROOT/'build/experiments/lsu-ab-v1/rtl_lowered.v';proof=path.with_suffix('.lowering.json')
    d=json.loads(proof.read_text())
    require(d['passed'] and d['returncode']==0 and d['input_identities_unchanged'] and
            d['rtl_files_sha256']==contract['candidate_rtl_files_sha256'] and
            d['experiment_manifest_sha256']==sha(ROOT/'experiments/lsu-ab-v1/manifest.json') and
            d['lowered_rtl_sha256']==sha(path),'A+B lowering source mismatch')
    original=ROOT/'experiments/fpu-mapping-v1/run_synthesis.py'
    spec=importlib.util.spec_from_file_location('accepted_synthesis',original)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.INPUTS={'AB':(str(path.relative_to(ROOT)),sha(path))}
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),original,proof,path,
             ROOT/'experiments/lsu-ab-v1/manifest.json']}
    start=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    module.main()
    require(all(sha(ROOT/p)==h for p,h in inputs.items()),'synthesis adapter/input changed')
    require(start==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'synthesis source commit changed')
    out=Path(sys.argv[sys.argv.index('--output')+1])
    (out/'adapter-proof.json').write_text(json.dumps(dict(passed=True,source_commit=start,inputs_sha256=inputs,
       scope='unchanged native synthesis commands; AB source identity supplied by adapter'),indent=2)+'\n')
if __name__=='__main__':main()
