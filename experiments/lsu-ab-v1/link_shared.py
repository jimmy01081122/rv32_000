#!/usr/bin/env python3
"""Preserve the freshly mapped AB core and reuse the exact proved shared FPU."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
sys.path.insert(0,str(ROOT/'experiments/fpu-mapping-v1'))
from link_shared import complete,interface,modules,REL,MODULE
from compare_mapped import canonical_graph
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def main():
    p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'fresh linked output required')
    complete(a.core)
    proof=json.loads((a.core.parent/'adapter-proof.json').read_text());require(proof['passed'],'missing synthesis adapter proof')
    for name,h in proof['inputs_sha256'].items():require(sha(ROOT/name)==h,'changed adapter/lowering input')
    old=ROOT/'build/experiments/fpu-mapping-v1/shared-linked-v1/link-manifest.json'
    require(sha(old)=='5c21f821c3e876d7afb898c45709ce45b2eb561fbeba81f7111bd75b9426829c','accepted shared FPU link changed')
    prior=json.loads(old.read_text());unit_path=ROOT/prior['unit_netlist']
    require(sha(unit_path)==prior['unit_netlist_sha256'],'accepted shared unit changed')
    unit_modules=modules(unit_path);require(set(unit_modules)=={MODULE},'unexpected shared unit modules')
    require(digest(unit_modules[MODULE])==prior['shared_fpu_body_sha256'],'shared FPU body mismatch')
    unit_json=unit_path.with_name('fp_mapped.rtlil.json')
    unit=json.loads(unit_json.read_text())['modules'][MODULE]
    _,graph=canonical_graph(unit)
    require(graph==prior['shared_fpu_graph_sha256'] and interface(unit)==prior['interface'],'shared FPU graph/ABI changed')
    source=a.core/REL/'1_2_yosys.v';original=modules(source)
    require(set(original)=={'rv32_ooo_core',MODULE},'unexpected AB synthesis modules')
    old_fp=json.loads((a.core/REL/'fp_mapped.rtlil.json').read_text())['modules'][MODULE]
    require(interface(old_fp)==interface(unit),'AB FPU interface mismatch')
    data=b'// Exact shared FPU; AB core body unchanged at link.\n'+original['rv32_ooo_core']+b'\n'+unit_modules[MODULE]+b'\n'
    a.output.mkdir(parents=True);target=a.output/'AB.v';target.write_bytes(data);reread=modules(target)
    require(reread['rv32_ooo_core']==original['rv32_ooo_core'] and reread[MODULE]==unit_modules[MODULE],'link modified module body')
    report=dict(passed=True,scope='mapped AB core plus exact previously proved shared FPU; physical qualification pending',
      wrapper_sha256=sha(Path(__file__)),reference_link_manifest_sha256=sha(old),unit_netlist=str(unit_path.relative_to(ROOT)),
      unit_netlist_sha256=sha(unit_path),unit_json_sha256=sha(unit_json),shared_fpu_body_sha256=digest(unit_modules[MODULE]),
      shared_fpu_graph_sha256=graph,interface=interface(unit),variants={'AB':dict(netlist=str(source.relative_to(ROOT)),
      netlist_sha256=sha(source),core_body_sha256=digest(original['rv32_ooo_core']),native_report_sha256=sha(a.core/'run.json'),
      linked_netlist=str(target.relative_to(ROOT)),linked_sha256=sha(target))})
    (a.output/'link-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('AB shared FPU link PASS',graph)
if __name__=='__main__':main()
