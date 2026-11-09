#!/usr/bin/env python3
"""Create explicit AB contracts with the exact accepted A/B physical policy."""
import copy,json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_contract import sha
from experiment_contract import load_experiment
def main():
    here=ROOT/'experiments/lsu-ab-v1'
    exp,_=load_experiment(here/'manifest.json')
    link_path=ROOT/'build/experiments/lsu-ab-v1/shared-linked-v1/link-manifest.json'
    link=json.loads(link_path.read_text())
    if not link['passed']:raise ValueError('complete shared link required')
    policy=json.loads((ROOT/'experiments/lsu-b-validation-v2/contract-ready-guard.json').read_text())['physical']
    for kind in ['grt','hold40','guard']:
        template=ROOT/'experiments/optimization-135-v1'/('contract-'+kind+'.json')
        d=json.loads(template.read_text())
        if d['physical']!=policy:raise ValueError('historical common policy differs')
        d.update(experiment_id='lsu-ab-'+kind+'-v1',scope='Independent AB under exact accepted shared-FPU/hold40/uniform-guard global-route policy; no baseline promotion',
                 source_parent=exp['tooling_reference_commit'],experiment_manifest_sha256=sha(here/'manifest.json'),
                 template_sha256=sha(template),unchanged_rtl=exp['candidate_rtl_files_sha256'],
                 shared_link_manifest={'path':str(link_path.relative_to(ROOT)),'sha256':sha(link_path)})
        d.pop('a_manifest_sha256',None);d.pop('b_manifest_sha256',None)
        d['variants']={'AB':{'netlist':link['variants']['AB']['linked_netlist'],
                           'netlist_sha256':link['variants']['AB']['linked_sha256'],
                           'rtl_files_sha256':exp['candidate_rtl_files_sha256']}}
        d['study_sources_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [here/'run_physical.py',here/'guard_ab.py',
             ROOT/'experiments/optimization-135-v1/checkpoint.py']}
        if kind!='grt':
            incoming=here/('contract-grt.json' if kind=='hold40' else 'contract-hold40.json')
            d['incoming_contract']={'path':str(incoming.relative_to(ROOT)),'sha256':sha(incoming)}
        path=here/('contract-'+kind+'.json')
        if path.exists():raise ValueError('preserve prior physical contract')
        path.write_text(json.dumps(d,indent=2)+'\n')
    print('AB physical policy frozen; commit contracts before native construction')
if __name__=='__main__':main()
