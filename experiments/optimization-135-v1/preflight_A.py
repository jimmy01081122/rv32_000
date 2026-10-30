#!/usr/bin/env python3
"""Offline A input/policy checks; does not qualify or start a physical run."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    accepted=json.loads((ROOT/'experiments/lsu-b-validation-v2/contract-ready-guard.json').read_text())
    a=json.loads((ROOT/'experiments/lsu-a-v1/manifest.json').read_text())
    reports=[]
    for name in ['contract-grt.json','contract-hold40.json','contract-guard.json']:
        p=HERE/name;d=json.loads(p.read_text())
        assert d['physical']==accepted['physical'], 'changed accepted physical policy'
        assert set(d['variants'])=={'A'}
        assert d['variants']['A']['rtl_files_sha256']==a['candidate_rtl_files_sha256']
        for k,h in {**d['unchanged_rtl'],**d['native_flow_sources_sha256'],**d['study_sources_sha256']}.items():assert sha(ROOT/k)==h,k
        row=d['variants']['A'];assert sha(ROOT/row['netlist'])==row['netlist_sha256']
        row=d['shared_link_manifest'];assert sha(ROOT/row['path'])==row['sha256']
        if 'incoming_contract' in d:
            row=d['incoming_contract'];assert sha(ROOT/row['path'])==row['sha256']
        reports.append(dict(contract=name,sha256=sha(p),passed=True))
    print(json.dumps(dict(scope='offline identity/policy preflight only; native execution/qualification outstanding',records=reports,passed=True),indent=2))
if __name__=='__main__':main()
