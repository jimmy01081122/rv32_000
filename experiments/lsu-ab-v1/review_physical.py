#!/usr/bin/env python3
"""Admit AB through the unchanged native guard reviewer and exact FPU proof."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
HERE=ROOT/'experiments/lsu-ab-v1';BASE=ROOT/'build/experiments/lsu-ab-v1';OUT=BASE/'native'
sys.path.insert(0,str(ROOT/'experiments/optimization-135-v1'))
import review_physical_A as prior
from checkpoint import verify_archive
from review_physical_A import read,sha,require,logical_sha,guest_path,archive_index,archived_current,command_shape,accepted,review_formal

def source_link(contract,index,formal):
    old=ROOT/'build/experiments/lsu-b-validation-v2/formal-to-physical-link-review.json'
    archived_current(old,index);reference=read(old)
    require(reference['passed'] and reference['proof_summary_sha256']==formal['proof_summary_sha256'],
            'shared FPU equivalence proof mismatch')
    manifest_path=ROOT/contract['shared_link_manifest']['path']
    require(sha(manifest_path)==contract['shared_link_manifest']['sha256'],'AB link manifest changed')
    manifest=read(manifest_path);row=manifest['variants']['AB'];policy=contract['variants']['AB']
    require(manifest['passed'] and manifest['reference_link_manifest_sha256']==reference['link_manifest_sha256'] and
            manifest['shared_fpu_graph_sha256']==reference['shared_graph_sha256']==contract['shared_fpu_graph_sha256'],
            'AB does not reuse the proved FPU')
    sys.path.insert(0,str(ROOT/'experiments/fpu-mapping-v1'))
    from link_shared import modules,complete,interface,REL,MODULE
    from compare_mapped import canonical_graph
    native=BASE/'mapping-v1/AB';complete(native)
    adapter=read(native.parent/'adapter-proof.json');require(adapter['passed'],'missing AB synthesis adapter proof')
    for p,h in adapter['inputs_sha256'].items():require(sha(ROOT/p)==h,'changed AB synthesis adapter input')
    require(sha(native/'run.json')==row['native_report_sha256'] and sha(ROOT/row['netlist'])==row['netlist_sha256'],
            'AB native mapping evidence changed')
    original=modules(ROOT/row['netlist']);linked=modules(ROOT/policy['netlist'])
    require(set(original)==set(linked)=={'rv32_ooo_core',MODULE},'wrong mapped module set')
    require(sha(ROOT/policy['netlist'])==policy['netlist_sha256']==row['linked_sha256'] and
            linked['rv32_ooo_core']==original['rv32_ooo_core'] and
            hashlib.sha256(linked['rv32_ooo_core']).hexdigest()==row['core_body_sha256'],'AB core changed at FPU link')
    unit=ROOT/manifest['unit_netlist'];mapped=unit.with_name('fp_mapped.rtlil.json')
    require(sha(unit)==manifest['unit_netlist_sha256'] and sha(mapped)==manifest['unit_json_sha256']==reference['actual_mapped_json_sha256'],
            'proved FPU implementation changed')
    require(linked[MODULE]==modules(unit)[MODULE] and
            hashlib.sha256(linked[MODULE]).hexdigest()==manifest['shared_fpu_body_sha256'],'linked FPU body changed')
    module=read(mapped)['modules'][MODULE];_,graph=canonical_graph(module)
    require(graph==reference['shared_graph_sha256'] and interface(module)==manifest['interface']==
            interface(read(native/REL/'fp_mapped.rtlil.json')['modules'][MODULE]),'FPU graph/port ABI mismatch')
    lowering=BASE/'rtl_lowered.lowering.json';d=read(lowering);rtl=BASE/'rtl_lowered.v'
    require(d['passed'] and d['input_identities_unchanged'] and d['returncode']==0 and
            d['experiment_manifest_sha256']==contract['experiment_manifest_sha256'] and
            d['rtl_files_sha256']==policy['rtl_files_sha256'] and d['lowered_rtl_sha256']==sha(rtl),
            'AB RTL/lowering lineage mismatch')
    body=re.findall(r'^module rv32_ooo_fp_execute\s*\(.*?^endmodule',rtl.read_text(),re.M|re.S)
    require(len(body)==1 and hashlib.sha256(body[0].encode()).hexdigest()==reference['original_FPU_body_sha256'],
            'AB FPU source differs from equivalence golden')
    return dict(passed=True,retained_link_review_sha256=sha(old),proof_summary_sha256=formal['proof_summary_sha256'],
                common_graph_sha256=graph,AB_linked_netlist_sha256=policy['netlist_sha256'],
                AB_lowering_report_sha256=sha(lowering),AB_mapping_report_sha256=sha(native/'run.json'))

def review(analysis):
    contract_path=OUT/'AB-guard-bound-contract.json';contract=read(contract_path)
    require(contract['physical']==read(ROOT/'experiments/lsu-b-validation-v2/contract-ready-guard.json')['physical'],
            'accepted physical policy changed')
    require(contract['experiment_manifest_sha256']==sha(HERE/'manifest.json') and
            contract['baseline_manifest_sha256']==sha(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'),'frozen identity changed')
    for p,h in {**contract['unchanged_rtl'],**contract['native_flow_sources_sha256'],**contract['study_sources_sha256']}.items():
        require(sha(ROOT/p)==h,'physical input changed: '+p)
    controller=read(OUT/'physical-controller.json');checkpoints=BASE/'checkpoints'
    require(controller['complete'] and controller['stages']==['grt','eco','guard'] and controller['input_identities_unchanged'] and
            len(controller['checkpoints'])==3 and controller['bound_guard_contract_sha256']==sha(contract_path),'incomplete native stages')
    require(read(checkpoints/'native-exit.json')['returncode']==0,'native controller failed')
    publication=read(OUT/'native-publication.json')
    require(publication['passed'] and publication['all_host_bytes_and_links_verified'] and publication['private_tmpfs_unmounted'],
            'native results not durably published')
    for item in controller['checkpoints']:
        receipt=read(checkpoints/item['receipt'])
        require(receipt['passed'] and receipt['sha256']==item['sha256']==sha(checkpoints/item['archive']),'checkpoint changed')
        verify_archive(checkpoints/item['archive'],receipt['records'])
    index=archive_index();old_path=prior.OLD/'final-common-clock-review.json'
    require(archived_current(old_path,index)=='c133e45ff7ad30f1ad049a13a45f4c66b3c8a6d37e6cad85daa8aee397de0ea0','accepted B reference changed')
    previous=read(old_path)
    require(previous['passed'] and sha(Path(accepted.__file__))==previous['reviewer_sha256'],'accepted native reviewer changed')
    for directory,collector in [
        (OUT/'physical-AB-v2/eco/independent-sta-v1',prior.OLD/'analyze_physical_v2.py'),
        (analysis,ROOT/'experiments/lsu-b-validation-v2/analyze_guard.py')]:
        require(archived_current(collector,index)==read(directory/'run.json')['collector_sha256'],
                'independent collector differs from accepted source')
    formal=review_formal();link=source_link(contract,index,formal);comparisons=[]
    for stage,number in [('grt',1),('eco',2),('guard',4)]:
        current=read(OUT/f'physical-AB-v{number}'/stage/'run.json')
        require(current['source_commit']==controller['source_commit'],'AB native source commits differ')
        for variant in ['baseline','B']:
            path=prior.OLD/f'physical-{variant}-v{number}'/stage/'run.json';archived_current(path,index);other=read(path)
            require(command_shape(current['command'])==command_shape(other['command']),'native command policy differs')
            for field in ['local_image_id','orfs_commit','period_ps','construction_timing_corners','config_sha256']:
                require(current[field]==other[field],'native flow field changed: '+field)
            comparisons.append(dict(stage=stage,reference=variant,command_policy_identical=True))
    accepted.CONTRACT=contract_path;accepted.PARENT_CONTRACT=HERE/'contract-hold40.json'
    candidate=accepted.review_guard(analysis,'AB',contract);reference=previous['baseline_physical']
    require(10000 in candidate['qualified_periods_ps'] and 10000 in reference['qualified_periods_ps'],'100 MHz not physically qualified')
    area=candidate['standard_cell_area_um2'];baseline=read(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json')
    return dict(passed=True,scope='Independent AB global-route research qualification; no baseline promotion',
                reviewer_sha256=sha(Path(__file__)),accepted_guard_reviewer_sha256=sha(Path(accepted.__file__)),
                contract_sha256=sha(contract_path),formal=formal,formal_to_physical=link,AB_physical=candidate,
                baseline_physical=reference,B_physical=previous['B_physical'],native_comparisons=comparisons,
                original_area_ratio=area/baseline['physical']['standard_cell_area_um2'],
                same_flow_area_ratio=area/reference['standard_cell_area_um2'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'fresh physical review required');d=review(a.analysis.resolve())
    a.output.write_text(json.dumps(d,indent=2)+'\n');print('AB physical qualification PASS',d['original_area_ratio'])
if __name__=='__main__':main()
